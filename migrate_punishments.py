import json, os

PATH = os.path.join("data", "punishments.json")
CHAT_ID = -1001234567890  # ← replace with your group/supergroup id (negative for supergroups)

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

changed = 0
for key, entries in list(data.items()):
    if not isinstance(entries, list):
        continue
    for e in entries:
        if e.get("chat_id") is None:
            e["chat_id"] = CHAT_ID
            changed += 1
        e.setdefault("user_id", None)
        e.setdefault("username", key if key and key != "unknown" else None)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated {changed} legacy rows. Done.")