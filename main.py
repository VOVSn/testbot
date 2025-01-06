import os
from dotenv import load_dotenv
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

from handlers import handle_message, error_handler
from commands import (
    materials_command, results_command, txt_command, start_command)
from test_handler import test_command, button_callback
from logging_config import logger


load_dotenv()
TOKEN = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
TEACHER_USERNAME = os.getenv('TEACHER_USERNAME')

if not TOKEN or not BOT_USERNAME or not TEACHER_USERNAME:
    logger.error(
        'Missing : TOKEN, BOT_USERNAME, or TEACHER_USERNAME')
    exit()


def main():
    logger.warning('Starting the bot...')
    
    try:
        app = Application.builder().token(TOKEN).build()
        app.bot_data['teacher_username'] = TEACHER_USERNAME

        handlers = [
            CommandHandler('start', start_command),
            CommandHandler('materials', materials_command),
            CommandHandler('results', results_command),
            CommandHandler('test', test_command),
            CommandHandler('txt', txt_command),
            CallbackQueryHandler(button_callback),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        ]

        # Log when handlers are added
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
