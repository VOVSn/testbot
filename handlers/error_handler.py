# handlers/error_handler.py (Refactored)

import html
import json
import traceback

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db import get_collection
from logging_config import logger
from settings import ADMIN_USER_ID # Import ADMIN_USER_ID for notifications


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Log the error with traceback
    logger.error(
        "Exception while handling an update:", exc_info=context.error
    )

    # Extract traceback details
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    # Prepare user/update information for logging/messages
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    user_info = "N/A"
    chat_info = "N/A"
    if isinstance(update, Update) and update.effective_user:
        user = update.effective_user
        user_info = f"User ID: {user.id}, Username: @{user.username}"
    if isinstance(update, Update) and update.effective_chat:
        chat = update.effective_chat
        chat_info = f"Chat ID: {chat.id}, Type: {chat.type}"

    # Log concise information first
    logger.error(
        f"Error Details:\n"
        f"  User: {user_info}\n"
        f"  Chat: {chat_info}\n"
        f"  Error: {context.error}\n"
        # Consider limiting traceback length in logs if too verbose
        f"  Traceback:\n{tb_string[:2000]}" # Log first 2000 chars of TB
    )

    # --- Notify User ---
    # Only reply if the error occurred in a context where a message can be sent
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "🤖 Упс! Что-то пошло не так. "
                "Команда уже работает над исправлением. Попробуйте позже. 🙏"
            )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


    # --- Notify Admin  ---
    try:
        # Prepare message for admin
        message = (
            f"‼️ <b>Bot Error Notification</b> ‼️\n\n"
            f"<b>Error:</b> <pre>{html.escape(str(context.error))}</pre>\n\n"
            f"<b>User:</b> {html.escape(user_info)}\n"
            f"<b>Chat:</b> {html.escape(chat_info)}\n\n"
            # Include first part of update and traceback for context
            f"<b>Update:</b>\n<pre>{html.escape(json.dumps(update_str, indent=2, ensure_ascii=False)[:1000])}</pre>\n\n"
            f"<b>Traceback:</b>\n<pre>{html.escape(tb_string[:1500])}</pre>"
        )

        admin_id = int(ADMIN_USER_ID)

        await context.bot.send_message(
            chat_id=admin_id, text=message, parse_mode=ParseMode.HTML
        )
        logger.info(f"Error notification sent to admin ID {admin_id}.")

    except ValueError:
         logger.error(f"Invalid ADMIN_USER_ID ('{ADMIN_USER_ID}') for error notification.")
    except Exception as e:
        logger.exception(f"Failed to send error notification to admin: {e}")