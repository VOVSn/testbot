# handlers/upload_handler.py

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
            "⬆️ **Загрузка теста (CSV):**\n"
            "Пожалуйста, отправьте файл CSV с вопросами.\n"
            "Имя файла должно быть `test<ID>.csv` (например, `testMath101.csv`).\n"
            "Разделитель: точка с запятой (;).\n"
            "Кодировка: UTF-8.\n"
            "Структура (6 колонок):\n"
            "`Вопрос;ТекстПравильногоОтвета;Опция1;Опция2;Опция3;Опция4`\n"
            "- `ТекстПравильногоОтвета` должен быть одним из Опция1-Опция4.\n"
            "- Все 4 опции должны быть заполнены.\n\n"
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
        return ConversationHandler.END

    user_id = update.effective_user.id
    # username = update.effective_user.username # Not used directly here
    upload_mode = context.user_data.get('upload_mode')

    file_type = None
    file = None
    file_name = "unknown_file"
    # tg_file_id = None # Assigned below

    if update.message.document:
        file_type = 'document'
        file = update.message.document
        file_name = file.file_name or f"{file_type}_{file.file_unique_id}.dat"
    elif update.message.photo:
        file_type = 'photo'
        file = update.message.photo[-1]
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
        return UPLOAD_FILE

    tg_file_id = file.file_id
    logger.info(f"User {user_id} uploaded {file_type} '{file_name}' (ID: {tg_file_id}) in mode '{upload_mode}'.")

    if upload_mode == 'test_csv':
        if file_type != 'document' or not file_name.lower().endswith('.csv'):
            await update.message.reply_text(
                "⛔ Для загрузки теста ожидается CSV файл (с расширением .csv).\n"
                "Пожалуйста, отправьте корректный файл или /cancel."
            )
            return UPLOAD_FILE
        return await _handle_test_csv_upload(update, context, file_name, tg_file_id, user_id)
    elif upload_mode == 'materials':
        return await _handle_material_upload(update, context, file_name, tg_file_id, file_type, user_id)
    else:
        logger.error(f"Invalid upload_mode '{upload_mode}' in user_data for user {user_id}.")
        await update.message.reply_text("Внутренняя ошибка состояния загрузки. Пожалуйста, начните заново с /upload.")
        return ConversationHandler.END


