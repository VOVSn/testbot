import asyncio
import logging # Import standard logging for potential setup before config

from telegram.ext import Application
from logging_config import logger # Use your configured logger

from settings import TOKEN, ADMIN_USER_ID, ADMIN_USERNAME
from db import connect_db, close_db, get_db

from handlers.activate_handler import activate_test_command_handler
from handlers.add_handler import add_teacher_command_handler
from handlers.error_handler import error_handler
from handlers.list_handler import list_teachers_command_handler
from handlers.upload_handler import upload_command_handler
from handlers.download_handler import download_command_handler
from handlers.message_handler import message_handler
from handlers.materials_handler import materials_command_handler
from handlers.show_handler import show_command_handler
from handlers.start_handler import start_command_handler, help_command_handler
from handlers.results_handler import results_command_handler # Needs refactoring
from handlers.test_handler import test_conversation_handler
from handlers.txt_handler import txt_command_handler


async def seed_initial_admin():
    """Checks and adds the initial admin user to the DB if not present."""
    if not ADMIN_USER_ID or not ADMIN_USERNAME:
        logger.error('ADMIN_USER_ID or ADMIN_USERNAME not set in .env')
        raise ValueError('Admin configuration missing in environment variables.')

    try:
        admin_user_id = int(ADMIN_USER_ID)
    except ValueError:
        logger.error(f'ADMIN_USER_ID "{ADMIN_USER_ID}" is not a valid integer.')
        raise ValueError('Invalid ADMIN_USER_ID format.')

    db = get_db()
    users_collection = db['users'] # Access users collection directly

    try:
        # Use update_one with upsert=True: creates if not exist, updates if exist
        # This ensures the admin role is correctly set even if the user existed before
        update_result = await users_collection.update_one(
            {'user_id': admin_user_id},
            {'$set': {
                'username': ADMIN_USERNAME,
                'role': 'admin',
                'user_id': admin_user_id # Ensure user_id is set/updated too
            }},
            upsert=True
        )
        if update_result.upserted_id:
            logger.info(
                f'Initial admin user {ADMIN_USERNAME} (ID: {admin_user_id})'
                ' created in database.'
            )
        elif update_result.matched_count:
            logger.info(
                f'Initial admin user {ADMIN_USERNAME} (ID: {admin_user_id})'
                ' found and ensured role is admin.'
            )
        else:
             # This case should ideally not happen with upsert=True unless
             # there was an underlying issue.
             logger.warning(
                 'Admin seeding via update_one reported no match or upsert.'
             )

    except Exception as e:
        logger.exception(f'Error seeding initial admin user: {e}')
        # Depending on policy, you might want to raise this error
        # raise RuntimeError("Failed to seed initial admin user") from e


# Note: Many handlers will need refactoring for DB usage.
# Comment out handlers that are broken until refactored.
HANDLERS = [
    activate_test_command_handler,
    add_teacher_command_handler,
    list_teachers_command_handler,
    upload_command_handler,
    download_command_handler,
    materials_command_handler,
    message_handler,
    show_command_handler,
    start_command_handler,
    help_command_handler,
    results_command_handler,
    test_conversation_handler,
    txt_command_handler,
]


async def main():
    logger.warning('Initializing bot application...')

    try:
        await connect_db()
        await seed_initial_admin()
        app_builder = Application.builder().token(TOKEN)
        app = app_builder.build()
        logger.info('Adding handlers...')
        for handler in HANDLERS:
            app.add_handler(handler)
            h_name = getattr(handler, '__name__', type(handler).__name__)
            callback_name = getattr(handler, 'callback', {}).__name__ \
                if hasattr(handler, 'callback') else 'N/A'
            logger.info(f'-> Added handler: {h_name} (Callback: {callback_name})')
        app.add_error_handler(error_handler)
        logger.info('Error handler added.')
        logger.warning('Bot initialization complete. Starting polling...')
        print('Бот запущен...')
        await app.run_polling(poll_interval=2)

    except (ValueError, ConnectionError) as e:
        logger.critical(f'{type(e).__name__}: {e}. Bot cannot start.')
        print(f'ERROR: {e}. Bot cannot start.')
    except Exception as e:
        logger.exception(f'An unexpected error occurred: {e}')
        print(f'CRITICAL ERROR: {e}')


if __name__ == '__main__':
    asyncio.run(main())