import csv
import random
import os

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from logging_config import logger

# Constants
RESPONSES_FILE = 'responses.csv'
DEFAULT_RESPONSE = 'Я пока не понимаю 🤖'


def load_responses(file_path: str = RESPONSES_FILE) -> dict[str, list[str]]:
    """Loads keyword-response mappings from a CSV file."""
    responses_map: dict[str, list[str]] = {}
    if not os.path.exists(file_path):
        logger.error(f'Response file not found: {file_path}')
        return responses_map

    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=';')
            try:
                header = next(reader)  # Read header
                logger.debug(f'Response CSV header: {header}')
            except StopIteration:
                logger.warning(f'Response file is empty: {file_path}')
                return responses_map

            for i, row in enumerate(reader, start=1):
                if not row or len(row) < 2 or not row[0].strip():
                    logger.warning(f'Skipping invalid row {i+1} in {file_path}: {row}')
                    continue
                tags = row[0].lower().strip()
                possible_responses = [resp.strip() for resp in row[1:] if resp.strip()]
                if tags and possible_responses:
                    responses_map[tags] = possible_responses
                else:
                    logger.warning(f'Skipping row {i+1} in {file_path} due to missing tags or responses.')

        logger.info(f'Successfully loaded {len(responses_map)} response mappings from {file_path}')

    except csv.Error as e:
        logger.error(f'CSV parsing error in {file_path} (delimiter=";"): {e}')
    except Exception as e:
        logger.exception(f'Unexpected error loading responses from {file_path}: {e}')

    return responses_map

# Load responses once when the module is imported
loaded_responses = load_responses()


def get_response(text: str) -> str:
    """Finds a random response matching keywords in the text."""
    lower_text = text.lower() # Process text once

    for tags, possible_responses in loaded_responses.items():
        # Check if any keyword from the tag list is present in the message
        keywords = [kw.strip() for kw in tags.split(',')]
        if any(keyword in lower_text for keyword in keywords if keyword):
            selected_response = random.choice(possible_responses)
            logger.debug(f"Matched tags '{tags}' for text '{text}'. Sending: '{selected_response}'")
            return selected_response

    # No match found
    logger.info(f"No response keyword match found for text: '{text}'")
    return DEFAULT_RESPONSE


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text messages (not commands)."""
    # Basic guard clauses
    if not update.message or not update.message.text or not update.effective_user:
        return

    message_text = update.message.text
    user = update.effective_user
    logger.info(f'Received message from user {user.id} (@{user.username}): "{message_text}"')

    # Get response based on text content
    response_text = get_response(message_text)

    # Send the reply
    await update.message.reply_text(response_text)
    logger.info(f'Sent response to user {user.id}: "{response_text}"')


# Define the handler
message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)