import os

from telegram import Update
from telegram.ext import CallbackContext

GRADES_FOLDER = 'grades'
MATERIALS_FOLDER = 'materials'


async def results_command(update: Update, context: CallbackContext) -> None:
    user_username = update.message.from_user.username
    if user_username != context.bot_data.get('teacher_username'):
        await update.message.reply_text("Только для преподавателя.")
        return
    if not context.args:
        await update.message.reply_text("Пример: /results <test_id>")
        return

    test_id = context.args[0]
    grades_file = os.path.join(GRADES_FOLDER, f'grades{test_id}.txt')
    if not os.path.exists(grades_file):
        await update.message.reply_text(f"Нет результатов теста {test_id}.")
        return
    with open(grades_file, 'r', encoding='utf-8') as file:
        results = file.read()
    await update.message.reply_text(results)


async def materials_command(update: Update, context: CallbackContext) -> None:
    if not context.args:
        await update.message.reply_text("Пример: /materials <test_id>")
        return
    test_id = context.args[0]
    materials_folder_id = os.path.join(MATERIALS_FOLDER, test_id)
    if not os.path.exists(materials_folder_id):
        await update.message.reply_text(f"Нет материалов теста {test_id}.")
        return
    files = [
        file for file in os.listdir(materials_folder_id) if os.path.isfile(
            os.path.join(materials_folder_id, file)
        )
    ]
    if not files:
        await update.message.reply_text(
            f"Нет материалов теста {test_id}.")
        return
    for file in files:
        file_path = os.path.join(materials_folder_id, file)
        await update.message.reply_document(document=open(file_path, 'rb'))
