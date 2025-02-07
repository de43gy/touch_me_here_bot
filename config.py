from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATABASE_PATH = "data/massage_slots.db"

print(f"BOT_TOKEN: {BOT_TOKEN}")
print(f"ADMIN_ID: {ADMIN_ID}")