# main.py
import time
import logging
import traceback

from telebot.types import Message, ChatPermissions
from telebot.apihelper import ApiTelegramException

from bot import bot
from punishments import (
    log_punishment,
    user_warn_count,
    warn_counts,
    generate_warning_graph,
)

# Configure logging (so we see what's happening)
logging.basicConfig(level=logging.INFO)
tele_logger = logging.getLogger("TeleBot")
tele_logger.setLevel(logging.DEBUG)


# ───────── helpers ─────────
def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        cm = bot.get_chat_member(chat_id, user_id)
        return cm.status in ("administrator", "creator")
    except Exception:
        return False


def parse_reason(text: str) -> str:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else "No reason provided"


def parse_window_seconds(cmd_text: str, default_days: int = 30) -> int:
    parts = cmd_text.split(maxsplit=1)
    if len(parts) < 2:
        return default_days * 86400
    token = parts[1].split()[0].lower()
    try:
        if token.endswith("d"):
            return int(token[:-1]) * 86400
        if token.endswith("w"):
            return int(token[:-1]) * 7 * 86400
        if token.endswith("m"):
            return int(token[:-1]) * 30 * 86400
        return int(token) * 86400
    except Exception:
        return default_days * 86400


def extract_target_from_entities(message: Message):
    """
    Returns (user_id, username_str) from entities.
    - If a text_mention is present, returns (id, username if available)
    - If only a @mention is present, returns (None, username_str)
    - If none, returns (None, None)
    """
    if not getattr(message, "entities", None):
        return (None, None)

    text = message.text or ""
    # Prefer text_mention: it contains a full User with id
    for ent in message.entities:
        if ent.type == "text_mention" and getattr(ent, "user", None):
            uid = ent.user.id
            uname = ent.user.username
            return (uid, uname)

    # Fallback: plain @mention
    for ent in message.entities:
        if ent.type == "mention":
            start = ent.offset
            end = ent.offset + ent.length
            mention_text = text[start:end]  # like "@username"
            return (None, mention_text.lstrip("@"))
    return (None, None)


def need_user_error(message: Message):
    bot.reply_to(
        message,
        "you need to specify the user (reply to the user or tap their name so it becomes a mention)",
    )


# ───────── commands ─────────
@bot.message_handler(commands=["start"])
def start(message: Message):
    bot.reply_to(
        message,
        "My name is Doggo and I’ll be assisting this group with moderation!",
    )


@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_user(message: Message):
    for user in message.new_chat_members:
        mention = f"@{user.username}" if user.username else user.first_name
        bot.send_message(
            message.chat.id,
            f"👋 Welcome {mention}! Please read the group rules.",
        )


@bot.message_handler(commands=["warn"])
def warn_user(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "This command only works in groups.")
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "You must be an admin to use /warn.")

    uid, uname = extract_target_from_entities(message)
    target = None

    if uid:
        try:
            target = bot.get_chat_member(message.chat.id, uid).user
        except Exception:
            target = None

    if not target and message.reply_to_message:
        target = message.reply_to_message.from_user
        uid, uname = target.id, target.username

    if not target:
        return need_user_error(message)

    reason = parse_reason(message.text)
    try:
        log_punishment(
            chat_id=message.chat.id,
            user_id=target.id,
            username=target.username,
            moderator_user=(
                f"@{message.from_user.username}"
                if message.from_user.username
                else str(message.from_user.id)
            ),
            action="warned",
            reason=reason,
        )
        total = user_warn_count(message.chat.id, target.id)
        bot.reply_to(
            message,
            f"⚠️ {target.first_name} has been warned. Reason: {reason}\nTotal warns: {total}",
        )
    except ApiTelegramException as e:
        bot.reply_to(
            message,
            f"❌ Could not warn user: {e.result_json.get('description', str(e))}",
        )


