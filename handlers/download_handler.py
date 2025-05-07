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
        tests_collection = await get_collection('tests')
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
                f"В тесте '{test_id}' нет вопросов для скачивания или они некорректны."
            )
            return

        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        # Optional: Header for clarity in downloaded CSV
        # csv_writer.writerow(['Вопрос', 'ТекстПравильногоОтвета', 'Опция1', 'Опция2', 'Опция3', 'Опция4'])


        for q_data in questions:
            question_text = q_data.get('question_text', '')
            options = q_data.get('options', []) # Should be a list of 4 strings
            correct_index = q_data.get('correct_option_index', -1)

            # Validate data fetched from DB
            if not question_text or not isinstance(options, list) or len(options) != 4 or \
               not (0 <= correct_index < len(options)):
                logger.warning(f"Skipping invalid question data during download for test '{test_id}': {q_data}")
                continue
            
            correct_answer_text = options[correct_index]

            # Construct the row: Question;CorrectAnswerText;Opt1;Opt2;Opt3;Opt4
            # The 'options' list already contains Opt1, Opt2, Opt3, Opt4
            csv_row = [question_text, correct_answer_text] + options
            csv_writer.writerow(csv_row)

        csv_content = csv_buffer.getvalue()
        if not csv_content.strip():
             logger.warning(f"No valid question data could be formatted for download for test '{test_id}'.")
             await update.message.reply_text(f"Не удалось сформировать CSV для теста '{test_id}'. Возможно, в нем нет корректных вопросов.")
             return

        csv_buffer.seek(0)

        file_name = f'test_{test_id}.csv'
        await update.message.reply_document(
            document=csv_buffer,
            filename=file_name,
            caption=f"⬇️ CSV файл для теста '{test_id}'.\nФормат: Вопрос;ПравильныйОтвет;Опция1;Опция2;Опция3;Опция4"
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