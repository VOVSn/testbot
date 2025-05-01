import datetime
from db import get_collection
from logging_config import logger
# We might need Update/ContextTypes if helpers interact directly with them,
# but get_user_role only needs basic types for now.

async def get_user_role(user_id: int, username: str | None) -> str:
    """
    Retrieves the user's role from the database.
    Defaults to 'student' and adds the user if they are not found.
    """
    users_collection = await get_collection('users')
    # Use projection to only fetch the 'role' field if user is found
    user_data = await users_collection.find_one(
        {'user_id': user_id},
        {'_id': 0, 'role': 1} # Fetch only role, exclude _id
    )

    if user_data and 'role' in user_data:
        return user_data['role']
    elif user_data: # Found but no role field? Default to student
         logger.warning(f"User {user_id} found but missing 'role' field.")
         return 'student'
    else:
        # User not found, treat as student and add them to DB
        logger.info(f'User {user_id} (@{username}) not found. Adding as student.')
        try:
            # Ensure timezone information is included for consistency
            utc_now = datetime.datetime.now(datetime.timezone.utc)
            await users_collection.insert_one({
                'user_id': user_id,
                'username': username,
                'role': 'student',
                'date_added': utc_now
                # TODO: Add first_name/last_name if available from Update object
                # This would require passing the `update` object or names here.
            })
            logger.info(f'Successfully added user {user_id} as student.')
        except Exception as e:
            # Log error but proceed treating them as student for this request
            logger.error(f'Failed to add user {user_id} to DB: {e}')
        return 'student'
