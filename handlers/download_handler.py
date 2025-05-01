# handlers/download_handler.py

import io
import csv

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role
from utils.common_helpers import normalize_test_id


async def download_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles /download <test_id> command for admins/teachers."""
    if not update.effective_user:
        logger.warning('/download triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {user_id} (@{username}) triggered /download command.")

    # 1. Check permissions
    user_role = await get_user_role(user_id, username)
    if user_role not in ('admin', 'teacher'):
        logger.warning(
            f"User {user_id} ({user_role}) attempted /download "
            f"without privileges."
        )
        await update.message.reply_text(
            "Эта команда доступна только для администраторов и преподавателей."
        )
        return

    # 2. Check arguments
    if not context.args:
        logger.info(f"Missing test_id arg for /download by user {user_id}.")
        await update.message.reply_text(
            "Пожалуйста, укажите ID теста для скачивания.\n"
            "Пример: `/download math101`"
        )
        return

    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)

    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return

    logger.info(f"{user_role.capitalize()} {user_id} requesting download"
                f" for test_id '{test_id}'.")

    try:
        # 3. Fetch the test data from MongoDB
        tests_collection = await get_collection('tests')
        # Fetch only the questions array
        test_data = await tests_collection.find_one(
            {'test_id': test_id},
            {'_id': 0, 'questions': 1}
        )

        if not test_data:
            logger.warning(f"Test '{test_id}' not found in DB for download.")
            await update.message.reply_text(f"Тест с ID '{test_id}' не найден.")
            return

        questions = test_data.get('questions')

        if not questions or not isinstance(questions, list):
            logger.warning(f"Test '{test_id}' has no questions or invalid format.")
            await update.message.reply_text(
                f"В тесте '{test_id}' нет вопросов для скачивания."
            )
            return

        # 4. Generate CSV content in memory
        csv_buffer = io.StringIO()
        # Use quoting=csv.QUOTE_MINIMAL or QUOTE_ALL if needed, default is fine usually
        csv_writer = csv.writer(csv_buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Write header dynamically based on max options? Simpler: write rows directly
        # csv_writer.writerow(['Вопрос', 'Правильный ответ', 'Ответ2', ...]) # Header optional

        for q_data in questions:
            question_text = q_data.get('question_text', '')
            options = q_data.get('options', [])
            correct_index = q_data.get('correct_option_index', -1)

            if not question_text or not options or correct_index < 0 or correct_index >= len(options):
                logger.warning(f"Skipping invalid question data during download for test '{test_id}': {q_data}")
                continue

            correct_answer = options[correct_index]
            # Get other options by excluding the correct one
            other_options = [opt for i, opt in enumerate(options) if i != correct_index]

            # Construct the row as expected by the upload format
            csv_row = [question_text, correct_answer] + other_options
            csv_writer.writerow(csv_row)

        # Check if any rows were written
        csv_content = csv_buffer.getvalue()
        if not csv_content.strip():
             logger.warning(f"No valid question data could be formatted for download for test '{test_id}'.")
             await update.message.reply_text(f"Не удалось сформировать CSV для теста '{test_id}'. Возможно, в нем нет корректных вопросов.")
             return

        csv_buffer.seek(0)

        # 5. Send the CSV file
        file_name = f'test_{test_id}.csv'
        await update.message.reply_document(
            document=csv_buffer,
            filename=file_name,
            caption=f"⬇️ CSV файл для теста '{test_id}'."
        )
        logger.info(f"Sent test '{test_id}' CSV to user {user_id}.")

    except Exception as e:
        logger.exception(
            f"Error fetching or generating CSV for test '{test_id}': {e}"
        )
        await update.message.reply_text(
            "Произошла ошибка при подготовке файла для скачивания."
        )


download_command_handler = CommandHandler('download', download_command)