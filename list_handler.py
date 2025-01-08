from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from logging_config import logger


async def list_teachers_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /list command.")
    
    # Check if the user is the admin
    is_admin = user_username == context.bot_data.get('admin_username')
    
    if not is_admin:
        await update.message.reply_text("You don't have permission to view the list of teachers.")
        return
    
    # Load teacher usernames from the file
    teacher_usernames = context.bot_data.get('teacher_usernames', [])
    
    if not teacher_usernames:
        await update.message.reply_text("No teachers have been added yet.")
    else:
        teacher_list = "\n".join(teacher_usernames)
        await update.message.reply_text(f"List of teachers:\n{teacher_list}")
    
    logger.info("Admin requested the list of teachers.")

list_command_handler = CommandHandler('list', list_teachers_command)
