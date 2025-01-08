from telegram import Update
from telegram.ext import ContextTypes
from logging_config import logger


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Log the error with traceback
    logger.error("An error occurred", exc_info=True)

    # Log details of the update if available
    if update:
        logger.error(f"Update that caused the error: {update}")

        # Include user details if possible
        if update.effective_user:
            user = update.effective_user
            logger.error(
                f"Error triggered by user {user.id} (@{user.username})")

    # Notify the user about the error gracefully
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Упс! Произошла ошибка. Мы работаем над её исправлением. "
            "Попробуйте позже. 🙏"
        )
