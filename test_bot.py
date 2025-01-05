import csv
import os
import random
from typing import Tuple, List

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackContext, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters
)

from handlers import handle_message, error_handler
from commands import materials_command, results_command

load_dotenv()
token = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
teacher_username = os.getenv('TEACHER_USERNAME')
if not token or not BOT_USERNAME or not teacher_username:
    print('Check .env')
    exit()

GRADES_FOLDER = 'grades'
TESTS_FOLDER = 'tests'


def initialize_test_session(context: CallbackContext, test_id: str):
    questions = load_questions(test_id)
    context.user_data['questions'] = questions
    context.user_data['current_question_index'] = 0
    context.user_data['test_results'] = {'correct': 0, 'total': 0}
    context.user_data['test_id'] = test_id


def load_questions(test_id: str) -> List[List[str]]:
    test_file = os.path.join(TESTS_FOLDER, f'test{test_id}.csv')
    if not os.path.exists(test_file):
        raise FileNotFoundError(f'Test file for {test_id} not found.')

    with open(test_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        questions = list(reader)
        random.shuffle(questions)
        return questions


def get_next_question(context: CallbackContext) -> Tuple[str, InlineKeyboardMarkup]:
    current_question_index = context.user_data.get('current_question_index', 0)
    questions = context.user_data['questions']
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
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    with open(grades_file, 'a', encoding='utf-8') as file:
        file.write(result_string)
    await query.edit_message_text(f'You have completed the test {correct} out of {total}.')
    context.user_data.clear()


async def start_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text('Please provide a test ID. Example: /start 45b7')
        return
    test_id = context.args[0]
    try:
        initialize_test_session(context, test_id)
        question, reply_markup = get_next_question(context)

        if question:
            message = await update.message.reply_text(question, reply_markup=reply_markup)
            context.user_data['last_question_message_id'] = message.message_id
        else:
            await update.message.reply_text('No questions available. Test cannot be started.')
    except FileNotFoundError:
        await update.message.reply_text(f'Test {test_id} not found.')


async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_choice = query.data
    if user_choice == 'cancel':
        await handle_cancel(query, context)
    else:
        await handle_answer(query, context)


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

    print('Starting polling...')
    app.run_polling(poll_interval=2)


if __name__ == '__main__':
    main()
