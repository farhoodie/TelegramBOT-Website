import os
from pathlib import Path

print("CWD:", os.getcwd())
print("ENV BOT_TOKEN present:", bool(os.getenv("BOT_TOKEN")))
print("ENV BOT_TOKEN value (masked):", (os.getenv("BOT_TOKEN","")[:6] + ":********") if ":" in (os.getenv("BOT_TOKEN","")) else "<invalid>")

for p in ["BOT_TOKEN", "token.txt", ".token", ".env", str(Path("config")/".token")]:
    print(f"Exists {p}:", os.path.exists(p))
    if os.path.exists(p) and p != ".env":
        try:
            with open(p, "r", encoding="utf-8") as f:
                val = f.read().strip().strip('"').strip("'")
                print(f"  Value in {p} (masked):", (val[:6] + ":********") if ":" in val else "<invalid>")
        except Exception as e:
            print(f"  Read error: {e}")