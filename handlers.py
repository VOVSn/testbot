import csv
import random
import logging

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

# Configure logging
logging.basicConfig(
    filename='test_bot.log',
    level=logging.WARNING,  # Adjust the level as needed (DEBUG, INFO, etc.)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username
    logger.info(f"Received message from user {user_id} ({user_name}): {text}")
    
    response = await handle_response(text, update, context)
    await update.message.reply_text(response)
    logger.info(f"Sent response to user {user_id}: {response}")


async def handle_response(text: str, update: Update, context: CallbackContext):
    responses = load_responses()
    for tag, possible_responses in responses.items():
        if any(keyword in text for keyword in tag.split(',')):
            response = random.choice(possible_responses)
            logger.debug(f"Matched tag '{tag}' for text '{text}'. Response: '{response}'")
            return response
    logger.warning(f"No match found for text '{text}'")
    return "I don't understand yet."


def load_responses(file_path='responses.csv'):
    responses = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row
            for row in reader:
                responses[row[0]] = row[1:]
        logger.info(f"Successfully loaded responses from {file_path}")
    except FileNotFoundError:
        logger.error(f"Response file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading responses from {file_path}: {e}")
    return responses


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("An error occurred", exc_info=True)
    if update:
        logger.error(f"Update that caused the error: {update}")
