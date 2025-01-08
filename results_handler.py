import os

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from logging_config import logger
from settings import GRADES_FOLDER, RESULTS_FOLDER


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    user_id = update.message.from_user.id
    logger.info(f"User {user_username} triggered /results command.")

    admin_username = context.bot_data.get('admin_username')
    teacher_usernames = context.bot_data.get('teacher_usernames')
    is_admin = user_username == admin_username
    is_teacher = user_username in teacher_usernames

    if context.args:  # If arguments are provided (e.g., /results <test_id>)
        test_id = context.args[0]
        grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
        
        if not (is_admin or is_teacher):
            logger.warning(
                f"User {user_username} is not authorized to access test results."
            )
            await update.message.reply_text(
                "Только преподаватели и администраторы могут просматривать результаты тестов."
            )
            return

        if not os.path.exists(grades_file):
            logger.warning(f"Results file for test {test_id} not found.")
            await update.message.reply_text(
                f"Нет результатов для теста {test_id}."
            )
            return

        logger.info(f"Found results for test {test_id}. Sending results.")
        try:
            with open(grades_file, 'r', encoding='utf-8') as file:
                results = file.read()
            await update.message.reply_text(results)
        except Exception as e:
            logger.error(
                f"Error reading results for test {test_id}: {str(e)}"
            )
            await update.message.reply_text(
                "Ошибка при чтении результатов теста."
            )
    else:  # If no arguments are provided (e.g., /results)
        student_results_file = os.path.join(RESULTS_FOLDER, f'{user_id}.txt')

        if not os.path.exists(student_results_file):
            logger.warning(
                f"Results file for student {user_username} not found."
            )
            await update.message.reply_text("У вас пока нет результатов.")
            return

        logger.info(
            f"Found results for {user_username}. Sending results file."
        )
        try:
            with open(student_results_file, 'r', encoding='utf-8') as file:
                results = file.read()
            await update.message.reply_text(f"Ваши результаты:\n\n{results}")
        except Exception as e:
            logger.error(
                f"Error reading results for student {user_username}: {str(e)}"
            )
            await update.message.reply_text(
                "Ошибка при получении ваших результатов."
            )


results_command_handler = CommandHandler('results', results_command)
