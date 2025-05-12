FROM python:3.9-slim

WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The CMD will depend on whether this Dockerfile is for FastAPI or Celery
# For FastAPI:
CMD ["uvicorn", "webhook_server:app", "--host", "0.0.0.0", "--port", "8000"]
# For the old polling bot (which we are phasing out):
# CMD ["python", "main.py"]
# For Celery worker (in next phase):
# CMD ["celery", "-A", "celery_app", "worker", "-l", "info", "-P", "gevent"]