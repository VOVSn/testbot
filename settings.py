# settings.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Core Bot Settings ---
TOKEN = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# --- Administrator Identification ---
# Username for reference/display purposes
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
# Telegram User ID is the primary identifier for the admin role
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')

# --- Database Settings ---
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')

# --- Logging Configuration ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper() # Default to INFO

TEMP_FOLDER = 'temp_files'
os.makedirs(TEMP_FOLDER, exist_ok=True) # Ensure temp dir exists

# --- Validation ---
REQUIRED_VARS = {
    'TOKEN': TOKEN,
    'BOT_USERNAME': BOT_USERNAME,
    'ADMIN_USERNAME': ADMIN_USERNAME,
    'ADMIN_USER_ID': ADMIN_USER_ID,
    'MONGO_URI': MONGO_URI,
    'MONGO_DB_NAME': MONGO_DB_NAME,
}

missing_vars = [k for k, v in REQUIRED_VARS.items() if not v]
if missing_vars:
    raise ValueError(
        f'Missing required environment variables: {", ".join(missing_vars)}'
    )

# Validate ADMIN_USER_ID is an integer
try:
    int(ADMIN_USER_ID)
except (ValueError, TypeError):
    raise ValueError(
        f'ADMIN_USER_ID must be a valid integer,'
        f' received: {ADMIN_USER_ID}'
    )

# Validate Log Level
valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
if LOG_LEVEL not in valid_log_levels:
     raise ValueError(
         f'Invalid LOG_LEVEL: {LOG_LEVEL}.'
         f' Must be one of {", ".join(valid_log_levels)}'
     )
