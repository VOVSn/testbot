# main.py

import asyncio
import logging # Import standard logging for potential setup before config

from telegram.ext import Application

# Configure logging ASAP, before other imports if possible
from logging_config import logger # Use your configured logger

# Database and Settings
from settings import TOKEN, ADMIN_USER_ID, ADMIN_USERNAME
from db import connect_db, close_db, get_db

# Handlers
from handlers.add_handler import add_command_handler
from handlers.error_handler import error_handler
# Removed list_handler temporarily as it needs DB refactoring
# from handlers.list_handler import list_command_handler
from handlers.load_handler import load_command_handler # Will need heavy refactoring
from handlers.message_handler import message_handler
from handlers.materials_handler import materials_command_handler # Needs refactoring
from handlers.show_handler import show_command_handler # Needs refactoring
from handlers.start_handler import start_command_handler, help_command_handler
from handlers.results_handler import results_command_handler # Needs refactoring
# Ensure test_handler exists or comment out if not ready
# from handlers.test_handler import test_command_handler, button_callback_handler
from handlers.txt_handler import txt_command_handler # Needs refactoring

# --- Placeholder for Admin Seeding ---
# This function ensures the admin defined in .env exists in the DB
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


# --- List of Handlers ---
# Note: Many handlers will need refactoring for DB usage.
# Comment out handlers that are broken until refactored.
HANDLERS = [
    # add_command_handler, # Needs refactoring for DB
    # button_callback_handler, # Needs refactoring if related to tests
    # list_command_handler, # Needs refactoring for DB
    load_command_handler, # Needs heavy refactoring for DB (tests/materials)
    # materials_command_handler, # Needs refactoring for DB
    message_handler, # Likely okay, check load_responses if moved
    show_command_handler, # Needs refactoring for DB (fetch test data)
    start_command_handler,
    help_command_handler,
    # results_command_handler, # Needs refactoring for DB
    # test_command_handler, # Needs heavy refactoring for DB (test flow)
    # txt_command_handler, # Needs refactoring for DB
]


# --- Main Application Logic ---
async def main():
    """Initializes DB, seeds admin, sets up and runs the bot."""
    logger.warning('Initializing bot application...')
    # Define db_instance here for broader scope if needed, though get_db() is preferred
    # db_instance = None

    try:
        # 1. Connect to Database
        await connect_db()
        # db_instance = get_db() # Retrieve instance if needed directly

        # 2. Seed Initial Admin User
        await seed_initial_admin()

        # 3. Build Telegram Application
        app_builder = Application.builder().token(TOKEN)
        app = app_builder.build()

        # 4. Store DB instance in bot_data (accessible via context.bot_data['db'])
        # This is useful if handlers don't import get_db directly
        # app.bot_data['db'] = get_db()
        # Note: Handlers can also directly call get_db() from db.py

        # -> Removed old file-based user loading:
        # app.bot_data['admin_username'] = ADMIN_USERNAME # No longer primary source
        # app.bot_data['teacher_usernames'] = load_teachers() # Removed

        # 5. Add Handlers
        logger.info('Adding handlers...')
        for handler in HANDLERS:
            app.add_handler(handler)
            # Improved logging for handler names
            h_name = getattr(handler, '__name__', type(handler).__name__)
            callback_name = getattr(handler, 'callback', {}).__name__ \
                if hasattr(handler, 'callback') else 'N/A'
            logger.info(f'-> Added handler: {h_name} (Callback: {callback_name})')

        # 6. Add Error Handler
        app.add_error_handler(error_handler)
        logger.info('Error handler added.')

        # 7. Start Polling
        logger.warning('Bot initialization complete. Starting polling...')
        print('Бот запущен...')
        # run_polling handles initialization, starting, stopping gracefully
        await app.run_polling(poll_interval=2)

    except (ValueError, ConnectionError) as e:
        # Catch specific startup errors (config, DB connection)
        logger.critical(f'{type(e).__name__}: {e}. Bot cannot start.')
        print(f'ERROR: {e}. Bot cannot start.')
    except Exception as e:
        # Catch any other unexpected errors during startup/runtime
        logger.exception(f'An unexpected error occurred: {e}')
        print(f'CRITICAL ERROR: {e}')
    # finally:
        # Close DB connection on shutdown. run_polling might handle this,
        # but explicit close is safer depending on context.
        # logger.warning('Shutting down bot...')
        # await close_db()
        # logger.warning('Bot shutdown complete.')


# --- Script Entry Point ---
if __name__ == '__main__':
    asyncio.run(main())