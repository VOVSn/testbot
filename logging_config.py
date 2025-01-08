import logging
import re


logging.basicConfig(
    filename='test_bot.log',
    level=logging.WARNING,
    format='%(asctime)s[%(levelname)s]%(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


def mask_token(message):
    return re.sub(r'/bot\d{10}:', '/bot<masked>:GHYjh', message)


def log_message(message):
    masked_message = mask_token(message)
    logger.info(masked_message)
