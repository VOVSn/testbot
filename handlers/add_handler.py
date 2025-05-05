# handlers/add_handler.py (Refactored)

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role


async def add_teacher_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the /add_teacher command to promote a user to teacher role."""
    if not update.effective_user:
        logger.warning('/add_teacher triggered with no effective_user.')
        return

    admin_user_id = update.effective_user.id
    admin_username = update.effective_user.username
    logger.info(
        f'User {admin_user_id} (@{admin_username})'
        f' triggered /add_teacher command.'
    )

    # 1. Check if the invoking user is an admin
    admin_role = await get_user_role(admin_user_id, admin_username)
    if admin_role != 'admin':
        logger.warning(
            f'User {admin_user_id} (@{admin_username}) attempted'
            f' /add_teacher without admin privileges.'
        )
        await update.message.reply_text(
            'Только администратор может добавлять преподавателей.'
        )
        return

    # 2. Check for command argument (the username to add)
    if len(context.args) != 1:
        await update.message.reply_text(
            'Пожалуйста, укажите имя пользователя (username) преподавателя.\n'
            'Пример: `/add_teacher new_teacher_username`'
        )
        return

    target_username = context.args[0]
    # Remove leading '@' if present
    if target_username.startswith('@'):
        target_username = target_username[1:]

    if not target_username:
         await update.message.reply_text('Имя пользователя не может быть пустым.')
         return

    logger.info(f'Admin {admin_user_id} trying to add/promote'
                f' @{target_username} to teacher.')

    # 3. Find the target user in the database by username
    users_collection = await get_collection('users')
    target_user_data = await users_collection.find_one(
        {'username': target_username}
    )

    if not target_user_data:
        logger.warning(
            f'Target user @{target_username} not found in the database.'
        )
        await update.message.reply_text(
            f'Пользователь @{target_username} не найден в базе данных.\n'
            f'Попросите его/ее сначала отправить /start боту.'
        )
        return

    target_user_id = target_user_data.get('user_id')
    current_role = target_user_data.get('role', 'student')

    # 4. Check if the user is already a teacher or admin
    if current_role == 'teacher':
        await update.message.reply_text(
            f'Пользователь @{target_username} уже является преподавателем.'
        )
        return
    if current_role == 'admin':
        await update.message.reply_text(
            f'Пользователь @{target_username} является администратором'
            f' и не может быть назначен преподавателем.'
        )
        return

    # 5. Update the user's role to 'teacher'
    try:
        update_result = await users_collection.update_one(
            {'user_id': target_user_id},
            {'$set': {'role': 'teacher'}}
        )

        if update_result.modified_count == 1:
            logger.info(
                f'Successfully promoted user {target_user_id}'
                f' (@{target_username}) to teacher by admin {admin_user_id}.'
            )
            await update.message.reply_text(
                f'Пользователь @{target_username} успешно назначен'
                f' преподавателем.'
            )
        else:
            # Should not happen if find_one succeeded, but good to check
            logger.error(
                f'Failed to update role for user {target_user_id}'
                f' (@{target_username}). Matched: {update_result.matched_count}'
            )
            await update.message.reply_text(
                f'Не удалось обновить роль для @{target_username}.'
                 ' Попробуйте снова.'
            )
    except Exception as e:
        logger.exception(
            f'Database error while promoting user @{target_username}: {e}'
        )
        await update.message.reply_text(
            'Произошла ошибка базы данных при назначении преподавателя.'
        )


async def add_teacher_by_id_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the /add_teacher_by_id command. Admin only."""
    if not update.effective_user:
        logger.warning('/add_teacher_by_id triggered with no effective_user.')
        return

    admin_user_id = update.effective_user.id
    admin_username = update.effective_user.username
    logger.info(
        f'User {admin_user_id} (@{admin_username})'
        f' triggered /add_teacher_by_id command.'
    )

    # 1. Check if the invoking user is an admin
    admin_role = await get_user_role(admin_user_id, admin_username)
    if admin_role != 'admin':
        logger.warning(
            f'User {admin_user_id} (@{admin_username}) attempted'
            f' /add_teacher_by_id without admin privileges.'
        )
        await update.message.reply_text(
            'Только администратор может добавлять преподавателей.'
        )
        return

    # 2. Check for command argument (the user ID to add)
    if len(context.args) != 1:
        await update.message.reply_text(
            'Пожалуйста, укажите ID пользователя (число) преподавателя.\n'
            'Пример: `/add_teacher_by_id 123456789`'
        )
        return

    # Validate and parse the ID
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text('ID пользователя должно быть числом.')
        return

    logger.info(f'Admin {admin_user_id} trying to add/promote'
                f' user ID {target_user_id} to teacher.')

    # 3. Find the target user in the database by user_id
    users_collection = await get_collection('users')
    target_user_data = await users_collection.find_one(
        {'user_id': target_user_id}
    )

    if not target_user_data:
        logger.warning(
            f'Target user ID {target_user_id} not found in the database.'
        )
        # Get the username for the reply if available, otherwise use ID
        target_display = f"ID {target_user_id}"
        await update.message.reply_text(
            f'Пользователь с {target_display} не найден в базе данных.\n'
            f'Попросите его/ее сначала отправить /start боту.'
        )
        return

    target_username = target_user_data.get('username', f'ID {target_user_id}') # For messages
    current_role = target_user_data.get('role', 'student')

    # 4. Check if the user is already a teacher or admin
    if current_role == 'teacher':
        await update.message.reply_text(
            f'Пользователь @{target_username} уже является преподавателем.'
        )
        return
    if current_role == 'admin':
        await update.message.reply_text(
            f'Пользователь @{target_username} является администратором'
            f' и не может быть назначен преподавателем.'
        )
        return

    # 5. Update the user's role to 'teacher'
    try:
        # The update logic is identical, as it already uses user_id
        update_result = await users_collection.update_one(
            {'user_id': target_user_id},
            {'$set': {'role': 'teacher'}}
        )

        if update_result.modified_count == 1:
            logger.info(
                f'Successfully promoted user {target_user_id}'
                f' (@{target_username}) to teacher by admin {admin_user_id}.'
            )
            await update.message.reply_text(
                f'Пользователь @{target_username} успешно назначен'
                f' преподавателем.'
            )
        else:
            logger.error(
                f'Failed to update role for user {target_user_id}'
                f' (@{target_username}). Matched: {update_result.matched_count}'
            )
            await update.message.reply_text(
                f'Не удалось обновить роль для @{target_username}.'
                 ' Попробуйте снова.'
            )
    except Exception as e:
        logger.exception(
            f'Database error while promoting user ID {target_user_id}: {e}'
        )
        await update.message.reply_text(
            'Произошла ошибка базы данных при назначении преподавателя.'
        )


# Rename the handler variable and the command string
add_teacher_command_handler = CommandHandler('add_teacher', add_teacher_command)
add_teacher_by_id_command_handler = CommandHandler('add_teacher_by_id', add_teacher_by_id_command)