async def _handle_test_csv_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, file_name: str, tg_file_id: str, user_id: int) -> int:
    """Processes an uploaded CSV file intended as a test bank."""
    match = re.match(r'^test.*\.csv$', file_name, re.IGNORECASE)
    if not match:
        await update.message.reply_text(
            "⛔ Имя файла должно быть `test<ID>.csv` (например, testMath101.csv).\n"
            "Пожалуйста, переименуйте и отправьте снова, или /cancel."
        )
        return UPLOAD_FILE

    raw_test_id_match = re.search(r'^test(.*)\.csv$', file_name, re.IGNORECASE)
    if not raw_test_id_match or not raw_test_id_match.group(1):
         await update.message.reply_text(
             "⛔ Не удалось извлечь ID из имени файла `test<ID>.csv`.\n"
             "Убедитесь, что ID присутствует (например, test_FINAL.csv).\n"
             "Пожалуйста, переименуйте и отправьте снова, или /cancel."
         )
         return UPLOAD_FILE

    raw_test_id = raw_test_id_match.group(1)
    test_id = normalize_test_id(raw_test_id)

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
            if not row or not row[0].strip(): # Skip empty lines or lines with no question
                continue
            
            # Validate column count: Expecting Question;CorrectText;Opt1;Opt2;Opt3;Opt4 (6 columns)
            if len(row) != 6:
                msg = (f"⚠️ Строка {line_num}: Ожидалось 6 колонок (Вопрос;ПравильныйОтвет;"
                       f"Опция1;Опция2;Опция3;Опция4), найдено {len(row)}. Строка пропущена.")
                logger.warning(f"Test '{test_id}' CSV: {msg} Content: {row}")
                await update.message.reply_text(msg)
                continue

            question_text = row[0].strip()
            correct_answer_text = row[1].strip()
            # These are the 4 options for the user
            options_texts = [s.strip() for s in row[2:6]] 

            # --- Validations ---
            if not question_text:
                msg = f"⚠️ Строка {line_num}: Текст вопроса (1-я колонка) не может быть пустым. Строка пропущена."
                logger.warning(f"Test '{test_id}' CSV: {msg} Content: {row}")
                await update.message.reply_text(msg)
                continue
            
            if not correct_answer_text:
                msg = f"⚠️ Строка {line_num}: Текст правильного ответа (2-я колонка) не может быть пустым. Строка пропущена."
                logger.warning(f"Test '{test_id}' CSV: {msg} Content: {row}")
                await update.message.reply_text(msg)
                continue

            if any(not opt for opt in options_texts):
                msg = (f"⚠️ Строка {line_num}: Все 4 варианта ответа (колонки 3-6) должны быть заполнены. "
                       "Строка пропущена.")
                logger.warning(f"Test '{test_id}' CSV: {msg} Content: {row}")
                await update.message.reply_text(msg)
                continue
            
            # Find the index of the correct_answer_text within the 4 options_texts
            try:
                correct_option_idx = options_texts.index(correct_answer_text)
            except ValueError:
                msg = (f"⚠️ Строка {line_num}: Текст правильного ответа из 2-й колонки ('{correct_answer_text}') "
                       f"не найден среди 4-х вариантов ответа ({', '.join(options_texts)}). Строка пропущена.")
                logger.warning(f"Test '{test_id}' CSV: {msg} Content: {row}")
                await update.message.reply_text(msg)
                continue
            
            questions_data.append({
                'question_text': question_text,
                'options': options_texts,  # Store the 4 options
                'correct_option_index': correct_option_idx 
            })

        if not questions_data:
            logger.warning(f"No valid questions found in CSV for test '{test_id}'.")
            await update.message.reply_text(
                "⛔ Ошибка: Не найдено ни одного корректного вопроса в CSV файле.\n"
                "Проверьте формат, количество колонок (должно быть 6) и заполненность данных. "
                "Отправьте исправленный файл или /cancel."
            )
            return UPLOAD_FILE

    except Exception as e:
        logger.exception(f"Error processing CSV for test '{test_id}': {e}")
        await update.message.reply_text(f"❌ Произошла ошибка при обработке CSV файла: {e}")
        return ConversationHandler.END # End conversation on unexpected error

    # 3. Update Database (Upsert)
    try:
        tests_collection = await get_collection('tests')
        utc_now = datetime.datetime.now(datetime.timezone.utc)

        set_data = {
            'questions': questions_data,
            'total_questions': len(questions_data),
            'uploaded_by_user_id': user_id,
            'upload_timestamp': utc_now,
            'title': f"Тест {test_id}" 
        }
        set_on_insert_data = {'test_id': test_id}

        update_result = await tests_collection.update_one(
            {'test_id': test_id},
            {'$set': set_data, '$setOnInsert': set_on_insert_data},
            upsert=True
        )

        num_q = len(questions_data)
        if update_result.upserted_id:
            logger.info(f"Successfully created test '{test_id}' with {num_q} questions by user {user_id}.")
            await update.message.reply_text(f"✅ Тест '{test_id}' ({num_q} вопр.) успешно создан!")
        elif update_result.modified_count:
             logger.info(f"Successfully updated test '{test_id}' with {num_q} questions by user {user_id}.")
             await update.message.reply_text(f"✅ Тест '{test_id}' ({num_q} вопр.) успешно обновлен!")
        else:
             logger.info(f"Test '{test_id}' data by user {user_id} was identical to existing.")
             await update.message.reply_text(f"ℹ️ Данные для теста '{test_id}' не изменились ({num_q} вопр.).")

        return ConversationHandler.END

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
        return UPLOAD_FILE

    except Exception as e:
        logger.exception(f"Database error saving material for test '{test_id}': {e}")
        await update.message.reply_text(
            f"❌ Ошибка при сохранении файла '{file_name}' в базу данных."
            "\nПопробуйте отправить его снова или /cancel."
        )
        return UPLOAD_FILE


async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the upload operation."""
    user_id = update.effective_user.id if update.effective_user else 'Unknown'
    mode = context.user_data.get('upload_mode', 'unknown')
    logger.info(f"User {user_id} canceled the /upload operation (mode: {mode}).")
    await update.message.reply_text("Загрузка отменена.")
    context.user_data.pop('upload_mode', None)
    context.user_data.pop('test_id', None)
    return ConversationHandler.END


upload_command_handler = ConversationHandler(
    entry_points=[CommandHandler('upload', upload_command)],
    states={
        UPLOAD_FILE: [
            MessageHandler(ATTACHMENT_FILTER, handle_file_upload),
            MessageHandler(filters.TEXT & ~filters.COMMAND, 
                           lambda u, c: u.message.reply_text("Пожалуйста, отправьте файл или используйте /cancel для отмены.")),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_upload)],
)