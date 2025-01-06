import csv
import os
import random
from typing import Tuple, List
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from logging_config import logger


GRADES_FOLDER = 'grades'
TESTS_FOLDER = 'tests'


def initialize_test_session(context: CallbackContext, test_id: str):
    logger.info(f"Initializing test session for test ID {test_id}")
    questions = load_questions(test_id)
    context.user_data['questions'] = questions
    context.user_data['current_question_index'] = 0
    context.user_data['test_results'] = {'correct': 0, 'total': 0}
    context.user_data['test_id'] = test_id
    logger.info(f"Test session for test ID {test_id} initialized with {len(questions)} questions.")


def load_questions(test_id: str) -> List[List[str]]:
    test_file = os.path.join(TESTS_FOLDER, f'test{test_id}.csv')
    if not os.path.exists(test_file):
        logger.error(f"Test file {test_id} not found at {test_file}.")
        raise FileNotFoundError(f'Файл теста {test_id} не найден.')

    with open(test_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        questions = list(reader)
        random.shuffle(questions)
        logger.info(f"Loaded {len(questions)} questions from test {test_id}.")
        return questions


def get_next_question(context: CallbackContext) -> Tuple[str, InlineKeyboardMarkup]:
    current_question_index = context.user_data.get('current_question_index', 0)
    questions = context.user_data['questions']
    if current_question_index < len(questions):
        selected_line = questions[current_question_index]
        logger.info(f"Fetching question {current_question_index + 1}.")
        return updated_inline_keyboard(context, selected_line)
    logger.info("No more questions to display.")
    return None, None


def updated_inline_keyboard(context: CallbackContext, selected_line: List[str]) -> Tuple[str, InlineKeyboardMarkup]:
    question = selected_line[0]
    choices = selected_line[2:6]
    random.shuffle(choices)
    context.user_data['right_answer'] = selected_line[1]
    keyboard = [
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[:2]],
        [InlineKeyboardButton(choice, callback_data=choice) for choice in choices[2:]],
        [InlineKeyboardButton('Отмена', callback_data='cancel')],
    ]
    return question, InlineKeyboardMarkup(keyboard)


async def handle_cancel(query, context):
    logger.warning(f"Test canceled by user {query.from_user.username}.")
    last_question_msg_id = context.user_data.get('last_question_message_id')
    if last_question_msg_id:
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=last_question_msg_id,
            text="Тест отменен.",
            reply_markup=None
        )
    else:
        await query.answer("Тест отменен.")
    context.user_data.clear()


async def handle_answer(query, context):
    right_answer = context.user_data.get('right_answer')
    user_data = context.user_data.setdefault(
        'test_results', {'correct': 0, 'total': 0}
    )
    if query.data == right_answer:
        logger.info(f"User {query.from_user.username} answered correctly.")
        await query.answer('ВЕРНО!')
        user_data['correct'] += 1
    else:
        logger.info(f"User {query.from_user.username} answered incorrectly.")
        await query.answer('НЕВЕРНО')
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
    user_first_name = query.from_user.first_name  # Fetch the first name
    
    # Calculate the percentage of correct answers
    if total > 0:
        percentage = (correct / total) * 100
    else:
        percentage = 0

    # Format the percentage with 2 decimal places
    percentage_str = f"{percentage:.1f}"

    gmt_plus_3_timezone = timezone(timedelta(hours=3))
    gmt_plus_3_time = datetime.now(gmt_plus_3_timezone)
    timestamp = gmt_plus_3_time.strftime("%Y-%m-%d %H:%M")
    
    # Include percentage in the result string
    result_string = f"{timestamp} - {user_first_name}({user_username}): {correct} из {total} [{percentage_str}%]\n"
    
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    with open(grades_file, 'a', encoding='utf-8') as file:
        file.write(result_string)
    
    logger.info(f"Test {test_id} completed by user {user_first_name}({user_username}): {correct} out of {total} [{percentage_str}%].")
    
    await query.edit_message_text(
        f'Вы завершили тест, правильно {correct} из {total} [{percentage_str}%].')
    
    context.user_data.clear()



async def test_command(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text(
            'Пожалуйста, введите номер теста, например: /test 2')
        return

    test_id = context.args[0]
    try:
        initialize_test_session(context, test_id)
        question, reply_markup = get_next_question(context)

        if question:
            message = await update.message.reply_text(
                question, reply_markup=reply_markup)
            context.user_data['last_question_message_id'] = message.message_id
        else:
            await update.message.reply_text('Нет вопросов в тесте!')
    except FileNotFoundError:
        logger.error(f"Test {test_id} not found.")
        await update.message.reply_text(f'Тест {test_id} не найден.')


async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_choice = query.data
    if user_choice == 'cancel':
        await handle_cancel(query, context)
    else:
        await handle_answer(query, context)
