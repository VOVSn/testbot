from telegram.ext import Application

from logging_config import logger
from settings import TOKEN, ADMIN_USERNAME, load_teachers

from handlers.add_handler import add_command_handler
from handlers.error_handler import error_handler
from handlers.load_handler import load_command_handler
from handlers.list_handler import list_command_handler
from handlers.message_handler import message_handler
from handlers.materials_handler import materials_command_handler
from handlers.show_handler import show_command_handler
from handlers.start_handler import start_command_handler
from handlers.results_handler import results_command_handler
from handlers.test_handler import test_command_handler, button_callback_handler
from handlers.txt_handler import txt_command_handler


HANDLERS = [
    add_command_handler,
    button_callback_handler,
    list_command_handler,
    load_command_handler,
    materials_command_handler,
    message_handler,
    show_command_handler,
    start_command_handler,
    results_command_handler,
    test_command_handler,
    txt_command_handler,
]


def main():
    logger.warning('Starting the bot...')
    try:
        app = Application.builder().token(TOKEN).build()
        app.bot_data['admin_username'] = ADMIN_USERNAME
        app.bot_data['teacher_usernames'] = load_teachers()

        for handler in HANDLERS:
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
