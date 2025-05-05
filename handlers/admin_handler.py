# handlers/admin_handler.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from db import get_collection
from logging_config import logger
from utils.db_helpers import get_user_role

# Helper to check if user is admin
async def _is_admin(user_id: int, username: str | None) -> bool:
    role = await get_user_role(user_id, username)
    return role == 'admin'

# Helper to find user by username (could move to db_helpers)
async def _find_user_by_username(username: str) -> dict | None:
    if not username: return None
    clean_username = username[1:] if username.startswith('@') else username
    if not clean_username: return None
    users_collection = await get_collection('users')
    return await users_collection.find_one({'username': clean_username})

# --- Commands ---

async def add_admin_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Promotes an existing user to admin role. Invoker must be admin."""
    invoker_id = update.effective_user.id
    invoker_username = update.effective_user.username

    if not await _is_admin(invoker_id, invoker_username):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Укажите имя пользователя для назначения администратором.\n"
                                        "Пример: `/add_admin new_admin_username`")
        return

    target_username = context.args[0]
    logger.info(f"Admin {invoker_id} attempting to add admin @{target_username}")

    target_user = await _find_user_by_username(target_username)

    if not target_user:
        await update.message.reply_text(f"Пользователь @{target_username} не найден. Он должен сначала запустить /start.")
        return

    target_user_id = target_user['user_id']
    current_role = target_user.get('role', 'student')

    if current_role == 'admin':
        await update.message.reply_text(f"Пользователь @{target_username} уже является администратором.")
        return

    # Promote to admin
    try:
        users_collection = await get_collection('users')
        result = await users_collection.update_one(
            {'user_id': target_user_id},
            {'$set': {'role': 'admin'}}
        )
        if result.modified_count == 1:
            logger.info(f"Admin {invoker_id} promoted @{target_username} (ID: {target_user_id}) to admin.")
            await update.message.reply_text(f"✅ Пользователь @{target_username} успешно назначен администратором.")
        else:
             logger.error(f"Failed to promote @{target_username} to admin (DB update failed).")
             await update.message.reply_text(f"❌ Не удалось назначить @{target_username} администратором.")
    except Exception as e:
        logger.exception(f"DB error during admin promotion for @{target_username}: {e}")
        await update.message.reply_text("❌ Ошибка базы данных при назначении администратора.")


async def remove_admin_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Demotes an admin back to student role. Invoker must be admin."""
    invoker_id = update.effective_user.id
    invoker_username = update.effective_user.username

    if not await _is_admin(invoker_id, invoker_username):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Укажите имя пользователя администратора для понижения.\n"
                                        "Пример: `/remove_admin old_admin`")
        return

    target_username = context.args[0]
    logger.info(f"Admin {invoker_id} attempting to remove admin @{target_username}")

    target_user = await _find_user_by_username(target_username)

    if not target_user:
        await update.message.reply_text(f"Пользователь @{target_username} не найден.")
        return

    target_user_id = target_user['user_id']
    current_role = target_user.get('role', 'student')

    if current_role != 'admin':
        await update.message.reply_text(f"Пользователь @{target_username} не является администратором.")
        return

    # Prevent self-demotion or demoting the last admin
    if target_user_id == invoker_id:
        await update.message.reply_text("Вы не можете понизить себя.")
        return

    users_collection = await get_collection('users')
    admin_count = await users_collection.count_documents({'role': 'admin'})
    if admin_count <= 1:
         await update.message.reply_text("Нельзя удалить единственного администратора.")
         return

    # Demote to student
    try:
        result = await users_collection.update_one(
            {'user_id': target_user_id},
            {'$set': {'role': 'student'}} # Demote to student
        )
        if result.modified_count == 1:
            logger.info(f"Admin {invoker_id} demoted @{target_username} (ID: {target_user_id}) to student.")
            await update.message.reply_text(f"✅ Администратор @{target_username} успешно понижен до студента.")
        else:
             logger.error(f"Failed to demote @{target_username} from admin (DB update failed).")
             await update.message.reply_text(f"❌ Не удалось понизить @{target_username}.")
    except Exception as e:
        logger.exception(f"DB error during admin demotion for @{target_username}: {e}")
        await update.message.reply_text("❌ Ошибка базы данных при понижении администратора.")


async def list_admins_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lists all users with the admin role. Invoker must be admin."""
    invoker_id = update.effective_user.id
    invoker_username = update.effective_user.username

    if not await _is_admin(invoker_id, invoker_username):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    logger.info(f"Admin {invoker_id} requested list of admins.")
    admin_usernames = []
    try:
        users_collection = await get_collection('users')
        cursor = users_collection.find({'role': 'admin'}, {'_id': 0, 'username': 1})
        async for admin_doc in cursor:
            username = admin_doc.get('username')
            if username:
                admin_usernames.append(f'@{username}')

    except Exception as e:
        logger.exception(f'Database error fetching admin list: {e}')
        await update.message.reply_text('Произошла ошибка при получении списка администраторов.')
        return

    if not admin_usernames:
        await update.message.reply_text('Администраторы не найдены (это не должно произойти).')
    else:
        admin_list_str = '\n'.join(sorted(admin_usernames))
        await update.message.reply_text(f'👑 Список администраторов:\n{admin_list_str}')


# --- Handlers ---
add_admin_command_handler = CommandHandler('add_admin', add_admin_command)
remove_admin_command_handler = CommandHandler('remove_admin', remove_admin_command)
list_admins_command_handler = CommandHandler('list_admins', list_admins_command)