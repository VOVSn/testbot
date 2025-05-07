# main.py (FOR PTB v21.10)

import asyncio
import logging # For initial configuration if needed, though logging_config handles it

from telegram.ext import Application, ConversationHandler # Added ConversationHandler for isinstance
from logging_config import logger

from settings import TOKEN
from db import connect_db, close_db
from utils.seed import seed_initial_data

# Import all your handlers
from handlers.activate_handler import activate_test_command_handler
from handlers.add_handler import add_teacher_command_handler, add_teacher_by_id_command_handler
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

HANDLERS = [
    add_admin_command_handler, remove_admin_command_handler, list_admins_command_handler,
    delete_test_command_handler, add_teacher_command_handler, add_teacher_by_id_command_handler,
    remove_teacher_command_handler, list_teachers_command_handler, activate_test_command_handler,
    upload_command_handler, download_command_handler, list_tests_command_handler,
    show_command_handler, materials_command_handler, results_command_handler,
    txt_command_handler, test_conversation_handler, start_command_handler,
    help_command_handler, help_act_test_command_handler, message_handler,
]


async def main():
    logger.warning('Initializing bot application...')
    app: Application | None = None  # For use in the finally block

    try:
        await connect_db()
        await seed_initial_data()

        # Build the application
        app = Application.builder().token(TOKEN).build()

        # Register handlers
        logger.info('Adding handlers...')
        for handler_obj in HANDLERS:
            app.add_handler(handler_obj)
            h_name = getattr(handler_obj, '__name__', type(handler_obj).__name__)
            callback_func = getattr(handler_obj, 'callback', None)
            
            if callable(callback_func):
                callback_name = callback_func.__name__
            elif isinstance(handler_obj, ConversationHandler):
                entry_points_info = []
                if handler_obj.entry_points:
                    for entry_handler in handler_obj.entry_points:
                        entry_callback = getattr(entry_handler, 'callback', None)
                        if callable(entry_callback):
                            entry_points_info.append(entry_callback.__name__)
                callback_name = f"ConversationHandler (entries: {', '.join(entry_points_info) or 'N/A'})"
            else:
                callback_name = "N/A"
            logger.info(f'-> Added handler: {h_name} (Callback: {callback_name})')

        app.add_error_handler(error_handler)
        logger.info('Error handler added.')

        # Initialize and start the bot
        logger.warning('Bot initialization complete. Starting application...')
        await app.initialize()
        # Pass poll_interval to start_polling, not run_polling
        await app.updater.start_polling(poll_interval=2) 
        await app.start()  # Start processing updates

        print('Бот запущен и работает... Нажмите Ctrl+C для остановки.')
        logger.info("Bot is now running. Press Ctrl-C to stop.")

        # Keep the main coroutine alive indefinitely until an interrupt.
        await asyncio.Event().wait()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received (KeyboardInterrupt/SystemExit).")
    except (ValueError, ConnectionError) as e: # Errors during initial setup
        logger.critical(f'{type(e).__name__}: {e}. Bot cannot start.')
        print(f'ERROR: {e}. Bot cannot start.')
    except Exception as e: # Catch-all for other unexpected errors
        logger.exception(f'An unexpected error occurred: {e}')
        print(f'CRITICAL ERROR: {e}')
    finally:
        logger.info("Initiating shutdown sequence...")
        if app:
            logger.info("Stopping Telegram bot components...")
            if app.updater and app.updater.running:
                await app.updater.stop()
                logger.info("Updater stopped.")
            if app.running: # Check if application's main processing loop was started
                await app.stop()
                logger.info("Application processor stopped.")
            # Shutdown should be safe to call even if not fully initialized/started
            await app.shutdown()
            logger.info("Application shutdown complete.")
        
        logger.info("Closing database connection...")
        await close_db()
        logger.info("Shutdown sequence finished.")


if __name__ == '__main__':
    asyncio.run(main())