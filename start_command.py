from telegram import Update
from telegram.ext import ContextTypes

from logging_config import logger


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /start command.")
    
    # Check if the user is the admin
    is_admin = user_username == context.bot_data.get('admin_username')
    
    # Check if the user is a teacher (teachers loaded from file)
    teacher_usernames = context.bot_data.get('teacher_usernames', [])
    is_teacher = user_username in teacher_usernames
    
    # If the user is admin, show the admin-specific help text
    if is_admin:
        help_text = """
        Я - робот для тестирования студентов!
        Доступные команды для администратора:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results <test_id> - результаты студентов для теста № <test_id>
        /txt <test_id> - результаты студентов в виде текстового файла
        /add_teacher <username> - добавить нового преподавателя
        """
    # If the user is not an admin but is a teacher, show the teacher-specific help text
    elif is_teacher:
        help_text = """
        Я - робот для тестирования студентов!
        Доступные команды для преподавателя:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results <test_id> - результаты студентов для теста № <test_id>
        /txt <test_id> - результаты студентов в виде текстового файла
        """
    # If the user is neither an admin nor a teacher, show the student help text
    else:
        help_text = """
        Я - робот для тестирования!
        Доступные команды для студентов:
        /test <test_id> - запустить тест № <test_id>
        /materials <test_id> - учебные материалы для теста № <test_id>
        /results - получить свои результаты
        """
    
    await update.message.reply_text(help_text)
