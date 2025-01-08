import os
from io import StringIO

from telegram import Update
from telegram.ext import CallbackContext

from logging_config import logger

GRADES_FOLDER = 'grades'
MATERIALS_FOLDER = 'materials'


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    user_id = update.message.from_user.id
    logger.info(f"User {user_username} triggered /results command.")

    # Get admin and teacher usernames
    admin_username = context.bot_data.get('admin_username')
    teacher_usernames = context.bot_data.get('teacher_usernames')

    # Check if the user is an admin or a teacher
    is_admin = user_username == admin_username
    is_teacher = user_username in teacher_usernames

    # If user is admin or teacher, they can use the command with a test_id
    if is_admin or is_teacher:
        if context.args:
            test_id = context.args[0]
            grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
            if not os.path.exists(grades_file):
                logger.warning(f"Results file for test {test_id} not found.")
                await update.message.reply_text(f"Нет результатов теста {test_id}.")
                return

            logger.info(f"Found results for test {test_id}. Sending results.")
            with open(grades_file, 'r', encoding='utf-8') as file:
                results = file.read()
            await update.message.reply_text(results)
        else:
            # If no test_id is provided, admins and teachers can see their passed tests
            results_files = [file for file in os.listdir(GRADES_FOLDER) 
                             if file.startswith(f'grades{user_id}')]

            if not results_files:
                logger.warning(f"No results found for {user_username}.")
                await update.message.reply_text("У вас пока нет результатов.")
                return

            logger.info(f"Found {len(results_files)} results for {user_username}. Sending results.")
            for file_name in results_files:
                with open(os.path.join(GRADES_FOLDER, file_name), 'r', encoding='utf-8') as file:
                    results = file.read()
                await update.message.reply_text(results)
    else:
        # For students, show only their own results
        student_results_file = os.path.join('results', f'{user_id}.txt')
        if not os.path.exists(student_results_file):
            logger.warning(f"Results file for student {user_username} not found.")
            await update.message.reply_text("У вас пока нет результатов.")
            return

        logger.info(f"Found results for student {user_username}. Sending results file.")
        try:
            with open(student_results_file, 'r', encoding='utf-8') as file:
                results = file.read()
            await update.message.reply_text(f"Ваши результаты:\n\n{results}")
        except Exception as e:
            logger.error(f"Error reading results for student {user_username}: {str(e)}")
            await update.message.reply_text("Ошибка при получении ваших результатов.")


async def txt_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /txt command.")

    # Check if the user is an admin or a teacher
    admin_username = context.bot_data.get('admin_username')
    teacher_usernames = context.bot_data.get('teacher_usernames')
    is_admin = user_username == admin_username
    is_teacher = user_username in teacher_usernames

    # Only admin and teacher can use this command
    if not (is_admin or is_teacher):
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя.")
        return

    if not context.args:
        logger.info(f"Missing test_id argument for /txt command by {user_username}.")
        await update.message.reply_text("Пример: /txt 2")
        return

    test_id = context.args[0].strip("'")
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    if not os.path.exists(grades_file):
        logger.warning(f"Results file for test {test_id} not found.")
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return

    logger.info(f"Found results for test {test_id}. Sending results as a document.")
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()
    titled_results = f"Результаты теста №'{test_id}'\n\n{results}"
    result_file = StringIO(titled_results)
    result_file.name = f"results'{test_id}'.txt"
    result_file.seek(0)
    await update.message.reply_document(document=result_file, filename=f"results'{test_id}'.txt")
    