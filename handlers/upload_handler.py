# handlers/load_handler.py (Refactored)

import csv
import io
import re
import datetime

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler,
    filters
)

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role
from utils.common_helpers import normalize_test_id

# Define states
UPLOAD_TYPE, UPLOAD_FILE = range(2) # UPLOAD_TYPE determines mode

# Allowed file types mapping (can be extended)
FILE_TYPE_MAP = {
    'document': filters.Document.ALL,
    'photo': filters.PHOTO,
    'video': filters.VIDEO,
    'audio': filters.AUDIO,
}
ATTACHMENT_FILTER = (
    filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
)


async def upload_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Starts the upload conversation (tests or materials)."""
    if not update.effective_user:
        return ConversationHandler.END

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {user_id} (@{username}) triggered /upload command.")

    # 1. Check permissions
    user_role = await get_user_role(user_id, username)
    if user_role not in ('admin', 'teacher'):
        logger.warning(
            f"User {user_id} ({user_role}) attempted /upload "
            f"without privileges."
        )
        await update.message.reply_text(
            "Эта команда доступна только для администраторов и преподавателей."
        )
        return ConversationHandler.END

    # 2. Determine mode based on arguments
    if not context.args:
        # --- Mode: Upload Test CSV ---
        context.user_data['upload_mode'] = 'test_csv'
        await update.message.reply_text(
            "⬆️ **Загрузка теста:**\n"
            "Пожалуйста, отправьте файл CSV с вопросами.\n"
            "Имя файла должно быть `test<ID>.csv` (например, `testMath101.csv`).\n"
            "Разделитель: точка с запятой (;).\n"
            "Кодировка: UTF-8.\n"
            "Структура: `Вопрос;Правильный ответ;Ответ2;Ответ3...`\n\n"
            "Или используйте /cancel для отмены."
        )
        return UPLOAD_FILE # Go directly to waiting for the file

    else:
        # --- Mode: Upload Materials ---
        raw_test_id = context.args[0]
        test_id = normalize_test_id(raw_test_id)
        if not test_id:
            await update.message.reply_text("Некорректный ID теста.")
            return ConversationHandler.END

        # Check if the base test exists
        tests_collection = await get_collection('tests')
        if not await tests_collection.find_one({'test_id': test_id}):
             await update.message.reply_text(
                 f"⚠️ Тест с ID '{test_id}' не найден в базе. "
                 f"Сначала загрузите тест с помощью `/upload` (без аргументов)."
             )
             return ConversationHandler.END

        context.user_data['upload_mode'] = 'materials'
        context.user_data['test_id'] = test_id
        await update.message.reply_text(
            f"📎 **Загрузка материалов для теста '{test_id}':**\n"
            "Отправьте файлы (документы, фото, видео, аудио).\n"
            "Отправьте /cancel когда закончите."
        )
        return UPLOAD_FILE # Go to waiting for file(s)


async def handle_file_upload(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles receiving attachments based on the upload mode."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END # Should not happen with MessageHandler

    user_id = update.effective_user.id
    username = update.effective_user.username
    upload_mode = context.user_data.get('upload_mode')

    # Determine file type and get file object
    file_type = None
    file = None
    file_name = "unknown_file"
    tg_file_id = None

    if update.message.document:
        file_type = 'document'
        file = update.message.document
        file_name = file.file_name or f"{file_type}_{file.file_unique_id}.dat"
    elif update.message.photo:
        file_type = 'photo'
        file = update.message.photo[-1] # Highest resolution
        file_name = f"{file_type}_{file.file_unique_id}.jpg"
    elif update.message.video:
        file_type = 'video'
        file = update.message.video
        file_name = file.file_name or f"{file_type}_{file.file_unique_id}.mp4"
    elif update.message.audio:
        file_type = 'audio'
        file = update.message.audio
        file_name = file.file_name or f"{file_type}_{file.file_unique_id}.mp3"

    if not file_type or not file:
        logger.warning(f"Could not determine file type for upload from user {user_id}.")
        await update.message.reply_text("Не удалось распознать тип файла. Попробуйте еще раз или /cancel.")
        return UPLOAD_FILE # Stay in state

    tg_file_id = file.file_id
    logger.info(f"User {user_id} uploaded {file_type} '{file_name}' (ID: {tg_file_id}) in mode '{upload_mode}'.")

    # --- Process based on Mode ---
    if upload_mode == 'test_csv':
        return await _handle_test_csv_upload(update, context, file_name, tg_file_id, user_id)
    elif upload_mode == 'materials':
        return await _handle_material_upload(update, context, file_name, tg_file_id, file_type, user_id)
    else:
        logger.error(f"Invalid upload_mode '{upload_mode}' in user_data for user {user_id}.")
        await update.message.reply_text("Внутренняя ошибка состояния загрузки. Пожалуйста, начните заново с /upload.")
        return ConversationHandler.END


async def _handle_test_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str, tg_file_id: str, user_id: int) -> int:
    """Processes an uploaded CSV file intended as a test bank."""
    # 1. Validate filename format
    match = re.match(r'^test.*\.csv$', file_name, re.IGNORECASE)
    if not match:
        await update.message.reply_text(
            "⛔ Имя файла должно быть `test<ID>.csv` (например, testMath101.csv).\n"
            "Пожалуйста, переименуйте и отправьте снова, или /cancel."
        )
        return UPLOAD_FILE # Remain waiting for a correct file

    # Extract raw ID (part after 'test' and before '.csv')
    raw_test_id_match = re.search(r'^test(.*)\.csv$', file_name, re.IGNORECASE)
    if not raw_test_id_match or not raw_test_id_match.group(1):
         await update.message.reply_text(
             "⛔ Не удалось извлечь ID из имени файла `test<ID>.csv`.\n"
             "Убедитесь, что ID присутствует (например, test_FINAL.csv)."
              "Пожалуйста, переименуйте и отправьте снова, или /cancel."
         )
         return UPLOAD_FILE

    raw_test_id = raw_test_id_match.group(1)
    test_id = normalize_test_id(raw_test_id) # Normalize the extracted ID

    if not test_id:
         await update.message.reply_text("⛔ Некорректный ID теста, извлеченный из имени файла.")
         return UPLOAD_FILE

    logger.info(f"Processing CSV upload for test_id '{test_id}' from file '{file_name}'.")

    questions_data = []
    try:
        file_obj = await context.bot.get_file(tg_file_id)
        csv_bytes = io.BytesIO()
        await file_obj.download_to_memory(csv_bytes)
        csv_bytes.seek(0)
        try:
            csv_text = csv_bytes.read().decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(f"CSV file '{file_name}' for test '{test_id}' is not UTF-8 encoded.")
            await update.message.reply_text(
                "⛔ Ошибка: Файл CSV должен быть в кодировке UTF-8.\n"
                "Пожалуйста, сохраните файл в UTF-8 и отправьте снова, или /cancel."
            )
            return UPLOAD_FILE

        csv_reader = csv.reader(io.StringIO(csv_text), delimiter=';')
        line_num = 0
        for row in csv_reader:
            line_num += 1
            if not row or not row[0].strip():
                continue
            
            # Expecting: Question;CorrectAnswerText;Opt1;Opt2;Opt3;Opt4
            if len(row) < 3: # Must have at least Question, CorrectAnswerText, and one Option
                logger.warning(f"Skipping invalid row {line_num} in test '{test_id}' CSV (not enough columns): {row}")
                await update.message.reply_text(f"⚠️ Предупреждение: Пропущена строка {line_num} (недостаточно колонок).")
                continue

            question_text = row[0].strip()
            correct_answer_text = row[1].strip() # The textual value of the correct answer
            
            # The actual options to present to the user are from column 2 onwards (index 2)
            # Filter out empty strings that might result from trailing semicolons
            actual_options = [opt.strip() for opt in row[2:] if opt.strip()] 

            if not question_text:
                logger.warning(f"Skipping row {line_num} in test '{test_id}' CSV: Empty question text.")
                await update.message.reply_text(f"⚠️ Предупреждение: Пропущена строка {line_num} (пустой текст вопроса).")
                continue
            
            if not correct_answer_text:
                logger.warning(f"Skipping row {line_num} in test '{test_id}' CSV: Empty correct answer text.")
                await update.message.reply_text(f"⚠️ Предупреждение: Пропущена строка {line_num} (пустой текст правильного ответа).")
                continue

            if not actual_options:
                logger.warning(f"Skipping row {line_num} in test '{test_id}' CSV: No options provided.")
                await update.message.reply_text(f"⚠️ Предупреждение: Пропущена строка {line_num} (нет вариантов ответа).")
                continue

            # Find the index of the correct_answer_text within the actual_options
            try:
                # Ensure case-sensitive match, or convert both to lower for case-insensitive
                # For simplicity, let's assume case-sensitive as per typical test requirements
                correct_option_idx = actual_options.index(correct_answer_text)
            except ValueError:
                logger.warning(
                    f"Skipping row {line_num} in test '{test_id}' CSV: Correct answer text "
                    f"'{correct_answer_text}' not found in the provided options {actual_options}."
                )
                await update.message.reply_text(
                    f"⚠️ Предупреждение: В строке {line_num} текст правильного ответа "
                    f"'{correct_answer_text}' не найден среди вариантов. Строка пропущена."
                )
                continue
            
            # Ensure a specific number of options if required, e.g., exactly 4
            # For now, we'll use whatever is provided in actual_options.
            # Example: If you require exactly 4 options:
            # if len(actual_options) != 4:
            #     logger.warning(f"Skipping row {line_num}: Expected 4 options, got {len(actual_options)}")
            #     await update.message.reply_text(f"⚠️ Предупреждение: Строка {line_num} должна содержать 4 варианта ответа.")
            #     continue


            questions_data.append({
                'question_text': question_text,
                'options': actual_options, # These are now [Opt1, Opt2, CorrectAnswer, Opt3] or similar
                'correct_option_index': correct_option_idx # Index of correct_answer_text in actual_options
            })

        if not questions_data:
            logger.warning(f"No valid questions found in CSV for test '{test_id}'.")
            await update.message.reply_text(
                "⛔ Ошибка: Не найдено ни одного корректного вопроса в CSV файле.\n"
                "Проверьте формат и отправьте снова, или /cancel."
            )
            return UPLOAD_FILE

    except Exception as e:
        logger.exception(f"Error processing CSV for test '{test_id}': {e}")
        await update.message.reply_text(f"❌ Произошла ошибка при обработке CSV файла: {e}")
        return ConversationHandler.END

    # 3. Update Database (Upsert)
    try:
        tests_collection = await get_collection('tests')
        utc_now = datetime.datetime.now(datetime.timezone.utc)

        # Data that always gets updated or set
        set_data = {
            'questions': questions_data,
            'total_questions': len(questions_data),
            'uploaded_by_user_id': user_id,
            'upload_timestamp': utc_now,
            # Consider adding title update here if desired, e.g., based on ID
            'title': f"Тест {test_id}" # Default title
        }
        # Data that only gets set when inserting a new document
        set_on_insert_data = {
            'test_id': test_id,
            # Add 'date_created': utc_now here if needed
        }

        update_result = await tests_collection.update_one(
            {'test_id': test_id},
            {
                '$set': set_data,
                '$setOnInsert': set_on_insert_data
            },
            upsert=True
        )

        if update_result.upserted_id:
            logger.info(f"Successfully created test '{test_id}' with {len(questions_data)} questions by user {user_id}.")
            await update.message.reply_text(
                f"✅ Тест '{test_id}' ({len(questions_data)} вопр.) успешно создан!"
            )
        elif update_result.modified_count:
             logger.info(f"Successfully updated test '{test_id}' with {len(questions_data)} questions by user {user_id}.")
             await update.message.reply_text(
                 f"✅ Тест '{test_id}' ({len(questions_data)} вопр.) успешно обновлен!"
             )
        else:
             # This case (matched but not modified) might mean the content was identical
             logger.info(f"Test '{test_id}' data submitted by user {user_id} was identical to existing data.")
             await update.message.reply_text(
                 f"ℹ️ Данные для теста '{test_id}' не изменились."
             )

        return ConversationHandler.END # End conversation after successful CSV upload

    except Exception as e:
        logger.exception(f"Database error upserting test '{test_id}': {e}")
        await update.message.reply_text("❌ Произошла ошибка при сохранении теста в базу данных.")
        return ConversationHandler.END


async def _handle_material_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str, tg_file_id: str, file_type: str, user_id: int) -> int:
    """Processes an uploaded file as material for a test."""
    test_id = context.user_data.get('test_id')
    if not test_id:
        logger.error(f"Missing test_id in user_data during material upload for user {user_id}.")
        await update.message.reply_text("Внутренняя ошибка: ID теста не найден. Начните заново с `/upload <ID>`.")
        return ConversationHandler.END

    # Insert material metadata into DB
    try:
        materials_collection = await get_collection('materials')
        material_doc = {
            'test_id': test_id,
            'telegram_file_id': tg_file_id,
            'file_name': file_name,
            'file_type': file_type,
            'uploaded_by_user_id': user_id,
            'upload_timestamp': datetime.datetime.now(datetime.timezone.utc)
        }
        await materials_collection.insert_one(material_doc)

        logger.info(f"Successfully saved material '{file_name}' for test '{test_id}' by user {user_id}.")
        await update.message.reply_text(
            f"✅ Файл '{file_name}' добавлен к тесту '{test_id}'.\n"
            f"Отправьте еще файлы или /cancel для завершения."
        )
        return UPLOAD_FILE # Stay in state to receive more files

    except Exception as e:
        logger.exception(f"Database error saving material for test '{test_id}': {e}")
        await update.message.reply_text(
            f"❌ Ошибка при сохранении файла '{file_name}' в базу данных."
            "\nПопробуйте отправить его снова или /cancel."
        )
        return UPLOAD_FILE # Stay in state, allow retry or cancel


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the upload operation."""
    user_id = update.effective_user.id if update.effective_user else 'Unknown'
    mode = context.user_data.get('upload_mode', 'unknown')
    logger.info(f"User {user_id} canceled the /upload operation (mode: {mode}).")
    await update.message.reply_text("Загрузка отменена.")
    # Clear user_data specific to this conversation
    context.user_data.pop('upload_mode', None)
    context.user_data.pop('test_id', None)
    return ConversationHandler.END


# Rename the main handler variable
upload_command_handler = ConversationHandler(
    entry_points=[CommandHandler('upload', upload_command)],
    states={
        UPLOAD_FILE: [
            MessageHandler(ATTACHMENT_FILTER, handle_file_upload),
            # Could add specific message if user sends text instead of file
            MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text("Пожалуйста, отправьте файл или /cancel.")),
        ],
        # No need for UPLOAD_TYPE state if entry point decides mode
    },
    fallbacks=[CommandHandler('cancel', cancel_upload)],
    # Optional: Add conversation timeout
    # conversation_timeout=60*10 # 10 minutes
)