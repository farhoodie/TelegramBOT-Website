import telebot
import sqlite3
from pathlib import Path

# ======================================================
#  BOT TOKEN
#  Paste your NEW BotFather token here and ONLY here.
#  Example: "1234567890:AAAbbbCCCdddEEEfffGGGhhhIIIjjj"
# ======================================================
TOKEN = "8303921152:AAHQE-F4KhVD75DXE7WQ5Dd-oB7VzGWu2Z8"

# Basic sanity check so we don't accidentally start with garbage
if ":" not in TOKEN.strip():
    raise ValueError("Invalid token format. Expected something like 1234567890:AA...")

# The TeleBot instance used everywhere (main.py imports this)
bot = telebot.TeleBot(TOKEN.strip(), parse_mode="HTML")

# ======================================================
#  (Optional) SQLite logging – you can still use this
#  if you want to log punishments in a DB as well.
#  Right now your main.py uses punishments.py, which
#  writes to data/punishments.json for the website.
# ======================================================

DB_PATH = Path("doggobot.db")


def log_punishment_db(user_id, username, chat_id, action, reason, moderator):
    """
    Optional: log a punishment into SQLite.
    Currently your main bot logic uses punishments.py (JSON),
    but you can call this if you want SQL logs as well.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO punishments (user_id, username, chat_id, action, reason, moderator)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, username, chat_id, action, reason, moderator),
    )
    conn.commit()
    conn.close()
