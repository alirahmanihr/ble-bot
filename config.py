import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = set()
<<<<<<< HEAD
for p in os.getenv("ADMIN_IDS", "").split(","):
    p = p.strip()
    if p.isdigit():
        ADMIN_IDS.add(int(p))
=======

for p in os.getenv("ADMIN_IDS", "").split(","):
    p = p.strip()
    if p.isdigit():
        ADMIN_IDS.add(int(p))
>>>>>>> b5b8e6b86e8330ffa1cb6ebdffd753fca440247f
