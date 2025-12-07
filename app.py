import json
import os
import sqlite3
import time
from pathlib import Path
from io import BytesIO

from flask import (
    Flask,
    request,
    redirect,
    send_from_directory,
    send_file,
    jsonify,
)
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# Import shared punishments logic from your bot
from punishments import LOG_FILE, warn_counts, generate_warning_graph  # noqa: E402

# Path to SQLite database for website users
DB_PATH = Path("doggobot.db")

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)


# ---------- Database helpers (website users only) ----------

def get_db():
    """Get a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables for website login if they do not exist."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


# ---------- Static file routes ----------

@app.route("/")
def index():
    """Serve landing page."""
    return send_from_directory(".", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve any other static file (html, css, etc.)."""
    return send_from_directory(".", filename)


# ---------- Auth routes ----------

@app.route("/register", methods=["POST"])
def register():
    """Handle registration form submission."""
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm = request.form.get("confirm")

    if not all([name, email, password, confirm]):
        return "Missing fields", 400
    if password != confirm:
        return "Passwords do not match", 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Email is already registered", 400

    conn.close()
    return redirect("/login.html")


@app.route("/login", methods=["POST"])
def login():
    """Handle login form submission."""
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return redirect("/login.html?error=1")

    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user["password_hash"], password):
        return redirect("/admin.html")
    else:
        return redirect("/login.html?error=1")


# ---------- Admin API actions (connected to bot logs) ----------

@app.route("/api/sync_punishments", methods=["POST"])
def api_sync_punishments():
    """
    Hook for future advanced sync.
    Right now your bot writes directly to data/punishments.json,
    so there is nothing extra to sync – but this keeps the button working.
    """
    # You could later add code to sync JSON -> SQL, or to refresh cached stats.
    return redirect("/admin.html")


@app.route("/api/generate_graph", methods=["GET"])
def api_generate_graph():
    """
    Generate a PNG graph of warnings per day for ALL chats.
    Uses the same punishments.json file that the Telegram bot writes to.
    """
    days = request.args.get("days", default=30, type=int)
    since_ts = int(time.time()) - days * 86400

    # chat_id=None => all chats (see generate_warning_graph in punishments.py)
    img_buf: BytesIO = generate_warning_graph(
        chat_id=None,
        since_ts=since_ts,
        user_id=None,
        username=None,
    )
    return send_file(img_buf, mimetype="image/png")


@app.route("/api/export_json", methods=["GET"])
def api_export_json():
    """
    Download the raw punishments.json file used by the bot.
    """
    if os.path.exists(LOG_FILE):
        return send_file(
            LOG_FILE,
            mimetype="application/json",
            as_attachment=True,
            download_name="punishments.json",
        )
    else:
        # No file yet -> return empty JSON object
        return jsonify({"message": "No punishments logged yet.", "data": {}})


@app.route("/api/top_warns", methods=["GET"])
def api_top_warns():
    """
    Optional JSON endpoint: Top users by warns (all chats).
    Not wired to a button yet, but can be used by charts.js etc.
    """
    days = request.args.get("days", default=30, type=int)
    since_ts = int(time.time()) - days * 86400
    # chat_id=None => all chats
    top = warn_counts(chat_id=None, since_ts=since_ts, limit=10)
    return jsonify({"days": days, "top": top})


# ---------- Entry point ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
