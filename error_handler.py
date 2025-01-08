from telegram import Update
from telegram.ext import ContextTypes

from logging_config import logger


async def error_handler(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("An error occurred", exc_info=True)
    if update:
        logger.error(f"Update that caused the error: {update}")
