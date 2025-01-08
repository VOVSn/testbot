from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    CallbackQueryHandler, MessageHandler, filters
)

from admin_commands import add_teacher_command, list_teachers_command
from commands import results_command, txt_command
from handlers import handle_message, error_handler
from logging_config import logger
from load_command import (
    load_command, handle_file_upload, cancel_load, UPLOAD_STATE
)
from start_command import start_command
from test_handler import test_command, button_callback
from show_command import show_command
from settings import TOKEN, ADMIN_USERNAME, load_teachers
from materials_handler import materials_command_handler


def main():
    logger.warning('Starting the bot...')
    try:
        app = Application.builder().token(TOKEN).build()
        app.bot_data['admin_username'] = ADMIN_USERNAME
        app.bot_data['teacher_usernames'] = load_teachers()  # Store teacher usernames

        load_handler = ConversationHandler(
            entry_points=[CommandHandler('load', load_command)],
            states={
                UPLOAD_STATE: [MessageHandler(
                    filters.Document.ALL, handle_file_upload)]
            },
            fallbacks=[CommandHandler('cancel', cancel_load)]
        )

        handlers = [
            CommandHandler('start', start_command),
            CommandHandler('results', results_command),
            CommandHandler('test', test_command),
            CommandHandler('txt', txt_command),
            CommandHandler('add', add_teacher_command),
            CommandHandler('list', list_teachers_command),
            CommandHandler('show', show_command),
            CallbackQueryHandler(button_callback),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            load_handler,
            materials_command_handler
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
