import json
import os
import tempfile
import io
import time
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

# Shared punishments log file (bot + website both use this)
LOG_FILE = os.path.join("data", "punishments.json")


def _atomic_write(path: str, data: dict) -> None:
    """Safely write JSON data to disk (avoids partial writes)."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _load() -> dict:
    """Load punishments.json, return {} if missing or corrupted."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    """Save punishments.json atomically."""
    _atomic_write(LOG_FILE, data)


def _now_ts() -> int:
    return int(time.time())


def _normalize_entries(punishment_log: dict):
    """
    Normalize legacy entries so all rows have:
      ts, chat_id, user_id, username, moderator, action, reason
    """
    for top_key, entries in punishment_log.items():
        if isinstance(entries, list):
            for e in entries:
                if "ts" not in e and "timestamp" in e:
                    try:
                        e["ts"] = int(datetime.strptime(
                            e["timestamp"], "%Y-%m-%d %H:%M:%S"
                        ).timestamp())
                    except Exception:
                        e["ts"] = _now_ts()
                e.setdefault("chat_id", None)
                e.setdefault("user_id", None)
                e.setdefault("username", top_key if top_key != "unknown" else None)
                e.setdefault("moderator", None)
                e.setdefault("action", None)
                e.setdefault("reason", None)
    return punishment_log


def log_punishment(
    *,
    chat_id: int,
    user_id: int,
    username: str | None,
    moderator_user: str,
    action: str,
    reason: str,
    ts: int | None = None,
) -> None:
    """
    Append a punishment entry for a user (called from the bot).
    """
    if ts is None:
        ts = _now_ts()

    target_key = str(user_id) if user_id else (username or "unknown")

    entry = {
        "timestamp": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        "ts": ts,
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "action": action,
        "moderator": moderator_user,
        "reason": reason,
    }

    log = _load()
    log.setdefault(target_key, []).append(entry)
    _save(log)


def user_warn_count(chat_id: int, user_id: int, since_ts: int | None = None) -> int:
    """
    Count warns for a specific user in a given chat (used by /warn).
    """
    log = _normalize_entries(_load())
    total = 0
    for entries in log.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if e.get("action") != "warned":
                continue
            # chat filter (legacy rows with chat_id=None are allowed)
            if e.get("chat_id") not in (None, chat_id):
                continue
            if e.get("user_id") not in (None, user_id):
                continue
            if since_ts and e.get("ts", 0) < since_ts:
                continue
            total += 1
    return total


def warn_counts(
    chat_id: int | None = None,
    since_ts: int | None = None,
    limit: int = 10,
):
    """
    Aggregate warns per user.
    If chat_id is None → include all chats (used by website).
    If chat_id is set  → filter to that chat (used by bot commands).
    """
    log = _normalize_entries(_load())
    counter = defaultdict(int)
    for entries in log.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if e.get("action") != "warned":
                continue
            if chat_id is not None and e.get("chat_id") not in (None, chat_id):
                continue
            if since_ts and e.get("ts", 0) < since_ts:
                continue
            label = (
                f"@{e['username']}"
                if e.get("username")
                else str(e.get("user_id") or "unknown")
            )
            counter[label] += 1
    return sorted(counter.items(), key=lambda x: x[1], reverse=True)[:limit]


def generate_warning_graph(
    chat_id: int | None = None,
    since_ts: int | None = None,
    user_id: int | None = None,
    username: str | None = None,
) -> io.BytesIO:
    """
    Build a per-day bar chart of warns:
      - If chat_id is None → include all chats (website "Generate graph")
      - Else              → filter by chat_id (bot /warnchart)
      - Optional per-user filter (user_id or username).
    Returns an in-memory PNG buffer.
    """
    log = _normalize_entries(_load())
    per_day = defaultdict(int)

    for entries in log.values():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if e.get("action") != "warned":
                continue

            # Chat filter (include all if chat_id is None)
            if chat_id is not None and e.get("chat_id") not in (None, chat_id):
                continue

            # Optional per-user filter
            if user_id is not None and e.get("user_id") not in (None, user_id):
                continue
            if user_id is None and username is not None:
                # compare case-insensitively (strip leading '@' if passed)
                un = (e.get("username") or "").lstrip("@").lower()
                if un != username.lstrip("@").lower():
                    continue

            if since_ts and e.get("ts", 0) < since_ts:
                continue

            d = datetime.fromtimestamp(e.get("ts", _now_ts())).date().isoformat()
            per_day[d] += 1

    dates = sorted(per_day.keys())
    counts = [per_day[d] for d in dates]

    plt.figure(figsize=(10, max(3, 4 + 0.1 * len(dates))))
    if dates:
        plt.bar(dates, counts)
        plt.xticks(rotation=45, ha="right")
        plt.xlabel("Date")
        plt.ylabel("Warnings")
        plt.title("Warnings per Day")
        plt.grid(axis="y", linestyle="--", alpha=0.4)
    else:
        plt.text(0.5, 0.5, "No warn data", ha="center", va="center", fontsize=14)
        plt.axis("off")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200)
    buf.seek(0)
    plt.close()
    return buf
