import logging
import re
# Import settings only AFTER basicConfig might be needed if LOG_LEVEL is used early
from settings import LOG_LEVEL

# Define log format
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
LOG_FILENAME = 'test_bot.log'

# Configure root logger
# Use basicConfig for initial setup, including file handler and format
logging.basicConfig(
    level=LOG_LEVEL, # Use level from settings
    format=LOG_FORMAT,
    filename=LOG_FILENAME,
    filemode='a' # Append mode
)

# Optionally, add a handler for console output as well
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
# Add console handler to the root logger
logging.getLogger().addHandler(console_handler)


# Get a specific logger for the application (optional, but good practice)
# Using __name__ helps identify the source module in logs
logger = logging.getLogger(__name__)

# The initial logger level might be overridden by basicConfig,
# ensure our specific logger respects the desired level.
logger.setLevel(LOG_LEVEL)