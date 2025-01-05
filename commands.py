import os

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from logging_config import logger

GRADES_FOLDER = 'grades'
MATERIALS_FOLDER = 'materials'


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /results command.")
    
    if user_username != context.bot_data.get('teacher_username'):
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя.")
        return

    if not context.args:
        logger.info(f"Missing test_id argument for /results command by {user_username}.")
        await update.message.reply_text("Пример: /results <test_id>")
        return

    test_id = context.args[0]
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')

    if not os.path.exists(grades_file):
        logger.warning(f"Results file for test {test_id} not found.")
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return

    logger.info(f"Found results for test {test_id}. Sending results to user {user_username}.")
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()

    await update.message.reply_text(results)


async def materials_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /materials command.")

    if not context.args:
        logger.info(f"Missing test_id argument for /materials command by {user_username}.")
        await update.message.reply_text("Пример: /materials <test_id>")
        return

    test_id = context.args[0]
    materials_folder_id = os.path.join(MATERIALS_FOLDER, test_id)

    if not os.path.exists(materials_folder_id):
        logger.warning(f"Materials folder for test {test_id} not found.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return

    files = [
        file for file in os.listdir(materials_folder_id) if os.path.isfile(
            os.path.join(materials_folder_id, file)
        )
    ]
    if not files:
        logger.warning(f"No files found in materials folder for test {test_id}.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return

    logger.info(f"Found {len(files)} files for test {test_id}. Sending materials to user {user_username}.")
    for file in files:
        file_path = os.path.join(materials_folder_id, file)
        try:
            await update.message.reply_document(document=open(file_path, 'rb'))
            logger.info(f"Sent file {file} to user {user_username}.")
        except Exception as e:
            logger.error(f"Error sending file {file} to user {user_username}: {str(e)}")
            await update.message.reply_text(f"Ошибка при отправке файла {file}.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    Welcome to the bot! Here are some commands you can use:
    
    /start - Start interacting with the bot
    /materials - Get the available materials
    /results - Check your results
    /help - Get this help message
    
    If you need assistance, feel free to reach out!
    """
    await update.message.reply_text(help_text)