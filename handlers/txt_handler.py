import os
from io import StringIO

from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext

from logging_config import logger
from settings import GRADES_FOLDER


async def txt_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /txt command.")

    admin_username = context.bot_data.get('admin_username')
    teacher_usernames = context.bot_data.get('teacher_usernames')
    is_admin = user_username == admin_username
    is_teacher = user_username in teacher_usernames

    if not (is_admin or is_teacher):
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя.")
        return

    if not context.args:
        logger.info(
            f"Missing test_id argument for /txt command by {user_username}.")
        await update.message.reply_text("Пример: /txt 2")
        return

    test_id = context.args[0].strip("'")
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    if not os.path.exists(grades_file):
        logger.warning(f"Results file for test {test_id} not found.")
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return

    logger.info(
        f"Found results for test {test_id}. Sending results as a document.")
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()
    titled_results = f"Результаты теста №'{test_id}'\n\n{results}"
    result_file = StringIO(titled_results)
    result_file.name = f"results'{test_id}'.txt"
    result_file.seek(0)
    await update.message.reply_document(
        document=result_file, filename=f"results'{test_id}'.txt")

txt_command_handler = CommandHandler('txt', txt_command)
