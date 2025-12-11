import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not CLOUDFLARE_ACCOUNT_ID:
    raise ValueError("CLOUDFLARE_ACCOUNT_ID environment variable is required")

if not CLOUDFLARE_API_TOKEN:
    raise ValueError("CLOUDFLARE_API_TOKEN environment variable is required")

MIN_QUESTIONS = 1
MAX_QUESTIONS = 20

WATERMARK = "【~@DrQuizRobot】"

ADMIN_USER_IDS = [
    8162524828,
]

admin_ids_env = os.getenv('ADMIN_USER_IDS')
if admin_ids_env:
    try:
        env_admin_ids = [int(id.strip()) for id in admin_ids_env.split(',')]
        ADMIN_USER_IDS.extend(env_admin_ids)
    except:
        pass

NEET_CORRECT_MARKS = 4
NEET_WRONG_MARKS = -1
NEET_UNATTEMPTED_MARKS = 0
