# utils/seed.py

import os
import csv
import io
import datetime
import re

from db import get_db, get_collection # get_db not used, can remove
from logging_config import logger
from settings import (
    ADMIN_USER_ID, ADMIN_USERNAME,
    INITIAL_SEED_ENABLED, TESTS_SEED_FOLDER, TEACHERS_SEED_FILE
)
from utils.common_helpers import normalize_test_id

async def _seed_initial_admin():
    """
    Ensures the VERY FIRST admin user exists if no admins are found.
    Uses details from .env for this bootstrap process ONLY.
    """
    logger.info("Checking for initial admin bootstrap...")
    if not ADMIN_USER_ID or not ADMIN_USERNAME:
        logger.error('ADMIN_USER_ID or ADMIN_USERNAME not set in .env for bootstrap.')
        return

    try:
        bootstrap_admin_id = int(ADMIN_USER_ID)
    except ValueError:
        logger.error(f'Invalid ADMIN_USER_ID "{ADMIN_USER_ID}" in .env for bootstrap.')
        return

    users_collection = await get_collection('users')

    try:
        existing_admin_count = await users_collection.count_documents({'role': 'admin'})
        if existing_admin_count > 0:
            logger.info(f"Found {existing_admin_count} existing admin(s). Skipping initial admin bootstrap.")
            return

        logger.info(f"No admins found in DB. Attempting to bootstrap admin from .env: "
                    f"ID={bootstrap_admin_id}, Username={ADMIN_USERNAME}")

        update_result = await users_collection.update_one(
            {'user_id': bootstrap_admin_id},
            {'$set': {
                'username': ADMIN_USERNAME,
                'role': 'admin',
                'user_id': bootstrap_admin_id
            },
             '$setOnInsert': {
                 'date_added': datetime.datetime.now(datetime.timezone.utc)
             }},
            upsert=True
        )

        if update_result.upserted_id:
            logger.info(f"Successfully bootstrapped initial admin user {ADMIN_USERNAME} (ID: {bootstrap_admin_id}).")
        elif update_result.matched_count and update_result.modified_count:
            logger.info(f"Successfully promoted existing user {ADMIN_USERNAME} (ID: {bootstrap_admin_id}) to admin during bootstrap.")
        else:
            logger.warning("Admin bootstrap via update_one reported no match or upsert unexpectedly, or no change needed.")

    except Exception as e:
        logger.exception(f"Error during initial admin bootstrap: {e}")
    logger.info("Initial admin bootstrap check complete.")


async def _seed_tests():
    """Seeds tests from CSV files if they don't already exist."""
    logger.info("Checking for initial test seeding...")
    tests_collection = await get_collection('tests')
    if not os.path.isdir(TESTS_SEED_FOLDER):
        logger.warning(f"TESTS_SEED_FOLDER '{TESTS_SEED_FOLDER}' not found. Skipping test seeding.")
        return

    logger.info(f"Seeding tests from folder: {TESTS_SEED_FOLDER}")
    file_count = 0
    seeded_count = 0
    skipped_count = 0

    for filename in os.listdir(TESTS_SEED_FOLDER):
        if re.match(r'^test.*\.csv$', filename, re.IGNORECASE):
            file_count += 1
            file_path = os.path.join(TESTS_SEED_FOLDER, filename)
            raw_test_id_match = re.search(r'^test(.*)\.csv$', filename, re.IGNORECASE)

            if not raw_test_id_match or not raw_test_id_match.group(1):
                logger.warning(f"Could not extract test ID from filename '{filename}'. Skipping.")
                continue

            raw_test_id = raw_test_id_match.group(1)
            test_id = normalize_test_id(raw_test_id)
            if not test_id:
                logger.warning(f"Invalid normalized test ID from filename '{filename}'. Skipping.")
                continue

            if await tests_collection.find_one({'test_id': test_id}, {'_id': 1}):
                logger.info(f"Test '{test_id}' already exists in DB. Skipping file '{filename}'.")
                skipped_count += 1
                continue

            logger.info(f"Processing seed file '{filename}' for test '{test_id}'...")
            questions_data = []
            try:
                with open(file_path, mode='r', encoding='utf-8') as csvfile:
                    csv_reader = csv.reader(csvfile, delimiter=';')
                    line_num = 0
                    for row in csv_reader:
                        line_num += 1
                        if not row or not row[0].strip(): continue

                        if len(row) != 6:
                            logger.warning(
                                f"Seed file '{filename}', line {line_num}: Expected 6 columns, found {len(row)}. Skipping row."
                            )
                            continue

                        question_text = row[0].strip()
                        correct_answer_text = row[1].strip()
                        options_texts = [s.strip() for s in row[2:6]]

                        if not question_text or not correct_answer_text or any(not opt for opt in options_texts):
                            logger.warning(
                                f"Seed file '{filename}', line {line_num}: Missing question, correct answer, or one of 4 options. Skipping row."
                            )
                            continue
                        
                        try:
                            correct_option_idx = options_texts.index(correct_answer_text)
                        except ValueError:
                            logger.warning(
                                f"Seed file '{filename}', line {line_num}: Correct answer text '{correct_answer_text}' "
                                f"not found in options {options_texts}. Skipping row."
                            )
                            continue
                        
                        questions_data.append({
                             'question_text': question_text,
                             'options': options_texts,
                             'correct_option_index': correct_option_idx
                        })

                if not questions_data:
                     logger.warning(f"No valid questions found in '{filename}' for test '{test_id}'. Skipping test seed.")
                     continue

                test_doc = {
                    'test_id': test_id,
                    'title': f"Тест {test_id}", # Or extract from filename/metadata if available
                    'questions': questions_data,
                    'total_questions': len(questions_data),
                    'uploaded_by_user_id': 0, # 0 indicates seeded by system
                    'upload_timestamp': datetime.datetime.now(datetime.timezone.utc),
                }
                insert_result = await tests_collection.insert_one(test_doc)
                if insert_result.inserted_id:
                    logger.info(f"Successfully seeded test '{test_id}' with {len(questions_data)} questions from '{filename}'.")
                    seeded_count += 1
                else:
                    logger.error(f"Failed to insert test '{test_id}' from '{filename}'.")

            except (FileNotFoundError, UnicodeDecodeError, csv.Error) as e:
                 logger.error(f"Error processing seed file '{filename}': {e}")
            except Exception as e:
                 logger.exception(f"Unexpected error processing seed file '{filename}': {e}")

    logger.info(f"Test seeding complete. Processed: {file_count}, Seeded: {seeded_count}, Skipped (exists): {skipped_count}.")


