from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from logging_config import logger
from utils.db_helpers import get_user_role


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the /start command, displaying role-specific help."""
    if not update.effective_user:
        logger.warning('/start triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f'User {user_id} (@{username}) triggered /start command.')

    user_role = await get_user_role(user_id, username)
    logger.info(f'User {user_id} role determined as: {user_role}')

    admin_help = """
🤖 Привет! Я - робот для тестирования студентов!

🛠️ **Команды Администратора:**
👑 /add_admin <username> - Назначить пользователя администратором.
💔 /remove_admin <username> - Понизить администратора до студента.
📋 /list_admins - Список всех администраторов.
---
➕ /add_teacher <username> - Добавить преподавателя.
📜 /list_teachers - Список преподавателей.
---
⬆️ /upload - Загрузить CSV тест (`test<ID>.csv`).
📎 /upload <ID> - Загрузить материалы для теста <ID>.
⬇️ /download <ID> - Скачать тест <ID> в CSV.
▶️ /act_test <ID> ... - Активировать тест <ID> (см. `/help act_test`).
📊 /results <ID> - Результаты активированного теста <ID>.
📄 /txt <ID> - Результаты теста <ID> в `.txt`.
🧐 /show <ID> - Показать вопросы теста <ID> (без ответов).
📚 /materials <ID> - Учебные материалы для теста <ID>.
---
🆘 /help - Показать это сообщение.
    """
    # TODO: Add /remove_teacher <username> ?
    # TODO: Add /delete_test <test_id> ?
    # TODO: Add /list_tests command handler?
    # TODO: Add /help act_test command handler

    teacher_help = """
🤖 Привет! Я - робот для тестирования студентов!

👩‍🏫 **Команды Преподавателя:**
⬆️ /upload - Загрузить CSV тест (`test<ID>.csv`).
📎 /upload <ID> - Загрузить материалы для теста <ID>.
⬇️ /download <ID> - Скачать тест <ID> в CSV.
▶️ /act_test <ID> ... - Активировать тест <ID> (см. `/help act_test`).
📊 /results <ID> - Результаты Ваших активированных тестов <ID>.
📄 /txt <ID> - Результаты Вашего теста <ID> в `.txt`.
🧐 /show <ID> - Показать вопросы теста <ID> (без ответов).
📚 /materials <ID> - Учебные материалы для теста <ID>.
✍️ /test <ID> - Пройти активный тест <ID>.
📈 /results - Посмотреть свои результаты.
🆘 /help - Показать это сообщение.
    """
    # TODO: Add /help act_test command handler

    student_help = """
🤖 Привет! Я - робот для тестирования!

🎓 **Команды Студента:**
✍️ /test <ID> - Начать проходить активный тест <ID>.
📚 /materials <ID> - Учебные материалы для теста <ID>.
📈 /results - Посмотреть свои результаты.
🧐 /show <ID> - Показать вопросы теста <ID> (без ответов).
🆘 /help - Показать это сообщение.
    """

    # Select help text based on role
    if user_role == 'admin':
        help_text = admin_help
    elif user_role == 'teacher':
        help_text = teacher_help
    else: # Default to student
        help_text = student_help

    await update.message.reply_text(help_text)


start_command_handler = CommandHandler('start', start_command)
help_command_handler = CommandHandler('help', start_command)