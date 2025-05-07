# handlers/activate_handler.py

import datetime
import re
from dateutil.parser import parse, ParserError

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role
from utils.common_helpers import normalize_test_id

# Define command structure options
# /act_test <id> <questions> <tries> <duration_minutes>
# /act_test <id> <questions> <tries> <start_YYYY-MM-DD> <start_HH-MM> <end_YYYY-MM-DD> <end_HH-MM>
# /act_test <id> status (or just /act_test <id>) -> Renamed to 'status' for clarity
# /act_test <id> deact

async def activate_test_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles activating, checking status, or deactivating a test."""
    if not update.effective_user:
        logger.warning('/act_test triggered with no effective_user.')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    logger.info(f"User {user_id} (@{username}) triggered /act_test command "
                f"with args: {context.args}")

    # 1. Check permissions
    user_role = await get_user_role(user_id, username)
    if user_role not in ('admin', 'teacher'):
        logger.warning(
            f"User {user_id} ({user_role}) attempted /act_test "
            f"without privileges."
        )
        await update.message.reply_text(
            "Эта команда доступна только для администраторов и преподавателей."
        )
        return

    # 2. Basic argument check
    if not context.args:
        await update.message.reply_text(
            "Необходимо указать ID теста.\n"
            "Примеры использования:\n"
            "`/act_test math101 status` - проверить статус\n"
            "`/act_test math101 deact` - деактивировать\n"
            "`/act_test math101 20 3 60` - активировать сейчас на 60 мин\n"
            "`/act_test math101 15 1 2024-06-20 09:00 2024-06-20 17:00` - по расписанию\n"
            "(questions, tries, start_date, start_time, end_date, end_time)"
        )
        return

    # 3. Parse arguments
    raw_test_id = context.args[0]
    test_id = normalize_test_id(raw_test_id)
    if not test_id:
        await update.message.reply_text("Некорректный ID теста.")
        return

    action_or_param = context.args[1].lower() if len(context.args) > 1 else "status"

    # --- Handle actions ---
    if action_or_param == "status":
        await _check_status(update, test_id)
    elif action_or_param == "deact":
        await _deactivate_test(update, test_id, user_id)
    else:
        # Assume activation attempt
        await _activate_test(update, context, test_id, user_id)


async def _check_status(update: Update, test_id: str):
    """Checks and reports the status of active tests with the given ID."""
    logger.info(f"Checking status for test_id '{test_id}'.")
    active_tests_coll = await get_collection('active_tests')
    now = datetime.datetime.now(datetime.timezone.utc)

    # Find activations that are currently running
    cursor = active_tests_coll.find({
        'test_id': test_id,
        'start_time': {'$lte': now},
        'end_time': {'$gte': now}
    }).sort('start_time', -1) # Show newest first

    active_list = []
    async for act in cursor:
        start_str = act['start_time'].strftime('%Y-%m-%d %H:%M UTC')
        end_str = act['end_time'].strftime('%Y-%m-%d %H:%M UTC')
        enabled_by = act.get('enabled_by_user_id', 'N/A')
        num_q = act.get('num_questions_to_ask', 'N/A')
        max_t = act.get('max_tries', 'N/A')
        active_list.append(
            f"- Активен с {start_str} до {end_str}\n"
            f"  (Вопросов: {num_q}, Попыток: {max_t}, Включен ID: {enabled_by})"
        )

    if not active_list:
        await update.message.reply_text(f"Тест '{test_id}' в данный момент не активен.")
    else:
        await update.message.reply_text(
            f"Статус активаций для теста '{test_id}':\n\n" + "\n".join(active_list)
        )


async def _deactivate_test(update: Update, test_id: str, user_id: int):
    """Deactivates currently running instances of a test."""
    logger.info(f"User {user_id} attempting to deactivate test_id '{test_id}'.")
    active_tests_coll = await get_collection('active_tests')
    now = datetime.datetime.now(datetime.timezone.utc)

    # Find activations that are currently running
    update_filter = {
        'test_id': test_id,
        'start_time': {'$lte': now},
        'end_time': {'$gte': now} # Find only those currently active
    }

    # Set end_time to now
    update_operation = {'$set': {'end_time': now}}

    try:
        update_result = await active_tests_coll.update_many(
            update_filter, update_operation
        )

        if update_result.matched_count == 0:
            await update.message.reply_text(f"Не найдено активных в данный момент сессий теста '{test_id}' для деактивации.")
        else:
            logger.info(f"User {user_id} deactivated {update_result.modified_count} sessions for test '{test_id}'.")
            await update.message.reply_text(
                f"✅ Успешно деактивировано {update_result.modified_count} активных сессий теста '{test_id}'."
                f"\nНовые студенты не смогут начать тест."
            )
    except Exception as e:
         logger.exception(f"DB error deactivating test '{test_id}': {e}")
         await update.message.reply_text("❌ Ошибка базы данных при деактивации теста.")


async def _activate_test(
    update: Update, context: ContextTypes.DEFAULT_TYPE, test_id: str, user_id: int
):
    """Parses activation parameters and creates a new active_test record."""
    # Expected formats:
    # <num_q> <tries> <duration_mins>  (len(args) == 4)
    # <num_q> <tries> <start_date> <start_time> <end_date> <end_time> (len(args) == 7)
    args = context.args # includes test_id at index 0

    # Fetch the base test first to get total question count
    tests_collection = await get_collection('tests')
    base_test = await tests_collection.find_one(
        {'test_id': test_id},
        {'_id': 0, 'total_questions': 1}
    )
    if not base_test:
        await update.message.reply_text(f"⚠️ Базовый тест с ID '{test_id}' не найден. Загрузите его сначала.")
        return
    total_questions_in_bank = base_test.get('total_questions', 0)

    num_q_str = args[1] if len(args) > 1 else None
    tries_str = args[2] if len(args) > 2 else None

    try:
        if not num_q_str or not tries_str:
             raise ValueError("Недостаточно параметров для активации.")

        num_questions = int(num_q_str)
        max_tries = int(tries_str)

        if num_questions <= 0 or max_tries <= 0:
            raise ValueError("Количество вопросов и попыток должно быть положительным.")
        if num_questions > total_questions_in_bank:
             logger.warning(f"Requested {num_questions} questions for test '{test_id}', but only {total_questions_in_bank} exist. Using max available.")
             num_questions = total_questions_in_bank
             await update.message.reply_text(f"ℹ️ Внимание: В тесте '{test_id}' всего {total_questions_in_bank} вопросов. Будут использованы все.")


        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = None
        end_time = None

        # Case 1: Duration based activation (4 args total: cmd, id, q, tries, duration)
        if len(args) == 4:
            duration_str = args[3]
            duration_minutes = int(duration_str)
            if duration_minutes <= 0:
                 raise ValueError("Продолжительность должна быть положительной.")
            start_time = now
            end_time = now + datetime.timedelta(minutes=duration_minutes)

        # Case 2: Scheduled activation (7 args total: cmd, id, q, tries, s_date, s_time, e_date, e_time)
        elif len(args) == 7:
            start_date_str = args[3]
            start_time_str = args[4]
            end_date_str = args[5]
            end_time_str = args[6]

            # Use dateutil.parser for flexible parsing
            start_time = parse(f"{start_date_str} {start_time_str}").replace(tzinfo=datetime.timezone.utc)
            end_time = parse(f"{end_date_str} {end_time_str}").replace(tzinfo=datetime.timezone.utc)

            if start_time >= end_time:
                raise ValueError("Время окончания должно быть позже времени начала.")
            # Optional: check if start time is in the past? Allow for flexibility maybe.
            # if start_time < now:
            #    logger.warning(f"Activation start time {start_time} is in the past.")

        else:
             raise ValueError(f"Неверное количество параметров ({len(args)}). Ожидалось 4 или 7.")

        # --- Create activation document ---
        activation_doc = {
            'test_id': test_id,
            'enabled_by_user_id': user_id,
            'start_time': start_time,
            'end_time': end_time,
            'num_questions_to_ask': num_questions,
            'max_tries': max_tries,
            'activation_timestamp': now
        }

        active_tests_coll = await get_collection('active_tests')
        insert_result = await active_tests_coll.insert_one(activation_doc)

        if insert_result.inserted_id:
            logger.info(f"Successfully activated test '{test_id}' by user {user_id} "
                        f"(Activation ID: {insert_result.inserted_id})")
            start_str = start_time.strftime('%Y-%m-%d %H:%M UTC')
            end_str = end_time.strftime('%Y-%m-%d %H:%M UTC')
            await update.message.reply_text(
                f"✅ Тест '{test_id}' успешно активирован!\n"
                f"🗓️ Период: с {start_str} по {end_str}\n"
                f"❓ Вопросов для попытки: {num_questions} (из {total_questions_in_bank})\n"
                f"🔄 Макс. попыток: {max_tries}"
            )
        else:
             raise Exception("Failed to insert activation document.")


    except (ValueError, ParserError) as e:
        logger.warning(f"Invalid parameters for /act_test by user {user_id}: {e}")
        await update.message.reply_text(f"❌ Ошибка в параметрах: {e}\n\n"
                                        "Примеры:\n"
                                        "`/act_test math101 status`\n"
                                        "`/act_test math101 deact`\n"
                                        "`/act_test math101 20 3 60`\n"
                                        "`/act_test math101 15 1 2024-06-20 09:00 2024-06-20 17:00`")
    except Exception as e:
        logger.exception(f"Error during test activation for '{test_id}': {e}")
        await update.message.reply_text("❌ Произошла внутренняя ошибка при активации теста.")


# Define the handler
activate_test_command_handler = CommandHandler('act_test', activate_test_command)