# Telegram Testing Bot (MongoDB Version)

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This Telegram bot facilitates creating, managing, activating, and taking multiple-choice tests. It uses MongoDB for data persistence, python-telegram-bot for interacting with the Telegram API, and Docker Compose for easy local development.

## Features

*   **Role-Based Access Control:** Admin, Teacher, Student roles with distinct permissions managed within the bot.
*   **Test Management:**
    *   Upload test question banks via CSV files (`/upload`).
    *   Download test banks as CSV (`/download`).
    *   View printable test versions (`/show`).
    *   List available tests (`/list_tests`).
    *   Delete tests (Admin only, `/delete_test`).
*   **Material Management:**
    *   Upload supplementary materials (docs, images, audio, video) linked to tests (`/upload <test_id>`).
    *   Students/Teachers can access materials (`/materials <test_id>`).
*   **Test Activation:**
    *   Teachers/Admins can activate tests for specific time windows or durations (`/act_test`).
    *   Configure number of questions per attempt and maximum tries.
    *   Check activation status (`/act_test <test_id> status`).
    *   Deactivate running tests (`/act_test <test_id> deact`).
    *   Detailed help available (`/help_act_test`).
*   **Test Taking:**
    *   Students (and Teachers/Admins) can take active tests (`/test <test_id>`).
    *   Interactive question flow using Inline Keyboards.
    *   Results (score, attempts, timing) stored per user per activation.
*   **Results Viewing:**
    *   Users can view their own results (`/results`).
    *   Teachers/Admins can view results for specific test activations (respecting permissions, `/results <test_id>`).
    *   Teachers/Admins can download results as a text file (`/txt <test_id>`).
*   **User Management:**
    *   Initial admin bootstrapped from `.env` (only if no admins exist in DB).
    *   Admins can manage other Admins (`/add_admin`, `/remove_admin`, `/list_admins`).
    *   Admins can manage Teachers (`/add_teacher`, `/add_teacher_by_id`, `/remove_teacher`, `/list_teachers`).
*   **Initial Data Seeding:** Optional automatic seeding of tests and teacher roles from local files on startup.
*   **Dockerized Development:** Includes `Dockerfile` and `docker-compose.yml` for easy local setup with MongoDB and Mongo Express (web UI for DB).

## Project Structure

```
.
├── handlers/          # Bot command and message handlers
│   ├── __init__.py
│   ├── activate_handler.py
│   ├── add_handler.py
│   ├── admin_handler.py
│   ├── download_handler.py
│   ├── error_handler.py
│   ├── help_handler.py # Contains /help_act_test
│   ├── list_handler.py # Contains /list_teachers
│   ├── list_tests_handler.py # Contains /list_tests
│   ├── materials_handler.py
│   ├── message_handler.py
│   ├── results_handler.py
│   ├── show_handler.py
│   ├── start_handler.py # Contains /start, /help
│   ├── test_handler.py
│   ├── txt_handler.py
│   └── upload_handler.py
├── utils/             # Utility functions and helpers
│   ├── __init__.py
│   ├── common_helpers.py # e.g., normalize_test_id
│   ├── db_helpers.py     # e.g., get_user_role
│   └── seed.py           # Initial data seeding logic
├── seed_data/         # Optional: Directory for seed files (configurable)
│   ├── tests/         # Contains initial test*.csv files
│   │   └── testExample.csv
│   └── teachers.txt   # Contains initial teacher usernames
├── .env.example       # Example environment variables file
├── .env               # Local environment variables (DO NOT COMMIT)
├── .gitignore         # Git ignore rules
├── db.py              # MongoDB connection setup (using Motor)
├── docker-compose.yml # Docker Compose for local development (Bot + MongoDB + Mongo Express)
├── Dockerfile         # Dockerfile for the bot application
├── logging_config.py  # Logging setup
├── main.py            # Main application entry point
├── requirements.txt   # Python dependencies
├── responses.csv      # Data for message_handler (optional)
└── settings.py        # Application settings loader
```

## Technology Stack

*   **Language:** Python 3.9+
*   **Bot Framework:** `python-telegram-bot` (v21+)
*   **Database:** MongoDB
*   **MongoDB Driver:** `motor` (async)
*   **Date Parsing:** `python-dateutil`
*   **Environment:** Docker, Docker Compose
*   **DB GUI (Dev):** Mongo Express

## Setup and Running Locally (Docker Compose)

