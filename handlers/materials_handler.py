from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import BadRequest

from db import get_collection
from logging_config import logger
from utils.common_helpers import normalize_test_id


async def materials_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles /materials command, sending stored files using file_ids."""
    if not update.effective_user or not update.effective_chat:
        logger.warning('/materials triggered with no user/chat info.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    chat_id = update.effective_chat.id

    logger.info(f"User {user_id} (@{username}) triggered /materials command.")

    if not context.args:
        logger.info(f"Missing test_id arg for /materials by user {user_id}.")
        await update.message.reply_text("Пожалуйста, укажите ID теста.\nПример: `/materials math101`")
        return

    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)

    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return

    logger.info(f"User {user_id} requesting materials for test_id '{test_id}'.")

    materials_found = False
    try:
        materials_collection = await get_collection('materials')
        cursor = materials_collection.find({'test_id': test_id})

        async for material in cursor:
            materials_found = True
            file_id = material.get('telegram_file_id')
            file_type = material.get('file_type', 'document') # Default to doc
            file_name = material.get('file_name', 'material') # Default name

            if not file_id:
                logger.warning(
                    f"Material entry for test {test_id} is missing file_id:"
                    f" {material.get('_id')}"
                )
                continue

            try:
                logger.debug(f"Attempting to send {file_type} (ID: {file_id}) for test {test_id} to chat {chat_id}")
                # Choose send method based on type
                if file_type == 'photo':
                    await context.bot.send_photo(chat_id=chat_id, photo=file_id, caption=file_name)
                elif file_type == 'video':
                    await context.bot.send_video(chat_id=chat_id, video=file_id, caption=file_name)
                elif file_type == 'audio':
                    await context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=file_name)
                # Default to document for 'document' or unknown types
                else:
                     await context.bot.send_document(chat_id=chat_id, document=file_id, filename=file_name)

                logger.info(f"Sent material '{file_name}' (ID: {file_id}) for test {test_id} to user {user_id}.")

            except BadRequest as e:
                # Common errors: file_id expired/invalid, bot blocked
                logger.error(
                    f"BadRequest sending material (ID: {file_id}, Type: {file_type})"
                    f" for test {test_id} to user {user_id}: {e}"
                )
                # Notify user about the specific file failure
                await update.message.reply_text(
                    f"Не удалось отправить материал '{file_name}'. Возможно, файл был удален или поврежден."
                )
            except Exception as e:
                logger.exception(
                    f"Unexpected error sending material (ID: {file_id})"
                    f" for test {test_id} to user {user_id}: {e}"
                )
                await update.message.reply_text(f"Ошибка при отправке материала '{file_name}'.")

        # After the loop, check if any materials were processed
        if not materials_found:
            logger.info(f"No materials found for test_id '{test_id}'.")
            await update.message.reply_text(f"🤷‍♂️ Не найдено материалов для теста '{test_id}'.")

    except Exception as e:
        logger.exception(f"Database error fetching materials for test {test_id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка при поиске материалов теста."
        )


materials_command_handler = CommandHandler('materials', materials_command)