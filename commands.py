import os
from io import StringIO

from telegram import Update
from telegram.ext import CallbackContext

from logging_config import logger

GRADES_FOLDER = 'grades'
MATERIALS_FOLDER = 'materials'


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /results command.")
    user_id = update.message.from_user.id
    is_teacher = user_username == context.bot_data.get('teacher_username')
    if is_teacher:
        if not context.args:
            logger.info(
                f"Missing test_id arg for /results command by {user_username}."
            )
            await update.message.reply_text("Пример: /results <test_id>")
            return
        test_id = context.args[0]
        grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
        if not os.path.exists(grades_file):
            logger.warning(f"Results file for test {test_id} not found.")
            await update.message.reply_text(
                f"Нет результатов теста {test_id}.")
            return
        logger.info(
            f"Found results for test {test_id}.v"
            f"Sending results to teacher {user_username}.")
        with open(grades_file, 'r', encoding='utf-8') as file:
            results = file.read()
        await update.message.reply_text(results)
    else:
        if context.args:
            logger.info(
                f"Ignoring args for /results command by {user_username}.")
        student_results_file = os.path.join('results', f'{user_id}.txt')
        if not os.path.exists(student_results_file):
            logger.warning(
                f"Results file for student {user_username} not found.")
            await update.message.reply_text("У вас пока нет результатов.")
            return
        logger.info(
            f"Found results for student {user_username}. Sending results file."
        )
        try:
            with open(student_results_file, 'r', encoding='utf-8') as file:
                results = file.read()
            await update.message.reply_text(f"Ваши результаты:\n\n{results}")
        except Exception as e:
            logger.error(
                f"Error reading results for student {user_username}: {str(e)}")
            await update.message.reply_text(
                "Ошибка при получении ваших результатов.")


async def txt_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /txt command.")
    if user_username != context.bot_data.get('teacher_username'):
        logger.warning(f"Unauthorized access attempt by user {user_username}.")
        await update.message.reply_text("Только для преподавателя.")
        return
    if not context.args:
        logger.info(
            f"Missing test_id argument for /txt command by {user_username}.")
        await update.message.reply_text("Пример: /txt 2")
        return
    test_id = context.args[0].strip("'")
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    if not os.path.exists(grades_file):
        logger.warning(f"Results file for test {test_id} not found.")
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return
    logger.info(
        f"Found results for test {test_id}. "
        f"Sending results as a document to user {user_username}.")
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()
    titled_results = f"Результаты теста №'{test_id}'\n\n{results}"
    result_file = StringIO(titled_results)
    result_file.name = f"results'{test_id}'.txt"
    result_file.seek(0)
    await update.message.reply_document(
        document=result_file, filename=f"results'{test_id}'.txt")


async def materials_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /materials command.")
    if not context.args:
        logger.info(
            f"Missing test_id arg for /materials command by {user_username}.")
        await update.message.reply_text("Пример: /materials 2")
        return
    test_id = context.args[0]
    materials_folder_id = os.path.join(MATERIALS_FOLDER, test_id)
    if not os.path.exists(materials_folder_id):
        logger.warning(f"Materials folder for test {test_id} not found.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return
    files = [
        file for file in os.listdir(materials_folder_id) if os.path.isfile(
            os.path.join(materials_folder_id, file)
        )
    ]
    if not files:
        logger.warning(
            f"No files found in materials folder for test {test_id}.")
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return
    logger.info(
        f"Found {len(files)} files for test {test_id}. "
        f"Sending materials to user {user_username}."
    )
    for file in files:
        file_path = os.path.join(materials_folder_id, file)
        try:
            await update.message.reply_document(document=open(file_path, 'rb'))
            logger.info(f"Sent file {file} to user {user_username}.")
        except Exception as e:
            logger.error(f"Error sending {file} to {user_username}: {str(e)}")
            await update.message.reply_text(f"Ошибка при отправке {file}.")
