# handlers/list_tests_handler.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role


async def list_tests_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lists all available test banks (IDs, titles, question counts)."""
    if not update.effective_user:
        logger.warning('/list_tests triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username

    # Allow Admins and Teachers to list tests
    user_role = await get_user_role(user_id, username)
    if user_role not in ('admin', 'teacher'):
        logger.warning(
            f"User {user_id} ({user_role}) attempted /list_tests "
            f"without privileges."
        )
        await update.message.reply_text(
            "Эта команда доступна только для администраторов и преподавателей."
        )
        return

    logger.info(f"User {user_id} (@{username}) triggered /list_tests command.")

    test_list_items = []
    try:
        tests_collection = await get_collection('tests')
        # Find all tests, projecting relevant fields, sort by test_id
        cursor = tests_collection.find(
            {},
            {'_id': 0, 'test_id': 1, 'title': 1, 'total_questions': 1}
        ).sort('test_id', 1)

        async for test_doc in cursor:
            test_id = test_doc.get('test_id', 'N/A')
            title = test_doc.get('title', 'Без названия')
            q_count = test_doc.get('total_questions', 0)
            test_list_items.append(
                f"- ID: `{test_id}` | {title} ({q_count} вопр.)"
            )

    except Exception as e:
        logger.exception(f'Database error fetching tests list: {e}')
        await update.message.reply_text(
            'Произошла ошибка при получении списка тестов.'
        )
        return

    if not test_list_items:
        await update.message.reply_text('В базе данных пока нет загруженных тестов.')
    else:
        # Consider pagination if list can become very long
        test_list_str = '\n'.join(test_list_items)
        await update.message.reply_text(
            f'📚 Доступные тесты:\n{test_list_str}',
            # parse_mode='MarkdownV2' # Use Markdown for backticks
        )


list_tests_command_handler = CommandHandler('list_tests', list_tests_command)