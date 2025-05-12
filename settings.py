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


INITIAL_SEED_ENABLED = os.getenv('INITIAL_SEED_ENABLED', 'False').lower() in ('true', '1', 't', 'yes')
TESTS_SEED_FOLDER = os.getenv('TESTS_SEED_FOLDER', 'seed_data/tests') # Use default relative paths
TEACHERS_SEED_FILE = os.getenv('TEACHERS_SEED_FILE', 'seed_data/teachers.txt')




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


# --- Webhook Settings ---
WEBHOOK_DOMAIN = os.getenv('WEBHOOK_DOMAIN') # e.g., testbot.mydomain.com
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/telegram-webhook') # e.g., /your-secret-webhook-path
WEBHOOK_URL = f"https://{WEBHOOK_DOMAIN}{WEBHOOK_PATH}" if WEBHOOK_DOMAIN else None
WEBHOOK_SECRET_TOKEN = os.getenv('WEBHOOK_SECRET_TOKEN') # For X-Telegram-Bot-Api-Secret-Token header

# --- RabbitMQ Settings ---
RABBITMQ_DEFAULT_USER = os.getenv('RABBITMQ_DEFAULT_USER', 'guest')
RABBITMQ_DEFAULT_PASS = os.getenv('RABBITMQ_DEFAULT_PASS', 'guest')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq') # Docker service name
RABBITMQ_PORT = os.getenv('RABBITMQ_PORT', '5672')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')
RABBITMQ_URL = f"amqp://{RABBITMQ_DEFAULT_USER}:{RABBITMQ_DEFAULT_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}{RABBITMQ_VHOST}"
RABBITMQ_QUEUE_NAME = os.getenv('RABBITMQ_QUEUE_NAME', 'telegram_updates_queue')

# --- FastAPI Settings ---
FASTAPI_INTERNAL_HOST = os.getenv('FASTAPI_INTERNAL_HOST', '0.0.0.0')
FASTAPI_INTERNAL_PORT = int(os.getenv('FASTAPI_INTERNAL_PORT', '8000'))

# --- Celery Settings (placeholders, will be used more in next phase) ---
CELERY_BROKER_URL = RABBITMQ_URL # Celery uses RabbitMQ as broker
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"


# --- Validation for new vars ---
if WEBHOOK_DOMAIN: # Only validate if domain is set, implying webhook mode
    if not WEBHOOK_URL.startswith("https://"):
        raise ValueError("WEBHOOK_URL must start with https://")
