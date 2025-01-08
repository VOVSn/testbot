from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from settings import TOKEN, ADMIN_USERNAME, load_teachers
from logging_config import logger
from message_handler import message_handler
from start_handler import start_command_handler
from materials_handler import materials_command_handler
from txt_handler import txt_command_handler
from results_handler import results_command_handler
from show_handler import show_command_handler
from load_handler import load_command_handler
from add_handler import add_command_handler
from list_handler import list_command_handler
from error_handler import error_handler
from test_handler import test_command_handler, button_callback_handler


def main():
    logger.warning('Starting the bot...')
    try:
        app = Application.builder().token(TOKEN).build()
        app.bot_data['admin_username'] = ADMIN_USERNAME
        app.bot_data['teacher_usernames'] = load_teachers()

        handlers = [
            materials_command_handler,
            txt_command_handler,
            results_command_handler,
            show_command_handler,
            start_command_handler,
            load_command_handler,
            add_command_handler,
            list_command_handler,
            message_handler,
            test_command_handler,
            button_callback_handler
        ]
        
        for handler in handlers:
            app.add_handler(handler)
            logger.info(f'Handler {handler} added.')
        
        app.add_error_handler(error_handler)
        logger.info('Bot is running. Awaiting commands and messages...')
        print('Бот запущен...')
        app.run_polling(poll_interval=2)

    except Exception as e:
        logger.exception(f'Error occurred while starting the bot: {e}')
        print('Error occurred while starting the bot.')

if __name__ == '__main__':
    main()
