import csv
import os
import random
from typing import Tuple, List

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackContext, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters
)

load_dotenv()
token = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
teacher_username = os.getenv('TEACHER_USERNAME')
if not token or not BOT_USERNAME or not teacher_username:
    print('Check .env')
    exit()

grades_folder = 'grades'
tests_folder = 'tests'
MATERIALS_FOLDER = 'materials'


def initialize_test_session(context: CallbackContext, test_id: str):
    context.user_data['current_question_index'] = 0
    context.user_data['test_results'] = {'correct': 0, 'total': 0}
    context.user_data['test_id'] = test_id


def load_questions(test_id: str) -> List[List[str]]:
    test_file = os.path.join(tests_folder, f'test{test_id}.csv')
    if not os.path.exists(test_file):
        raise FileNotFoundError(f"Test file for {test_id} not found.")

    with open(test_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        return list(reader)


def get_next_question(context: CallbackContext) -> Tuple[str, InlineKeyboardMarkup]:
    current_question_index = context.user_data.get('current_question_index', 0)
    test_id = context.user_data['test_id']
    questions = load_questions(test_id)
    if current_question_index < len(questions):
        selected_line = questions[current_question_index]
        return updated_inline_keyboard(context, selected_line)
    return None, None


def updated_inline_keyboard(context: CallbackContext, selected_line: List[str]) -> Tuple[str, InlineKeyboardMarkup]:
    question = selected_line[0]
    choices = selected_line[2:6]
    random.shuffle(choices)
    context.user_data['right_answer'] = selected_line[1]
    keyboard = [
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[:2]],
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[2:]],
        [InlineKeyboardButton("Cancel", callback_data='cancel')],
    ]
    return question, InlineKeyboardMarkup(keyboard)


async def handle_cancel(query, context):
    last_question_message_id = context.user_data.get('last_question_message_id')
    if last_question_message_id:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=last_question_message_id,
            text="Test is cancelled.",
            reply_markup=None
        )
    else:
        await query.answer("Test cancelled.")
    context.user_data.clear()


async def handle_answer(query, context):
    right_answer = context.user_data.get('right_answer')
    user_data = context.user_data.setdefault('test_results', {'correct': 0, 'total': 0})
    if query.data == right_answer:
        await query.answer("Right!")
        user_data['correct'] += 1
    else:
        await query.answer("Wrong!")
    user_data['total'] += 1
    context.user_data['current_question_index'] += 1
    question, reply_markup = get_next_question(context)
    if question:
        await query.edit_message_text(question, reply_markup=reply_markup)
    else:
        await display_results(query, context)


async def display_results(query, context):
    correct = context.user_data['test_results']['correct']
    total = context.user_data['test_results']['total']
    test_id = context.user_data['test_id']
    user_username = query.from_user.username
    result_string = f"{user_username}: {correct} out of {total}\n"
    grades_file = os.path.join(grades_folder, f'grades{test_id}.txt')
    with open(grades_file, 'a', encoding='utf-8') as file:
        file.write(result_string)
    await query.edit_message_text(f"You have completed the test {correct} out of {total}.")
    context.user_data.clear()


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    if user_username != context.bot_data.get('teacher_username'):
        await update.message.reply_text("Only for the teacher.")
        return
    if not context.args:
        await update.message.reply_text("Correct use: /results <test_id>")
        return

    test_id = context.args[0]
    grades_file = os.path.join(grades_folder, f'grades{test_id}.txt')
    if not os.path.exists(grades_file):
        await update.message.reply_text(f"No results found for test {test_id}.")
        return
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()
    await update.message.reply_text(results)


async def materials_command(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Correct use: /materials <test_id>")
        return
    test_id = context.args[0]
    materials_folder_id = os.path.join(MATERIALS_FOLDER, test_id)
    if not os.path.exists(materials_folder_id):
        await update.message.reply_text(f"No materials found for test {test_id}.")
        return
    files = [file for file in os.listdir(materials_folder_id) if os.path.isfile(os.path.join(materials_folder_id, file))]
    if not files:
        await update.message.reply_text(f"No materials available for test {test_id}.")
        return
    for file in files: 
        file_path = os.path.join(materials_folder_id, file)
        await update.message.reply_document(document=open(file_path, 'rb'))


async def start_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("Please provide a test ID. Example: /start 45b7")
        return
    test_id = context.args[0]
    try:
        initialize_test_session(context, test_id)
        question, reply_markup = get_next_question(context)

        if question:
            message = await update.message.reply_text(question, reply_markup=reply_markup)
            context.user_data['last_question_message_id'] = message.message_id
        else:
            await update.message.reply_text("No questions available. Test cannot be started.")
    except FileNotFoundError:
        await update.message.reply_text(f"Test {test_id} not found.")


async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_choice = query.data
    if user_choice == 'cancel':
        await handle_cancel(query, context)
    else:
        await handle_answer(query, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    response = await handle_response(text, update, context)
    await update.message.reply_text(response)


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
        next(reader)
        for row in reader:
            responses[row[0]] = row[1:]
    return responses


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print('error')


def main():
    app = Application.builder().token(token).build()
    app.bot_data['teacher_username'] = teacher_username
    handlers = [
        (CommandHandler('start', start_command)),
        (CommandHandler('materials', materials_command)),
        (CommandHandler('results', results_command)),
        (CallbackQueryHandler(button_callback)),
        (MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)),
    ]
    for handler in handlers:
        app.add_handler(handler)
    app.add_error_handler(error_handler)

    print("Starting polling...")
    app.run_polling(poll_interval=1)


if __name__ == '__main__':
    main()
