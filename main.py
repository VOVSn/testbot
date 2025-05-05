import asyncio
import logging # Import standard logging for potential setup before config

from telegram.ext import Application
from logging_config import logger # Use your configured logger

from settings import TOKEN, ADMIN_USER_ID, ADMIN_USERNAME
from db import connect_db, close_db, get_db
from utils.seed import seed_initial_data

from handlers.activate_handler import activate_test_command_handler
from handlers.add_handler import add_teacher_command_handler

from handlers.admin_handler import (
    add_admin_command_handler,
    remove_admin_command_handler,
    list_admins_command_handler,
    remove_teacher_command_handler,
    delete_test_command_handler,
)

from handlers.error_handler import error_handler
from handlers.list_handler import list_teachers_command_handler
from handlers.list_tests_handler import list_tests_command_handler
from handlers.upload_handler import upload_command_handler
from handlers.download_handler import download_command_handler
from handlers.message_handler import message_handler
from handlers.materials_handler import materials_command_handler
from handlers.show_handler import show_command_handler
from handlers.start_handler import start_command_handler, help_command_handler
from handlers.help_handler import help_act_test_command_handler
from handlers.results_handler import results_command_handler
from handlers.test_handler import test_conversation_handler
from handlers.txt_handler import txt_command_handler


# Note: Many handlers will need refactoring for DB usage.
# Comment out handlers that are broken until refactored.
HANDLERS = [
    # Admin Management
    add_admin_command_handler,
    remove_admin_command_handler,
    list_admins_command_handler,
    delete_test_command_handler,
    # Teacher Management
    add_teacher_command_handler,
    remove_teacher_command_handler,
    list_teachers_command_handler,
    # Test Management
    activate_test_command_handler,
    upload_command_handler,
    download_command_handler,
    list_tests_command_handler,
    show_command_handler,
    # Materials
    materials_command_handler,
    # Results
    results_command_handler,
    txt_command_handler,
    # Student Actions
    test_conversation_handler,
    # General
    start_command_handler,
    help_command_handler,
    help_act_test_command_handler,
    message_handler, # Keep last as it catches general text
]


async def main():
    logger.warning('Initializing bot application...')

    try:
        await connect_db()

        await seed_initial_data()

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