import os

from dotenv import load_dotenv


MATERIALS_FOLDER = 'materials'
GRADES_FOLDER = 'grades'
TESTS_FOLDER = 'tests'
RESULTS_FOLDER = 'results'

load_dotenv()
TOKEN = os.getenv('TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
TEACHER_USERNAMES_FILE = os.getenv('TEACHER_USERNAMES_FILE', 'teachers.txt')

if not TOKEN or not BOT_USERNAME or not ADMIN_USERNAME:
    raise ValueError(
        "Missing required environment variables:"
        " TOKEN, BOT_USERNAME, or ADMIN_USERNAME"
    )


def load_teachers():
    if not os.path.exists(TEACHER_USERNAMES_FILE):
        return []

    with open(TEACHER_USERNAMES_FILE, 'r') as file:
        return [line.strip() for line in file.readlines()]
