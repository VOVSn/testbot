from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role


async def list_teachers_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_user:
        logger.warning('/list_teachers triggered with no effective_user.')
        return

    admin_user_id = update.effective_user.id
    admin_username = update.effective_user.username
    logger.info(
        f'User {admin_user_id} (@{admin_username})'
        f' triggered /list_teachers command.'
    )

    admin_role = await get_user_role(admin_user_id, admin_username)
    if admin_role != 'admin':
        logger.warning(
            f'User {admin_user_id} (@{admin_username}) attempted'
            f' /list_teachers without admin privileges.'
        )
        await update.message.reply_text(
            'Только администратор может просматривать список преподавателей.'
        )
        return

    teacher_usernames = []
    try:
        users_collection = await get_collection('users')
        cursor = users_collection.find(
            {'role': 'teacher'},
            {'_id': 0, 'username': 1}
        )

        async for teacher_doc in cursor:
            username = teacher_doc.get('username')
            if username: # Ensure username exists
                teacher_usernames.append(f'@{username}') # Add @ for clarity

    except Exception as e:
        logger.exception(f'Database error fetching teachers list: {e}')
        await update.message.reply_text(
            'Произошла ошибка при получении списка преподавателей.'
        )
        return

    if not teacher_usernames:
        await update.message.reply_text('Преподаватели еще не добавлены.')
        logger.info(f'Admin {admin_user_id} requested teacher list: None found.')
    else:
        teacher_list_str = '\n'.join(sorted(teacher_usernames)) # Sort list
        await update.message.reply_text(
            f'📋 Список преподавателей:\n{teacher_list_str}'
        )
        logger.info(
            f'Admin {admin_user_id} requested teacher list:'
            f' {len(teacher_usernames)} found.'
        )


list_teachers_command_handler = CommandHandler(
                                    'list_teachers', list_teachers_command)