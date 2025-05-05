# handlers/help_handler.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters

from logging_config import logger

from utils.db_helpers import get_user_role

HELP_ACT_TEST_TEXT = """
**ℹ️ Помощь по команде `/act_test`**

Эта команда используется для активации тестов, проверки их статуса и деактивации. Доступна Администраторам и Преподавателям.

**1. Активация с указанием продолжительности:**
   `/act_test <ID_теста> <Кол-во_вопросов> <Кол-во_попыток> <Длительность_в_минутах>`
   - `<ID_теста>`: ID теста для активации (например, `math101`).
   - `<Кол-во_вопросов>`: Сколько вопросов будет выбрано случайно из банка для каждой попытки.
   - `<Кол-во_попыток>`: Максимальное число попыток для каждого студента.
   - `<Длительность_в_минутах>`: На сколько минут тест будет активен *с текущего момента*.

   *Пример:* `/act_test final_exam 30 1 120`
   (Активировать тест `final_exam` на 120 минут с этого момента, 30 вопросов в попытке, 1 попытка на студента).

**2. Активация по расписанию:**
   `/act_test <ID_теста> <Кол-во_вопросов> <Кол-во_попыток> <Дата_старта> <Время_старта> <Дата_окончания> <Время_окончания>`
   - `<Дата>`: Формат `YYYY-MM-DD` (например, `2024-07-15`).
   - `<Время>`: Формат `HH:MM` (24-часовой, например, `09:00` или `17:30`). Время указывается в UTC.

   *Пример:* `/act_test quiz5 10 2 2024-08-01 10:00 2024-08-01 18:00`
   (Активировать тест `quiz5` с 10:00 UTC до 18:00 UTC 1 августа 2024, 10 вопросов, 2 попытки).

**3. Проверка статуса:**
   `/act_test <ID_теста> status`
   *Или просто:* `/act_test <ID_теста>`
   - Показывает, активен ли тест с указанным ID *в данный момент*, и параметры активной сессии.

**4. Деактивация:**
   `/act_test <ID_теста> deact`
   - Немедленно завершает *все текущие* активные сессии для указанного теста. Новые студенты не смогут начать тест. Студенты, уже проходящие тест, смогут его завершить (результат будет сохранен).
"""

async def help_act_test_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Sends detailed help for the /act_test command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    user_role = await get_user_role(user_id, username)

    if user_role not in ('admin', 'teacher'):
        logger.warning(f"User {user_id} ({user_role}) attempted /help_act_test.")
        # Send a generic denial or just don't reply
        # await update.message.reply_text("Эта информация доступна только администраторам и преподавателям.")
        return # Silently ignore if not admin/teacher

    logger.info(f"User {update.effective_user.id} requested help for /act_test.")
    await update.message.reply_text(HELP_ACT_TEST_TEXT, parse_mode='MarkdownV2')


help_act_test_command_handler = CommandHandler('help_act_test', help_act_test_command)