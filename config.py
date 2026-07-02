import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = set()
for p in os.getenv("ADMIN_IDS", "").split(","):
    p = p.strip()
    if p.isdigit():
        ADMIN_IDS.add(int(p))

CHANNEL_1 = os.getenv("CHANNEL_1", "@hamrakar")
CHANNEL_2 = os.getenv("CHANNEL_2", "@hamrakarjob")
BOT_NAME = os.getenv("BOT_NAME", "رسانه استخدامی همراکار")
SLOGAN = os.getenv("SLOGAN", "✨ ما به توان انسان‌ها باور داریم ✨")
SLOGAN_EMP = os.getenv("SLOGAN_EMP", "🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
THANKS = os.getenv("THANKS", "🙏 با تشکر از اعتماد شما")
