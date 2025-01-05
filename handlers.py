import csv
import random

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    response = await handle_response(text, update, context)
    await update.message.reply_text(response)


async def handle_response(text: str, update: Update, context: CallbackContext):
    responses = load_responses()
    for tag, possible_responses in responses.items():
        if any(keyword in text for keyword in tag.split(',')):
            return random.choice(possible_responses)
    return "I don't understand yet."


def load_responses(file_path='responses.csv'):
    responses = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            responses[row[0]] = row[1:]
    return responses


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print('error')