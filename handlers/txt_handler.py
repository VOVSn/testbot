import io
import datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role
from utils.common_helpers import normalize_test_id


async def txt_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles /txt <test_id> command for admins/teachers to get results as .txt"""
    if not update.effective_user:
        logger.warning('/txt triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {user_id} (@{username}) triggered /txt command.")

    # 1. Check permissions
    user_role = await get_user_role(user_id, username)
    if user_role not in ('admin', 'teacher'):
        logger.warning(
            f"User {user_id} ({user_role}) attempted /txt without privileges."
        )
        await update.message.reply_text(
            "Эта команда доступна только для администраторов и преподавателей."
        )
        return

    # 2. Check arguments
    if not context.args:
        logger.info(f"Missing test_id arg for /txt by user {user_id}.")
        await update.message.reply_text(
            "Пожалуйста, укажите ID теста.\nПример: `/txt math101`"
        )
        return

    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)

    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return

    logger.info(f"{user_role.capitalize()} {user_id} requesting TXT results for '{test_id}'.")

    # 3. Fetch results (using similar logic as _get_test_results_for_teacher)
    allowed_activation_ids = []
    results_list = []
    try:
        # Find relevant activations based on permissions
        active_tests_coll = await get_collection('active_tests')
        activation_filter = {'test_id': test_id}
        if user_role == 'teacher':
            activation_filter['enabled_by_user_id'] = user_id

        cursor = active_tests_coll.find(activation_filter, {'_id': 1})
        async for activation in cursor:
            allowed_activation_ids.append(activation['_id'])

        if not allowed_activation_ids:
            logger.info(
                f"No activations found for test '{test_id}' matching permissions "
                f"for user {user_id} ({user_role})."
            )
            await update.message.reply_text(
                 f"Не найдено результатов для теста '{test_id}' "
                 f"(или у вас нет прав на их просмотр)."
            )
            return

        # Find results for those activations
        results_coll = await get_collection('results')
        results_cursor = results_coll.find(
            {'active_test_id': {'$in': allowed_activation_ids}}
        ).sort([('username', 1), ('end_timestamp', 1)]) # Sort for consistency

        async for result in results_cursor:
             res_username = result.get('username', 'N/A')
             score = result.get('score', 0.0)
             attempt = result.get('attempt_number', 1)
             timestamp = result.get('end_timestamp')
             time_str = timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A'
             results_list.append(
                 f"@{res_username}: Попытка {attempt}, Оценка: {score:.1f}%, Завершен: {time_str}"
             )

        if not results_list:
             logger.info(f"No results found for allowed activations of test '{test_id}'.")
             await update.message.reply_text(f"Не найдено результатов для теста '{test_id}'.")
             return

        # 4. Generate TXT content
        file_content = f"Результаты теста '{test_id}'\n"
        file_content += "=" * (len(file_content) -1) + "\n\n" # Underline
        file_content += "\n".join(results_list)

        # 5. Create in-memory file
        txt_buffer = io.StringIO()
        txt_buffer.write(file_content)
        txt_buffer.seek(0)

        # 6. Send document
        file_name = f'results_{test_id}.txt'
        await update.message.reply_document(
            document=txt_buffer, filename=file_name
        )
        logger.info(f"Sent TXT results for test '{test_id}' to user {user_id}.")

    except Exception as e:
        logger.exception(
            f"Error fetching or generating TXT results for test '{test_id}': {e}"
        )
        await update.message.reply_text(
            "Произошла ошибка при получении результатов теста."
        )


txt_command_handler = CommandHandler('txt', txt_command)