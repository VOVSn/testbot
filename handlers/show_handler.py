import io

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.common_helpers import normalize_test_id


async def show_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles /show command, sending test questions with answer options
       (without indicating correct one) formatted for printing as .txt"""
    if not update.effective_user:
        logger.warning('/show triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username

    logger.info(f"User {user_id} (@{username}) triggered /show command.")

    if not context.args:
        logger.info(f"Missing test_id arg for /show by user {user_id}.")
        await update.message.reply_text(
            "Пожалуйста, укажите ID теста.\nПример: `/show math101`"
        )
        return

    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)

    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return

    logger.info(f"User {user_id} requesting printable test questions for '{test_id}'.")

    try:
        # 1. Fetch the test document from MongoDB
        tests_collection = await get_collection('tests')
        test_data = await tests_collection.find_one(
            {'test_id': test_id},
            {'_id': 0, 'title': 1, 'questions': 1}
        )

        if not test_data:
            logger.warning(f"Test with ID '{test_id}' not found in DB.")
            await update.message.reply_text(f"Тест с ID '{test_id}' не найден.")
            return

        questions = test_data.get('questions')
        test_title = test_data.get('title', f"Тест {test_id}")

        if not questions or not isinstance(questions, list):
            logger.warning(
                f"Test '{test_id}' found but has no questions or invalid format."
            )
            await update.message.reply_text(
                f"В тесте '{test_id}' нет вопросов или формат некорректен."
            )
            return

        # 2. Generate the text content with corrected formatting
        test_lines = []
        for i, q_data in enumerate(questions):
            question_text = q_data.get('question_text', f'Вопрос {i+1}')
            options = q_data.get('options', [])

            if not isinstance(options, list):
                 logger.warning(f"Question {i+1} in test '{test_id}' has invalid options format.")
                 options_text = "[Неверный формат опций]"
            elif not options:
                 options_text = "[Нет вариантов ответа]"
            else:
                # --- FORMATTING CHANGE HERE ---
                # Use "[   ]" prefix and omit numbering for options
                options_text = "\n".join(
                    f"[   ] {opt}" for opt in options
                )
                # --- END FORMATTING CHANGE ---

            # Add question number before the question text
            test_lines.append(f"{i+1}. {question_text}\n{options_text}")

        # Add title (Markdown won't render in TXT, but harmless)
        test_content = f"**{test_title}**\n\n" + '\n\n'.join(test_lines)

        # 3. Create an in-memory text file
        txt_buffer = io.StringIO()
        txt_buffer.write(test_content)
        txt_buffer.seek(0)

        # 4. Send the file
        file_name = f'test_{test_id}.txt'
        await update.message.reply_text(
            f"📄 Вот вопросы для теста '{test_id}' (версия для печати):",
             quote=False
        )
        await update.message.reply_document(
            document=txt_buffer, filename=file_name
        )
        logger.info(
            f"Sent printable text version of test '{test_id}' to user {user_id}."
        )

    except Exception as e:
        logger.exception(
            f"Error fetching or generating test '{test_id}' for /show: {e}"
        )
        await update.message.reply_text(
            "Произошла ошибка при получении вопросов теста."
        )


show_command_handler = CommandHandler('show', show_command)