1.  **Prerequisites:**
    *   [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed.
    *   Git.

2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/VOVSn/testbot
    cd testbot
    ```

3.  **Create `.env` File:**
    *   Copy the `.env.example` file to `.env`:
        ```bash
        cp .env.example .env
        ```
    *   **Edit `.env`** and fill in your actual values for `TOKEN`, `ADMIN_USER_ID`, `ADMIN_USERNAME`, `MONGO_USER`, `MONGO_PASS`, `MONGO_EXPRESS_USER`, `MONGO_EXPRESS_PASS`.
    *   Ensure `MONGO_URI` uses the correct format (e.g., `mongodb://${MONGO_USER}:${MONGO_PASS}@mongo-db:27017/?authSource=admin` for the default Docker Compose setup).
    *   Adjust `MONGO_DB_NAME` if desired.
    *   Configure seeding variables (`INITIAL_SEED_ENABLED`, `TESTS_SEED_FOLDER`, `TEACHERS_SEED_FILE`) if you plan to use initial seeding.

4.  **(Optional) Prepare Seed Data:**
    *   If `INITIAL_SEED_ENABLED` is `True` in `.env`:
        *   Create the directory specified by `TESTS_SEED_FOLDER` (e.g., `mkdir -p seed_data/tests`).
        *   Place your initial `test<ID>.csv` files inside it. Format: `Question;CorrectAnswer;Option2;...` (UTF-8 encoded).
        *   Create the file specified by `TEACHERS_SEED_FILE` (e.g., `seed_data/teachers.txt`).
        *   List usernames (without `@`) of users you want promoted to 'teacher' (one per line). These users must have started the bot previously to exist in the DB.

5.  **Build and Run Containers:**
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces Docker to rebuild the bot image if needed.
    *   `-d`: Runs containers in the background.

6.  **View Logs:**
    ```bash
    docker-compose logs -f # View all logs (Bot, DB, Mongo Express)
    docker-compose logs -f telegram-bot # View only bot logs
    ```

7.  **Interact with the Bot:** Find your bot on Telegram and send `/start` or `/help`.

8.  **Access Mongo Express (DB GUI):**
    *   Open your web browser and navigate to `http://localhost:8082` (or the host port you mapped in `docker-compose.yml`).
    *   Log in using the `MONGO_EXPRESS_USER` and `MONGO_EXPRESS_PASS` defined in your `.env` file.
    *   You can now browse your MongoDB database (`telegram_test_bot_db`) and its collections.

9.  **Stopping:**
    ```bash
    docker-compose down
    ```
    (Use `docker-compose down -v` to also remove the MongoDB data volume for a completely fresh database).

## Configuration (`.env` File)

The following environment variables are used (refer to `.env.example` for details):

*   `TOKEN`: Your Telegram Bot API token.
*   `BOT_USERNAME`: Your bot's Telegram username.
*   `ADMIN_USER_ID`, `ADMIN_USERNAME`: Details for the *initial* admin bootstrap.
*   `MONGO_URI`: Full connection string for MongoDB.
*   `MONGO_USER`, `MONGO_PASS`: Credentials for authenticating with MongoDB.
*   `MONGO_DB_NAME`: The name of the database to use.
*   `MONGO_EXPRESS_USER`, `MONGO_EXPRESS_PASS`: Credentials for accessing the Mongo Express web UI.
*   `INITIAL_SEED_ENABLED`: `True` or `False` to enable/disable initial data seeding.
*   `TESTS_SEED_FOLDER`: Path to folder with initial test CSVs.
*   `TEACHERS_SEED_FILE`: Path to file with initial teacher usernames.
*   `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`).

## Key Commands Summary

Use `/start` or `/help` within the bot to see the commands available for your specific role (Student, Teacher, or Admin).

## Future Enhancements (Planned)

*   **Architecture:** Transition from polling to webhooks using FastAPI.
*   **Task Queue:** Implement asynchronous task processing using Celery and RabbitMQ (or Redis).
*   **Caching/State:** Potentially integrate Redis for caching, rate limiting, or distributed state management.
*   **Testing:** Add comprehensive unit and integration tests.
*   **Features:** Implement test timers, detailed answer feedback, etc.

## Contributing

Contributions are welcome! Please follow standard fork-and-pull-request workflows. Aim for PEP 8 compliance (using `black` and `flake8` is recommended) and include clear logging.
