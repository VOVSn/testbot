# handlers/test_handler.py (Refactored)

import random
import datetime
from typing import List, Dict, Any, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode

from db import get_collection
from logging_config import logger
from utils.common_helpers import normalize_test_id

# Conversation states
ASKING_QUESTION = range(1)

# Callback data prefixes or constants
ANSWER_PREFIX = 'ans_'
CANCEL_TEST = 'cancel_test'


async def test_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    """Entry point for the /test command and conversation."""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    username = update.effective_user.username

    # 1. Argument check
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажите ID теста.\nПример: `/test math101`"
        )
        return ConversationHandler.END

    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)
    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return ConversationHandler.END

    logger.info(f"User {user_id} (@{username}) attempting to start test '{test_id}'.")

    # 2. Find active test activation
    now = datetime.datetime.now(datetime.timezone.utc)
    active_tests_coll = await get_collection('active_tests')
    activation = await active_tests_coll.find_one({
        'test_id': test_id,
        'start_time': {'$lte': now},
        'end_time': {'$gte': now}
    }) # Consider sorting if multiple could be active, maybe by start_time desc

    if not activation:
        logger.warning(f"No active session found for test '{test_id}' for user {user_id}.")
        await update.message.reply_text(f"Тест '{test_id}' в данный момент не активен или недоступен.")
        return ConversationHandler.END

    active_test_id = activation['_id']
    max_tries = activation.get('max_tries', 1)
    num_questions_to_ask = activation.get('num_questions_to_ask', 10) # Default

    # 3. Check attempts
    results_coll = await get_collection('results')
    previous_attempts = await results_coll.count_documents({
        'user_id': user_id,
        'active_test_id': active_test_id
    })

    if previous_attempts >= max_tries:
        logger.info(f"User {user_id} exceeded max tries ({max_tries}) for test '{test_id}' (activation {active_test_id}).")
        await update.message.reply_text(
            f"Вы уже использовали все доступные попытки ({max_tries}) для этого теста."
        )
        return ConversationHandler.END

    attempt_number = previous_attempts + 1
    logger.info(f"User {user_id} starting attempt {attempt_number}/{max_tries} for test '{test_id}' (activation {active_test_id}).")

    # 4. Load base test questions
    tests_coll = await get_collection('tests')
    base_test = await tests_coll.find_one(
        {'test_id': test_id},
        {'questions': 1} # Only need the questions array
    )

    if not base_test or not base_test.get('questions'):
        logger.error(f"Base test '{test_id}' not found or has no questions in DB.")
        await update.message.reply_text("Ошибка: не найдены вопросы для этого теста.")
        return ConversationHandler.END

    all_questions = base_test['questions']
    total_in_bank = len(all_questions)

    if total_in_bank == 0:
        logger.error(f"Test bank for '{test_id}' is empty.")
        await update.message.reply_text("Ошибка: в банке нет вопросов для этого теста.")
        return ConversationHandler.END

    # 5. Select questions for this session
    num_to_select = min(num_questions_to_ask, total_in_bank)
    selected_questions_indices = random.sample(range(total_in_bank), num_to_select)
    questions_for_session = []
    for index in selected_questions_indices:
         # Store original index for results reporting if needed
         q_data = all_questions[index]
         q_data['original_index'] = index
         questions_for_session.append(q_data)

    # Shuffle the selected questions for this session
    random.shuffle(questions_for_session)

    # 6. Initialize user_data for the conversation
    context.user_data.clear() # Ensure clean state
    context.user_data['active_test_id'] = active_test_id
    context.user_data['test_id'] = test_id
    context.user_data['questions_for_session'] = questions_for_session
    context.user_data['current_q_index'] = 0
    context.user_data['score'] = 0
    context.user_data['answers'] = [] # To store {q_original_idx, selected_idx, correct}
    context.user_data['attempt_number'] = attempt_number
    context.user_data['test_start_time'] = now # Record start time

    logger.debug(f"User {user_id} test session initialized: {context.user_data}")

    # 7. Send the first question
    await _send_question(update, context)
    return ASKING_QUESTION


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles callback queries with answers."""
    query = update.callback_query
    await query.answer() # Acknowledge callback

    if not context.user_data or 'questions_for_session' not in context.user_data:
        logger.warning(f"Received callback query but user_data is missing/incomplete for user {query.from_user.id}. Ending conversation.")
        await query.edit_message_text("Произошла ошибка состояния теста. Пожалуйста, начните заново с /test.")
        return ConversationHandler.END

    user_choice_data = query.data
    user_id = query.from_user.id

    # Check for cancellation first
    if user_choice_data == CANCEL_TEST:
        return await _cancel_test(update, context, query)

    # Extract chosen answer index
    try:
        # Assumes callback data is like "ans_0", "ans_1", etc.
        chosen_option_index = int(user_choice_data.split('_')[-1])
    except (ValueError, IndexError):
        logger.error(f"Invalid callback data format received: {user_choice_data} from user {user_id}.")
        # Maybe inform user or just ignore? For now, ignore and don't proceed.
        return ASKING_QUESTION # Stay in state, don't crash

    # Get current question details
    current_q_index = context.user_data.get('current_q_index', 0)
    questions = context.user_data['questions_for_session']
    current_question = questions[current_q_index]
    correct_option_index = current_question.get('correct_option_index', -1)
    original_index = current_question.get('original_index', -1)

    # Record answer
    is_correct = (chosen_option_index == correct_option_index)
    context.user_data['answers'].append({
        'question_index_in_bank': original_index,
        'selected_option_index': chosen_option_index,
        'is_correct': is_correct
    })

    if is_correct:
        context.user_data['score'] += 1
        logger.info(f"User {user_id} answered Q{current_q_index+1} correctly.")
    else:
        logger.info(f"User {user_id} answered Q{current_q_index+1} incorrectly.")

    # Move to next question
    context.user_data['current_q_index'] += 1

    # Check if test finished
    if context.user_data['current_q_index'] >= len(questions):
        return await _finish_test(update, context, query)
    else:
        # Send next question
        await _send_question(update, context, query) # Pass query to edit message
        return ASKING_QUESTION


async def _send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, query: Any = None):
    """Sends the current question or edits the message for the next question."""
    current_q_index = context.user_data['current_q_index']
    questions = context.user_data['questions_for_session']
    question_data = questions[current_q_index]
    test_id = context.user_data['test_id']

    q_text = question_data.get('question_text', 'Error: Missing question text')
    options = question_data.get('options', [])

    # Shuffle options for presentation, but keep track of original indices for callback data
    indexed_options = list(enumerate(options)) # [(0, 'OptA'), (1, 'OptB'), ...]
    random.shuffle(indexed_options)

    keyboard = []
    row = []
    for original_index, option_text in indexed_options:
        button = InlineKeyboardButton(
            option_text,
            # Use prefix and ORIGINAL index in callback data
            callback_data=f"{ANSWER_PREFIX}{original_index}"
        )
        row.append(button)
        # Create rows of 2 buttons max
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: # Add remaining button if odd number
        keyboard.append(row)

    # Add cancel button
    keyboard.append([InlineKeyboardButton('❌ Отмена', callback_data=CANCEL_TEST)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    total_questions = len(questions)
    question_number = current_q_index + 1
    formatted_question = (
        f"📝 *Тест: {test_id}* ({context.user_data['attempt_number']}-я попытка)\n\n"
        f"*Вопрос {question_number} из {total_questions}:*\n\n"
        f"{q_text}"
    )

    try:
        if query: # Edit previous message if handling a callback
            message = await query.edit_message_text(
                text=formatted_question,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['last_message_id'] = message.message_id
        elif update.message: # Send new message if it's the start
            message = await update.message.reply_text(
                text=formatted_question,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['last_message_id'] = message.message_id
        else:
             logger.error("Cannot send question: No query or message context available.")

    except Exception as e:
         logger.exception(f"Error sending/editing question {question_number} for user {context._user_id}: {e}")
         # Try sending a simple error message?
         if query:
             await query.message.reply_text("Ошибка при отображении вопроса.")
         elif update.message:
             await update.message.reply_text("Ошибка при отображении вопроса.")
         # Consider ending the conversation here if sending fails


async def _finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE, query: Any) -> int:
    """Calculates results, saves them to DB, and informs the user."""
    user_id = query.from_user.id
    username = query.from_user.username
    score = context.user_data['score']
    total_questions = len(context.user_data['questions_for_session'])
    test_id = context.user_data['test_id']
    active_test_id = context.user_data['active_test_id']
    attempt_number = context.user_data['attempt_number']
    answers = context.user_data['answers']
    start_time = context.user_data['test_start_time']
    end_time = datetime.datetime.now(datetime.timezone.utc)

    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    percentage_str = f"{percentage:.1f}"

    logger.info(
        f"User {user_id} finished test '{test_id}' (activation {active_test_id}, "
        f"attempt {attempt_number}): Score {score}/{total_questions} ({percentage_str}%)"
    )

    # Save result to database
    result_doc = {
        'user_id': user_id,
        'username': username,
        'test_id': test_id,
        'active_test_id': active_test_id,
        'attempt_number': attempt_number,
        'score': percentage, # Store percentage score
        'correct_count': score,
        'total_questions': total_questions,
        'selected_answers': answers,
        'start_timestamp': start_time,
        'end_timestamp': end_time
    }
    try:
        results_coll = await get_collection('results')
        await results_coll.insert_one(result_doc)
        logger.info(f"Result for user {user_id}, test '{test_id}' saved to DB.")
    except Exception as e:
        logger.exception(f"Failed to save result to DB for user {user_id}, test '{test_id}': {e}")
        # Inform user about the error saving?
        await query.edit_message_text("Тест завершен, но произошла ошибка при сохранении вашего результата.")
        context.user_data.clear()
        return ConversationHandler.END

    # Inform user
    final_message = (
        f"🎉 Тест '{test_id}' завершен!\n\n"
        f"Ваш результат: {score} из {total_questions} ({percentage_str}%)\n\n"
        f"Вы можете посмотреть все свои результаты командой /results."
    )
    await query.edit_message_text(text=final_message, reply_markup=None)

    # Clean up user_data
    context.user_data.clear()
    return ConversationHandler.END


async def _cancel_test(update: Update, context: ContextTypes.DEFAULT_TYPE, query: Any) -> int:
    """Handles test cancellation."""
    user_id = query.from_user.id
    test_id = context.user_data.get('test_id', 'N/A')
    logger.warning(f"User {user_id} cancelled test '{test_id}'.")

    await query.edit_message_text(text="Тест отменен. 🚫", reply_markup=None)
    context.user_data.clear()
    return ConversationHandler.END


# Define the ConversationHandler
test_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('test', test_command)],
    states={
        ASKING_QUESTION: [
            CallbackQueryHandler(handle_answer) # Handles answer buttons and cancel
        ],
    },
    fallbacks=[
        CommandHandler('cancel', _cancel_test), # Allow cancelling via command too
        # Add other fallbacks if needed (e.g., unexpected text messages)
    ],
    # Optional: define how conversation data is stored (default is memory)
    # persistent=False, # Or use a different storage backend if needed
    # Allow re-entry if user starts /test again while in conversation?
    # allow_reentry=True # Be careful with state if allowing re-entry
)