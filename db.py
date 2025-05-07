import os
import motor.motor_asyncio
from logging_config import logger
from settings import MONGO_URI, MONGO_DB_NAME

# Module-level variables for client and db instances
TIMEOUT_DB = 5000
_client = None
_db = None


async def connect_db():
    global _client, _db
    if _db:
        logger.info('Database connection already established.')
        return

    if not MONGO_URI or not MONGO_DB_NAME:
        logger.critical(
            'MONGO_URI or MONGO_DB_NAME environment variables not set.'
        )
        raise ValueError(
            'MongoDB connection details missing in environment variables.'
        )

    try:
        logger.info(f'Attempting to connect to MongoDB at {MONGO_URI}...')
        _client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_URI,
            # Set serverSelectionTimeoutMS to handle connection issues faster
            serverSelectionTimeoutMS=TIMEOUT_DB
        )
        # The ismaster command is cheap and does not require auth.
        await _client.admin.command('ping')
        _db = _client[MONGO_DB_NAME]
        logger.info(
            f'Successfully connected to MongoDB.'
            f' Database: "{MONGO_DB_NAME}"'
        )
    except Exception as e:
        logger.exception(f'Failed to connect to MongoDB: {e}')
        _client = None
        _db = None
        # Propagate the error to signal connection failure
        raise ConnectionError('Could not connect to MongoDB') from e


def get_db():
    if _db is None:
        logger.error('Database connection not initialized.')
        # This indicates a programming error (connect_db was not called/awaited)
        raise ConnectionError(
            'Database not initialized. Call connect_db() first.'
        )
    return _db


async def close_db():
    global _client, _db
    if _client:
        _client.close()
        logger.info('MongoDB connection closed.')
        _client = None
        _db = None


async def get_collection(collection_name: str):
    db_instance = get_db()  # Ensures DB is connected
    return db_instance[collection_name]
