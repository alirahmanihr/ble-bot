import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

# ── Provider Tokens ──
BALE_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Legacy
_FALLBACK = os.getenv("BOT_TOKEN", "")
if not BALE_TOKEN and _FALLBACK and _FALLBACK != "YOUR_BOT_TOKEN_HERE":
    BALE_TOKEN = _FALLBACK

TOKEN = BALE_TOKEN  # backward compat

# Base URLs
BALE_BASE = "https://tapi.bale.ai/bot"
TELEGRAM_BASE = "https://api.telegram.org/bot"

# Active providers
PROVIDERS = []
if BALE_TOKEN and BALE_TOKEN not in ("YOUR_BOT_TOKEN_HERE", "YOUR_BALE_BOT_TOKEN_HERE"):
    PROVIDERS.append(("Bale", BALE_TOKEN, BALE_BASE))
if TELEGRAM_TOKEN and TELEGRAM_TOKEN not in ("YOUR_TELEGRAM_BOT_TOKEN_HERE",):
    PROVIDERS.append(("Telegram", TELEGRAM_TOKEN, TELEGRAM_BASE))

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
