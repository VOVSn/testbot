import json
import pika
from fastapi import FastAPI, Request, Header, HTTPException, status
from telegram import Update as PTB_Update # Renamed to avoid conflict if Update is used from FastAPI
from telegram.ext import Application as PTB_Application # For Bot instance
import uvicorn # For type hinting if needed, and direct execution

from settings import (
    TOKEN, WEBHOOK_SECRET_TOKEN, RABBITMQ_URL, RABBITMQ_QUEUE_NAME,
    FASTAPI_INTERNAL_HOST, FASTAPI_INTERNAL_PORT, WEBHOOK_PATH
)
from logging_config import logger

# Initialize FastAPI app
# The lifespan context manager can be used for RabbitMQ connection pool if using aio_pika
app = FastAPI(
    # lifespan=lifespan, # Example for managing resources like DB connections
    title="TestBot Webhook Server",
    version="1.0.0"
)

# Initialize a dummy PTB Application just to get a Bot instance
# This Bot instance is needed for PTB_Update.de_json()
# In later phases, the actual PTB Application will live in the Celery worker.
ptb_bot_dummy_app = PTB_Application.builder().token(TOKEN).build()


def publish_to_rabbitmq(update_dict: dict):
    """Publishes a message to RabbitMQ."""
    try:
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.queue_declare(queue=RABBITMQ_QUEUE_NAME, durable=True) # Ensure queue exists

        message_body = json.dumps(update_dict)

        channel.basic_publish(
            exchange='',
            routing_key=RABBITMQ_QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE # Make message persistent
            ))
        logger.info(f"Successfully published update for user_id {update_dict.get('message', {}).get('from', {}).get('id')} to RabbitMQ.")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ Connection Error: {e}")
        # Potentially raise an exception or handle more gracefully (e.g., retry with backoff)
        return False
    except Exception as e:
        logger.exception(f"Failed to publish message to RabbitMQ: {e}")
        return False

@app.post(WEBHOOK_PATH) # Use the path from settings
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None)
):
    """
    Handles incoming updates from Telegram.
    """
    # Verify secret token (if configured)
    if WEBHOOK_SECRET_TOKEN:
        if not x_telegram_bot_api_secret_token:
            logger.warning("Webhook secret token missing from request.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret token missing")
        if x_telegram_bot_api_secret_token != WEBHOOK_SECRET_TOKEN:
            logger.warning("Invalid webhook secret token received.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret token")

    try:
        update_data = await request.json()
        logger.debug(f"Received update JSON: {update_data}")
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from webhook request.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # For now, we just publish the raw dictionary.
    # Deserialization to PTB_Update will happen in the Celery worker.
    # update = PTB_Update.de_json(data=update_data, bot=ptb_bot_dummy_app.bot)
    # update_dict_for_mq = update.to_dict()

    if publish_to_rabbitmq(update_data): # Pass raw update_data dictionary
        return {"status": "ok", "message": "Update queued"}
    else:
        # If publishing fails, Telegram will retry.
        # We should return an error status so Telegram knows.
        logger.error("Failed to queue update to RabbitMQ. Telegram will retry.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to queue update")


@app.get("/") # Simple health check or info endpoint
async def root():
    return {"message": "TestBot Webhook Server is running."}

# To run this FastAPI app directly for local testing (without Docker):
# uvicorn webhook_server:app --host 0.0.0.0 --port 8000 --reload