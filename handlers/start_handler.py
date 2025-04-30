# handlers/start_handler.py (Re-Re-Refactored)

import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger

# --- Helper to get user role ---
async def get_user_role(user_id: int, username: str | None) -> str:
    """
    Retrieves the user's role from the database.
    Defaults to 'student' if the user is not found.
    Optionally adds the user as a 'student' if they don't exist.
    """
    users_collection = await get_collection('users')
    user_data = await users_collection.find_one({'user_id': user_id})

    if user_data:
        return user_data.get('role', 'student') # Default role if field missing
    else:
        # User not found, treat as student and add them to DB
        logger.info(f'User {user_id} (@{username}) not found. Adding as student.')
        try:
            await users_collection.insert_one({
                'user_id': user_id,
                'username': username,
                'role': 'student',
                'date_added': datetime.datetime.now(datetime.timezone.utc)
                # TODO: Add first_name/last_name if available from Update
            })
            logger.info(f'Successfully added user {user_id} as student.')
        except Exception as e:
            # Log error but proceed treating them as student for this request
            logger.error(f'Failed to add user {user_id} to DB: {e}')
        return 'student'


# --- Command Handler ---
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

    # Get user role from database
    user_role = await get_user_role(user_id, username)
    logger.info(f'User {user_id} role determined as: {user_role}')

    # --- Define Help Texts (with more emojis and corrected /results) ---
    admin_help = """
🤖 Привет! Я - робот для тестирования студентов!

🛠️ **Команды Администратора:**
⬆️ /upload - Загрузить CSV тест (`test<ID>.csv`).
📎 /upload <ID> - Загрузить материалы для теста <ID>.
⬇️ /download <ID> - Скачать тест <ID> в CSV.
▶️ /act_test <ID> ... - Активировать тест <ID> (см. `/help act_test`).
➕ /add_teacher <username> - Добавить преподавателя.
📜 /list_teachers - Список преподавателей.
📊 /results <ID> - Результаты активированного теста <ID>.
📄 /txt <ID> - Результаты теста <ID> в `.txt`.
🧐 /show <ID> - Показать вопросы теста <ID> (без ответов).
📚 /materials <ID> - Учебные материалы для теста <ID>.
🆘 /help - Показать это сообщение.
    """
    # TODO: Add /remove_teacher <username> ?
    # TODO: Add /help command handler? (maybe alias to /start)
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


# --- Create the handler ---
start_command_handler = CommandHandler('start', start_command)
# Optional: Add alias for /help pointing to the same function
help_command_handler = CommandHandler('help', start_command)