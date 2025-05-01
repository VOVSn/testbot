import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role
from utils.common_helpers import normalize_test_id


async def results_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles /results command for viewing own or specific test results."""
    if not update.effective_user:
        logger.warning('/results triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {user_id} (@{username}) triggered /results command.")

    user_role = await get_user_role(user_id, username)

    # --- Branch 1: Admin/Teacher requests results for a specific test ---
    if context.args:
        if user_role not in ('admin', 'teacher'):
            logger.warning(
                f"User {user_id} ({user_role}) attempted "
                f"/results <test_id> without privileges."
            )
            await update.message.reply_text(
                "Эта команда доступна только для администраторов и преподавателей."
            )
            return

        raw_test_id = context.args[0]
        test_id = normalize_test_id(raw_test_id)

        if not test_id:
            await update.message.reply_text("Некорректный ID теста.")
            return

        logger.info(
            f"{user_role.capitalize()} {user_id} requesting results "
            f"for test_id '{test_id}'."
        )

        results_text = await _get_test_results_for_teacher(test_id, user_id, user_role)
        if not results_text:
             await update.message.reply_text(
                 f"Не найдено результатов для теста '{test_id}' "
                 f"(или у вас нет прав на их просмотр)."
             )
        else:
            # Split long messages if necessary (Telegram limit is 4096 chars)
            for chunk in _split_message(results_text):
                 await update.message.reply_text(chunk)

    # --- Branch 2: Any user requests their own results ---
    else:
        logger.info(f"User {user_id} requesting own results.")
        results_text = await _get_own_results(user_id)
        if not results_text:
             await update.message.reply_text("У вас пока нет результатов.")
        else:
             for chunk in _split_message(results_text):
                  await update.message.reply_text(chunk)


async def _get_test_results_for_teacher(
    test_id: str, teacher_user_id: int, teacher_role: str
) -> str:
    """Fetches and formats results for a specific test, checking permissions."""
    allowed_activation_ids = []
    try:
        # 1. Find relevant activations
        active_tests_coll = await get_collection('active_tests')
        activation_filter = {'test_id': test_id}
        # Admins see all activations for the test_id
        # Teachers only see activations they enabled
        if teacher_role == 'teacher':
            activation_filter['enabled_by_user_id'] = teacher_user_id

        cursor = active_tests_coll.find(activation_filter, {'_id': 1})
        async for activation in cursor:
            allowed_activation_ids.append(activation['_id'])

        if not allowed_activation_ids:
            logger.info(
                f"No activations found for test '{test_id}' matching "
                f"permissions for user {teacher_user_id} ({teacher_role})."
            )
            return ""

        # 2. Find results for those activations
        results_coll = await get_collection('results')
        # Sort by username, then timestamp/attempt number for clarity
        results_cursor = results_coll.find(
            {'active_test_id': {'$in': allowed_activation_ids}}
        ).sort([('username', 1), ('end_timestamp', 1)])

        results_list = []
        async for result in results_cursor:
            username = result.get('username', 'N/A')
            score = result.get('score', 0.0)
            attempt = result.get('attempt_number', 1)
            # Format timestamp nicely (adjust timezone/format as needed)
            timestamp = result.get('end_timestamp')
            time_str = timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A'

            results_list.append(
                f"@{username}: Попытка {attempt}, Оценка: {score:.1f}%, Завершен: {time_str}"
            )

        if not results_list:
            logger.info(f"No results found for allowed activations of test '{test_id}'.")
            return ""

        return f"📊 Результаты теста '{test_id}':\n\n" + "\n".join(results_list)

    except Exception as e:
        logger.exception(f"DB error fetching results for test '{test_id}' for teacher {teacher_user_id}: {e}")
        return "Произошла ошибка при получении результатов теста."


async def _get_own_results(user_id: int) -> str:
    """Fetches and formats results for the requesting user."""
    try:
        results_coll = await get_collection('results')
        results_cursor = results_coll.find({'user_id': user_id}).sort('end_timestamp', -1) # Newest first

        results_list = []
        async for result in results_cursor:
            test_id = result.get('test_id', 'N/A')
            score = result.get('score', 0.0)
            attempt = result.get('attempt_number', 1)
            timestamp = result.get('end_timestamp')
            time_str = timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A'

            results_list.append(
                f"Тест '{test_id}': Попытка {attempt}, Оценка: {score:.1f}%, Завершен: {time_str}"
            )

        if not results_list:
            logger.info(f"No results found for user {user_id}.")
            return ""

        return "📈 Ваши результаты:\n\n" + "\n".join(results_list)

    except Exception as e:
        logger.exception(f"DB error fetching own results for user {user_id}: {e}")
        return "Произошла ошибка при получении ваших результатов."


def _split_message(text: str, chunk_size: int = 4000) -> list[str]:
    """Splits a long message into chunks respecting line breaks."""
    chunks = []
    current_chunk = ""
    for line in text.splitlines(keepends=True):
        if len(current_chunk) + len(line) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += line
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


results_command_handler = CommandHandler('results', results_command)