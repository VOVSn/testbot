import os
import csv

from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

from logging_config import logger
from settings import TESTS_FOLDER


async def show_command(update: Update, context: CallbackContext) -> None:
    """Handles the /show <test_id> command."""
    user_username = update.message.from_user.username
    test_id = context.args[0] if context.args else None

    if not test_id:
        await update.message.reply_text("Пожалуйста, укажите test_id.")
        return

    # Check if the test file exists
    test_file_path = os.path.join(TESTS_FOLDER, f'test{test_id}.csv')
    if not os.path.exists(test_file_path):
        await update.message.reply_text(f"Тест с ID {test_id} не найден.")
        return

    # Generate the test text without correct answers
    try:
        with open(test_file_path, newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';')
            test_lines = []

            for row in csvreader:
                if len(row) < 2:
                    continue  # Skip invalid rows
                question = row[0]
                all_answers = row[1:]
                incorrect_answers = all_answers[:0] + all_answers[1:]

                # Format the question and its choices
                test_lines.append(
                    f"{question}\n" + "\n".join(
                        f"[ ]{i + 1}. {choice}" for i, choice in enumerate(
                            incorrect_answers
                        ))
                )

        # Create the .txt file to send to the user
        test_text = '\n\n'.join(test_lines)
        test_filename = f'test_{test_id}.txt'
        test_file_path_txt = os.path.join(TESTS_FOLDER, test_filename)

        # Save the generated test text to a file
        with open(test_file_path_txt, 'w', encoding='utf-8') as f:
            f.write(test_text)

        # Send the generated file to the user
        await update.message.reply_text(
            f"Вот ваш тест (test_id: {test_id}):", quote=False
        )
        await update.message.reply_document(
            document=open(test_file_path_txt, 'rb'))
        os.remove(test_file_path_txt)

        logger.info(f"Test {test_id} sent to {user_username}")

    except Exception as e:
        logger.exception(f"Error generating test {test_id}: {e}")
        await update.message.reply_text(
            "Произошла ошибка при генерации теста.")

show_command_handler = CommandHandler('show', show_command)
