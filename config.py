# config.py
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

TOKEN     = os.getenv("BOT_TOKEN", "")
CHANNEL_1 = "@hamrakar"
CHANNEL_2 = "@hamrakarjob"
BOT_NAME  = "رسانه استخدامی همراکار"
SLOGAN    = "✨ ما به توان انسان‌ها باور داریم ✨"
FOOTER    = "\n\n📣 @Hamrakar\n📣 @Hamrakarjob"