async def _seed_teachers():
    """Seeds initial teachers from a file if no teachers exist yet."""
    logger.info("Checking for initial teacher seeding...")
    users_collection = await get_collection('users')

    existing_teacher_count = await users_collection.count_documents({'role': 'teacher'})
    if existing_teacher_count > 0:
        logger.info(f"Found {existing_teacher_count} existing teacher(s). Skipping teacher seeding.")
        return

    if not os.path.isfile(TEACHERS_SEED_FILE):
        logger.warning(f"TEACHERS_SEED_FILE '{TEACHERS_SEED_FILE}' not found. Skipping teacher seeding.")
        return

    logger.info(f"Seeding teachers from file: {TEACHERS_SEED_FILE}")
    promoted_count = 0
    not_found_or_already_teacher = 0 # Combined count
    line_num = 0
    try:
        with open(TEACHERS_SEED_FILE, mode='r', encoding='utf-8') as file:
            for line in file:
                line_num += 1
                username = line.strip()
                if not username: continue
                if username.startswith('@'): username = username[1:]

                user_doc = await users_collection.find_one({'username': username})
                if user_doc:
                    if user_doc.get('role') != 'teacher':
                        update_result = await users_collection.update_one(
                            {'user_id': user_doc['user_id']},
                            {'$set': {'role': 'teacher'}}
                        )
                        if update_result.modified_count == 1:
                            logger.info(f"Promoted user @{username} (ID: {user_doc['user_id']}) to teacher via seed file.")
                            promoted_count += 1
                        else: # Should not happen if role was not teacher
                            logger.warning(f"Attempted to promote @{username} but role not modified (was {user_doc.get('role')}).")
                            not_found_or_already_teacher +=1
                    else:
                        logger.info(f"User @{username} from seed file is already a teacher.")
                        not_found_or_already_teacher += 1
                else:
                    logger.warning(f"Teacher seed file lists '@{username}' (line {line_num}), but user not found in DB. User must /start first.")
                    not_found_or_already_teacher += 1
    except Exception as e:
        logger.exception(f"Error processing teacher seed file '{TEACHERS_SEED_FILE}': {e}")

    logger.info(f"Teacher seeding complete. Promoted: {promoted_count}, Not found/Already Teacher: {not_found_or_already_teacher}.")


async def seed_initial_data():
    """Orchestrates the initial data seeding process based on settings."""
    logger.info("Running initial data seeding process...")
    await _seed_initial_admin() 

    if INITIAL_SEED_ENABLED:
        logger.info("Initial seeding from files is ENABLED.")
        await _seed_tests()
        await _seed_teachers()
    else:
        logger.info("Initial seeding from files is DISABLED.")

    logger.info("Initial data seeding process finished.")