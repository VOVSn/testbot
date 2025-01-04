import csv
import logging
import os
import random
from typing import Tuple, List

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler
)


# Load environment variables from .env file
load_dotenv()

# Retrieve values from environment variables
token = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
teacher_username = os.getenv('TEACHER_USERNAME')

if not token or not BOT_USERNAME or not teacher_username:
    print("Please check your .env file.")
    exit()

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = "log_file_01.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Load questions from CSV file
def load_questions():
    with open('test.csv', 'r') as file:
        reader = csv.reader(file)
        return list(reader)

# Helper functions for modularization


def initialize_test_session(context: CallbackContext):
    """Initialize a new test session for the user."""
    context.user_data['current_question_index'] = 0
    context.user_data['test_results'] = {'correct': 0, 'total': 0}


def get_next_question(context: CallbackContext) -> Tuple[str, InlineKeyboardMarkup]:
    """Retrieve the next question and keyboard from the CSV file."""
    current_question_index = context.user_data.get('current_question_index', 0)
    questions = load_questions()

    if current_question_index < len(questions):
        selected_line = questions[current_question_index]
        return updated_inline_keyboard(context, selected_line)
    return None, None


def updated_inline_keyboard(context: CallbackContext, selected_line: List[str]) -> Tuple[str, InlineKeyboardMarkup]:
    """Create an inline keyboard for the given question."""
    question = selected_line[0]
    choices = selected_line[2:6]
    random.shuffle(choices)

    # Store correct answer in user context
    context.user_data['right_answer'] = selected_line[1]

    keyboard = [
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[:2]],
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[2:]],
        [InlineKeyboardButton("Cancel", callback_data='cancel')],
    ]
    return question, InlineKeyboardMarkup(keyboard)


async def handle_cancel(query, context):
    """Handle the 'cancel' action during the test."""
    last_question_message_id = context.user_data.get('last_question_message_id')
    if last_question_message_id:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=last_question_message_id,
            text="Test is cancelled.",
            reply_markup=None
        )
    else:
        await query.answer("Test is cancelled.")
    context.user_data.clear()


async def handle_answer(query, context):
    """Validate the user's answer and proceed to the next question."""
    right_answer = context.user_data.get('right_answer')
    user_data = context.user_data.setdefault('test_results', {'correct': 0, 'total': 0})

    if query.data == right_answer:
        await query.answer("You are right!")
        user_data['correct'] += 1
    else:
        await query.answer("You are wrong!")

    user_data['total'] += 1
    context.user_data['current_question_index'] += 1

    question, reply_markup = get_next_question(context)
    if question:
        await query.edit_message_text(question, reply_markup=reply_markup)
    else:
        await display_results(query, context)


async def display_results(query, context):
    """Send the final results to the user and save them to grades.txt."""
    correct = context.user_data['test_results']['correct']
    total = context.user_data['test_results']['total']

    # Prepare result string
    user_username = query.from_user.username
    result_string = f"{user_username}: {correct} out of {total}\n"

    # Save the results to grades.txt
    with open('grades.txt', 'a') as file:
        file.write(result_string)

    await query.edit_message_text(f"You have completed the test {correct} out of {total}.")
    context.user_data.clear()


# Commands
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("To start the test, press /start")


async def custom_command(update: Update, context: CallbackContext) -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    materials_folder = os.path.join(current_dir, "materials")
    files = [file for file in os.listdir(materials_folder) if os.path.isfile(os.path.join(materials_folder, file))]

    if not files:
        await update.message.reply_text("No materials available.")
        return

    for file in files:
        file_path = os.path.join(materials_folder, file)
        await update.message.reply_document(document=open(file_path, 'rb'))


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    if user_username != context.bot_data.get('teacher_username'):
        await update.message.reply_text("Only for the teacher.")
        return

    with open('grades.txt', 'r') as file:
        results = file.read()
    await update.message.reply_text(results)


async def start_command(update: Update, context: CallbackContext):
    initialize_test_session(context)
    question, reply_markup = get_next_question(context)

    if question:
        message = await update.message.reply_text(question, reply_markup=reply_markup)
        context.user_data['last_question_message_id'] = message.message_id
    else:
        await update.message.reply_text("No questions available. Test cannot be started.")


# Callback handlers
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_choice = query.data

    if user_choice == 'cancel':
        await handle_cancel(query, context)
    else:
        await handle_answer(query, context)


# Handling user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    response = await handle_response(text, update, context)
    await update.message.reply_text(response)


# Response loader
async def handle_response(text: str, update: Update, context: CallbackContext) -> str:
    responses = load_responses()
    for tag, possible_responses in responses.items():
        if any(keyword in text for keyword in tag.split(',')):
            return random.choice(possible_responses)
    return "I don't understand yet."


def load_responses(file_path='responses.csv'):
    responses = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        for row in reader:
            responses[row[0]] = row[1:]
    return responses


# Error handling
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")


# Main
if __name__ == '__main__':
    app = Application.builder().token(token).build()

    # Set teacher username in bot data
    app.bot_data['teacher_username'] = teacher_username

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("materials", custom_command))
    app.add_handler(CommandHandler("results", results_command))

    # Callback handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
   
    app.add_error_handler(error_handler)

    print("Starting polling...")
    app.run_polling(poll_interval=1)
