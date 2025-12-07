import json
import os
import tempfile
from punishments import log_punishment


# File path for punishment logs
LOG_FILE = "data/punishments.json"


def _atomic_write(path: str, data: dict) -> None:


   # Write to a temp file then replace -> avoids partial writes/corruption


   directory = os.path.dirname(os.path.abspath(path)) or "."
   fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=directory, text=True)
   try:
       with os.fdopen(fd, "w", encoding="utf-8") as f:
           json.dump(data, f, indent=4, ensure_ascii=False)
       os.replace(tmp_path, path)
   finally:
       if os.path.exists(tmp_path):
           try: os.remove(tmp_path)
           except OSError: pass




def load_punishments() -> dict[int, dict[int, list[dict]]]:
   try:
       with open(LOG_FILE, "r") as file:
           data = json.load(file)
       return data
   except (FileNotFoundError, json.JSONDecodeError):
       # If the file doesn't exist or is corrupted, return an empty dictionary
       return {}


def save_punishments(punishments: dict[int, dict[int, list[dict]]]) -> None:
   _atomic_write(LOG_FILE, punishments)
