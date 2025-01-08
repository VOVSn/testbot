from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from logging_config import logger


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /start command.")
    is_admin = user_username == context.bot_data.get('admin_username')
    teacher_usernames = context.bot_data.get('teacher_usernames', [])
    is_teacher = user_username in teacher_usernames

    if is_admin:
        help_text = """
        Я - робот для тестирования студентов!
        Доступные команды для администратора:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results <test_id> - результаты студентов для теста № <test_id>
        /txt <test_id> - результаты студентов в виде текстового файла
        /add <username> - добавить нового преподавателя
        /list - список преподавателей
        """
    elif is_teacher:
        help_text = """
        Я - робот для тестирования студентов!
        Доступные команды для преподавателя:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results <test_id> - результаты студентов для теста № <test_id>
        /txt <test_id> - результаты студентов в виде текстового файла
        """
    else:
        help_text = """
        Я - робот для тестирования!
        Доступные команды для студентов:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results - получить свои результаты
        """

    await update.message.reply_text(help_text)

start_command_handler = CommandHandler('start', start_command)
