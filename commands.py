import os
from io import StringIO

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




async def txt_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /txt command.")
    
    if user_username != context.bot_data.get('teacher_username'):
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя.")
        return

    if not context.args:
        logger.info(f"Missing test_id argument for /txt command by {user_username}.")
        await update.message.reply_text("Пример: /txt '<test_id>'")
        return

    test_id = context.args[0].strip("'")  # Removing any surrounding single quotes
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')

    if not os.path.exists(grades_file):
        logger.warning(f"Results file for test {test_id} not found.")
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return

    logger.info(f"Found results for test {test_id}. Sending results as a document to user {user_username}.")
    
    # Read the content of the grades file
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()

    # Add the title to the results
    titled_results = f"Результаты теста №'{test_id}'\n\n{results}"

    # Create a StringIO object to simulate a file for the bot to send
    result_file = StringIO(titled_results)
    result_file.name = f"results'{test_id}'.txt"  # Set the filename with single quotes
    result_file.seek(0)

    # Send the results as a document (file) to the teacher
    await update.message.reply_document(document=result_file, filename=f"results'{test_id}'.txt")

    # After sending the results, no further action is taken to store them



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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
    Я - робот для тестирования студентов!
    Примеры комманд:
    /test 2 - запустить тест № 2
    /materials 2 - получить учебные материалы по тесту № 2
    """
    await update.message.reply_text(help_text)
