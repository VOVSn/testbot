import os
import re
import random

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, filters

from logging_config import logger
from settings import MATERIALS_FOLDER, TESTS_FOLDER, ADMIN_USERNAME

UPLOAD_STATE = range(1)  # For tracking the state of uploads


def generate_random_digits(length=10):
    return ''.join(random.choices('0123456789', k=length))


async def load_command(update: Update, context: CallbackContext) -> int:
    user_username = update.message.from_user.username
    teacher_usernames = context.bot_data.get('teacher_usernames', [])
    logger.info(f"User {user_username} triggered /load command.")

    # Check if the user is the admin or a teacher
    if user_username != ADMIN_USERNAME and user_username not in teacher_usernames:
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
        await update.message.reply_text("Некорректный test_id. Используйте только буквы и цифры.")
        return ConversationHandler.END

    context.user_data['load_mode'] = 'materials'
    context.user_data['test_id'] = test_id
    materials_folder = os.path.join(MATERIALS_FOLDER, test_id)
    os.makedirs(materials_folder, exist_ok=True)

    await update.message.reply_text(
        f"Отправьте файлы для загрузки материалов в: materials/{test_id}/"
    )
    return UPLOAD_STATE


async def handle_file_upload(update: Update, context: CallbackContext) -> int:
    user_username = update.message.from_user.username
    document = update.message.document
    photo = update.message.photo
    video = update.message.video
    audio = update.message.audio

    # Check which type of file was uploaded
    if document:
        file_type = "document"
        file_id = document.file_id
        file_name = document.file_name if document.file_name else f"document_{generate_random_digits()}.txt"
    elif photo:
        file_type = "photo"
        file_id = photo[-1].file_id  # Get the highest-resolution photo
        file_name = f"photo_{generate_random_digits()}.jpg"
    elif video:
        file_type = "video"
        file_id = video.file_id
        file_name = (video.file_name if video.file_name else f"video_{generate_random_digits()}.mp4")
    elif audio:
        file_type = "audio"
        file_id = audio.file_id
        file_name = (audio.file_name if audio.file_name else f"audio_{generate_random_digits()}.mp3")
    else:
        await update.message.reply_text("Пожалуйста, отправьте файл.")
        return UPLOAD_STATE

    load_mode = context.user_data.get('load_mode')
    logger.debug(f"User {user_username} is uploading a {file_type} in mode {load_mode}")

    try:
        # Get the file using its file_id
        file = await context.bot.get_file(file_id)

        # Handle file uploads based on the load mode
        if load_mode == 'test_csv' and file_type == 'document':
            if not file_name.startswith("test") or not file_name.endswith(".csv"):
                await update.message.reply_text("Файл должен быть в формате test*.csv.")
                return UPLOAD_STATE

            os.makedirs(TESTS_FOLDER, exist_ok=True)
            file_path = os.path.join(TESTS_FOLDER, file_name)

            logger.info(f"Downloading test file to {file_path}")
            await file.download_to_drive(file_path)
            logger.info(f"Test file {file_name} uploaded by {user_username}.")
            await update.message.reply_text(f"Файл {file_name} успешно загружен в папку tests.")
            return ConversationHandler.END

        elif load_mode == 'materials':
            test_id = context.user_data.get('test_id')
            materials_folder = os.path.join(MATERIALS_FOLDER, test_id)
            os.makedirs(materials_folder, exist_ok=True)
            file_path = os.path.join(materials_folder, file_name)

            logger.info(f"Downloading {file_type} file to {file_path}")
            await file.download_to_drive(file_path)
            logger.info(f"{file_type.capitalize()} file {file_name} uploaded for test {test_id} by {user_username}.")
            await update.message.reply_text(f"Файл {file_name} успешно загружен в папку materials/{test_id}.")
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


async def end_upload_state(update: Update, context: CallbackContext) -> int:
    """Automatically end the upload state on any command or message."""
    logger.info(f"Upload state ended because a message or command was received.")
    await update.message.reply_text("Загрузка прервана.")
    return ConversationHandler.END


# Define the conversation handler for /load
load_command_handler = ConversationHandler(
    entry_points=[CommandHandler('load', load_command)],
    states={
        UPLOAD_STATE: [
            MessageHandler(
                filters.ATTACHMENT,
                handle_file_upload
            ),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                end_upload_state  # Any message (non-command) will end the state
            ),
            CommandHandler(
                'cancel',
                cancel_load  # /cancel will still stop the state manually
            ),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_load)]
)
