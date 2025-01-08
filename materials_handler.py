import os

from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext

from logging_config import logger
from settings import MATERIALS_FOLDER


async def materials_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /materials command.")

    if not context.args:
        logger.info(
            f"Missing test_id arg for /materials command by {user_username}.")
        await update.message.reply_text("Пример: /materials 2")
        return

    test_id = context.args[0]
    materials_folder_id = os.path.join(MATERIALS_FOLDER, test_id)
    if not os.path.exists(materials_folder_id):
        logger.warning(f"Materials folder for test {test_id} not found.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return

    files = [
        file for file in os.listdir(materials_folder_id) 
        if os.path.isfile(os.path.join(materials_folder_id, file))
    ]
    if not files:
        logger.warning(
            f"No files found in materials folder for test {test_id}.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return

    logger.info(
        f"Found {len(files)} files for test {test_id}. Sending materials.")
    for file in files:
        file_path = os.path.join(materials_folder_id, file)
        try:
            await update.message.reply_document(document=open(file_path, 'rb'))
            logger.info(f"Sent file {file} to user {user_username}.")
        except Exception as e:
            logger.error(f"Error sending {file} to {user_username}: {str(e)}")
            await update.message.reply_text(f"Ошибка при отправке {file}.")

materials_command_handler = CommandHandler('materials', materials_command)
