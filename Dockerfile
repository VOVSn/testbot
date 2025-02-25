FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Set environment variable for the bot token (optional)
# ENV TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
CMD ["python", "main.py"]