@bot.message_handler(commands=["mute"])
def mute_user(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "This command only works in groups.")
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "You must be an admin to use /mute.")

    uid, uname = extract_target_from_entities(message)
    target = None

    if uid:
        try:
            target = bot.get_chat_member(message.chat.id, uid).user
        except Exception:
            target = None

    if not target and message.reply_to_message:
        target = message.reply_to_message.from_user
        uid, uname = target.id, target.username

    if not target:
        return need_user_error(message)

    reason = parse_reason(message.text)
    until = int(time.time()) + 600  # 10 minutes

    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        log_punishment(
            chat_id=message.chat.id,
            user_id=target.id,
            username=target.username,
            moderator_user=(
                f"@{message.from_user.username}"
                if message.from_user.username
                else str(message.from_user.id)
            ),
            action="muted",
            reason=reason,
        )
        bot.reply_to(
            message,
            f"🔇 {target.first_name} is muted for 10 minutes. Reason: {reason}",
        )
    except ApiTelegramException as e:
        bot.reply_to(
            message,
            f"❌ Could not mute user: {e.result_json.get('description', str(e))}",
        )


@bot.message_handler(commands=["ban"])
def ban_user(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "This command only works in groups.")
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "You must be an admin to use /ban.")

    uid, uname = extract_target_from_entities(message)
    target = None

    if uid:
        try:
            target = bot.get_chat_member(message.chat.id, uid).user
        except Exception:
            target = None

    if not target and message.reply_to_message:
        target = message.reply_to_message.from_user
        uid, uname = target.id, target.username

    if not target:
        return need_user_error(message)

    reason = parse_reason(message.text)

    try:
        bot.ban_chat_member(message.chat.id, target.id)
        log_punishment(
            chat_id=message.chat.id,
            user_id=target.id,
            username=target.username,
            moderator_user=(
                f"@{message.from_user.username}"
                if message.from_user.username
                else str(message.from_user.id)
            ),
            action="banned",
            reason=reason,
        )
        bot.reply_to(
            message,
            f"🚫 {target.first_name} has been banned. Reason: {reason}",
        )
    except ApiTelegramException as e:
        bot.reply_to(
            message,
            f"❌ Could not ban user: {e.result_json.get('description', str(e))}",
        )


@bot.message_handler(commands=["warnchart", "warns"])
def warn_chart(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "This command only works in groups.")
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "You must be an admin to use /warnchart.")

    uid, uname = extract_target_from_entities(message)
    if not uid and not uname:
        return need_user_error(message)

    window = parse_window_seconds(message.text, default_days=30)
    since_ts = int(time.time()) - window

    img = generate_warning_graph(
        message.chat.id,
        since_ts=since_ts,
        user_id=uid if uid else None,
        username=uname if (not uid and uname) else None,
    )

    user_label = (
        f"@{uname}" if (uname and not uid) else (f"@{uname}" if uname else f"id {uid}")
    )
    bot.send_photo(
        message.chat.id,
        img,
        caption=f"Warns for {user_label} in last {window // 86400} day(s)",
    )
    img.close()


# ───────── generic reply to normal messages ─────────
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"), content_types=["text"])
def reply_to_messages(message: Message):
    """
    Reply to ANY non-command text message.
    You can customise this however you like.
    """
    bot.reply_to(
        message,
        "I'm DoggoBot 🐶. Use /warn, /mute or /ban if you're a mod — or just say hi!",
    )


# ───────── run the bot (with retries) ─────────
if __name__ == "__main__":
    print("Testing connection with bot.get_me()...")
    try:
        me = bot.get_me()
        print(f"✅ Bot connected as @{me.username} (id={me.id})")
    except Exception as e:
        print("❌ Failed to connect to Telegram. Check token / internet.")
        print(type(e).__name__, e)
        raise

    print("Starting infinity polling...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
        except KeyboardInterrupt:
            print("Stopping bot (Ctrl+C pressed).")
            break
        except Exception as e:
            print("Polling crashed with error:", e)
            traceback.print_exc()
            print("Retrying in 5 seconds...")
            time.sleep(5)
