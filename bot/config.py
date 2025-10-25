import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

MIN_QUESTIONS = 1
MAX_QUESTIONS = 20

WATERMARK = "【~@DrQuizRobot】"

# Admin user IDs (add your Telegram user ID here)
# IMPORTANT: Add at least one admin ID to use /fjoin and /removefjoin commands
# 
# To get your user ID:
# 1. Send a message to @userinfobot on Telegram, OR
# 2. Use the /myid command in this bot
#
# Then add your ID to the list below:
ADMIN_USER_IDS = [
    8162524828,  # Permanent admin
]

# Load admin IDs from environment variable if available (for production)
import os
if os.getenv('ADMIN_USER_IDS'):
    try:
        env_admin_ids = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS').split(',')]
        ADMIN_USER_IDS.extend(env_admin_ids)
    except:
        pass
