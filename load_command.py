import os
import re

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from logging_config import logger

UPLOAD_STATE = range(1)  # For tracking the state of uploads
MATERIALS_FOLDER = 'materials'


async def load_command(update: Update, context: CallbackContext) -> int:
    user_username = update.message.from_user.username
    admin_username = os.getenv('ADMIN_USERNAME')
    teacher_usernames = context.bot_data.get('teacher_usernames', [])  # Access teacher usernames

    logger.info(f"User {user_username} triggered /load command.")

    # Check if the user is the admin or a teacher
    if user_username != admin_username and user_username not in teacher_usernames:
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя или администратора.")
        return ConversationHandler.END

    # Without arguments: Expecting a test CSV file
    if not context.args:
        await update.message.reply_text(
            "Отправьте файл CSV для загрузки тестов. "
            "Формат файла: test*.csv, разделитель ';'."
        )
        context.user_data['load_mode'] = 'test_csv'
        return UPLOAD_STATE

    # With arguments: Prepare for materials upload
    test_id = context.args[0]
    if not re.match(r'^\w+$', test_id):  # Validate test_id format
        await update.message.reply_text(
            "Некорректный test_id. Используйте только буквы и цифры.")
        return ConversationHandler.END

    context.user_data['load_mode'] = 'materials'
    context.user_data['test_id'] = test_id
    materials_folder = os.path.join(MATERIALS_FOLDER, test_id)
    os.makedirs(materials_folder, exist_ok=True)

    await update.message.reply_text(
        f"Отправьте файлы для загрузки материалов в папку:" 
        f" materials/{test_id}/"
    )
    return UPLOAD_STATE


async def handle_file_upload(update: Update, context: CallbackContext) -> int:
    user_username = update.message.from_user.username
    document = update.message.document

    # Ensure a file was uploaded
    if not document:
        await update.message.reply_text("Пожалуйста, отправьте файл.")
        return UPLOAD_STATE

    load_mode = context.user_data.get('load_mode')
    logger.debug(f"User {user_username} is uploading in mode {load_mode}")

    try:
        # Get the file using its file_id
        file = await context.bot.get_file(document.file_id)

        # Handle test CSV upload
        if load_mode == 'test_csv':
            if not document.file_name.startswith("test") or not document.file_name.endswith(".csv"):
                await update.message.reply_text("Файл должен быть в формате test*.csv.")
                return UPLOAD_STATE

            tests_folder = 'tests'
            os.makedirs(tests_folder, exist_ok=True)
            file_path = os.path.join(tests_folder, document.file_name)

            logger.info(f"Downloading test file to {file_path}")
            await file.download_to_drive(file_path)  # Download the file to the specified path
            logger.info(f"Test file {document.file_name} uploaded by {user_username}.")
            await update.message.reply_text(f"Файл {document.file_name} успешно загружен в папку tests.")
            return ConversationHandler.END

        # Handle materials upload
        elif load_mode == 'materials':
            # Reject CSV files in the materials folder
            if document.file_name.endswith(".csv"):
                await update.message.reply_text(
                    "Cтуденты могут увидеть тесты!")
                return UPLOAD_STATE

            test_id = context.user_data.get('test_id')
            materials_folder = os.path.join(MATERIALS_FOLDER, test_id)
            os.makedirs(materials_folder, exist_ok=True)
            file_path = os.path.join(materials_folder, document.file_name)

            logger.info(f"Downloading material file to {file_path}")
            await file.download_to_drive(file_path)  # Download the file to the specified path
            logger.info(f"Material file {document.file_name} uploaded for test {test_id} by {user_username}.")
            await update.message.reply_text(f"Файл {document.file_name} успешно загружен в папку materials/{test_id}.")
            return UPLOAD_STATE
    except Exception as e:
        logger.exception(f"Error handling file upload: {e}")
        await update.message.reply_text("Ошибка при загрузке файла.")
        return UPLOAD_STATE


async def cancel_load(update: Update, context: CallbackContext) -> int:
    """Cancel the file upload process."""
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} canceled the /load operation.")
    await update.message.reply_text("Загрузка завершена.")
    return ConversationHandler.END
