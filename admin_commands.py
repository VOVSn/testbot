from telegram import Update
from telegram.ext import ContextTypes
from logging_config import logger

async def add_teacher_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_username = update.message.from_user.username
    logger.info(f"User {user_username} triggered /add command.")
    
    # Check if the user is the admin
    is_admin = user_username == context.bot_data.get('admin_username')
    
    if not is_admin:
        await update.message.reply_text("You don't have permission to add teachers.")
        return
    
    # Ensure the command includes a username argument
    if len(context.args) != 1:
        await update.message.reply_text("Please provide a username to add.")
        return
    
    new_teacher_username = context.args[0]
    
    # Load the existing teacher usernames
    teacher_usernames = context.bot_data.get('teacher_usernames', [])
    
    # Check if the username is already a teacher
    if new_teacher_username in teacher_usernames:
        await update.message.reply_text(f"{new_teacher_username} is already a teacher.")
        return
    
    # Add the new teacher to the list and update the file
    teacher_usernames.append(new_teacher_username)
    with open('teachers.txt', 'a') as file:
        file.write(f"{new_teacher_username}\n")
    
    # Update bot data
    context.bot_data['teacher_usernames'] = teacher_usernames
    
    await update.message.reply_text(f"Teacher {new_teacher_username} has been added.")
    logger.info(f"Teacher {new_teacher_username} added by admin.")


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
    
    logger.info(f"Admin requested the list of teachers.")
