"""Bale HTTP API - همراکار"""
import asyncio, aiohttp, logging
log = logging.getLogger(__name__)
_BASE = ""

def set_token(t):
    global _BASE
    _BASE = f"https://tapi.bale.ai/bot{t}"

async def _post(s, method, **kw):
    kw = {k:v for k,v in kw.items() if v is not None}
    try:
        async with s.post(f"{_BASE}/{method}", json=kw,
                          timeout=aiohttp.ClientTimeout(total=60)) as r:
            return await r.json()
    except Exception as e:
        log.error(f"API {method}: {e}")
        return {"ok": False}

async def get_me(s):
    return await _post(s, "getMe")

async def get_updates(s, offset=0, timeout=25, limit=100):
    return await _post(s, "getUpdates", offset=offset, timeout=timeout, limit=limit)

async def send_message(s, cid, text, reply_markup=None):
    return await _post(s, "sendMessage", chat_id=str(cid),
                       text=str(text)[:4096], reply_markup=reply_markup,
                       parse_mode="Markdown")

async def edit_message_text(s, cid, mid, text, reply_markup=None):
    return await _post(s, "editMessageText", chat_id=str(cid), message_id=mid,
                       text=str(text)[:4096], reply_markup=reply_markup,
                       parse_mode="Markdown")

async def edit_reply_markup(s, cid, mid, reply_markup=None):
    return await _post(s, "editMessageReplyMarkup", chat_id=str(cid),
                       message_id=mid, reply_markup=reply_markup)

async def answer_cb(s, cbid, text=None, alert=False):
    return await _post(s, "answerCallbackQuery", callback_query_id=cbid,
                       text=text, show_alert=alert)

async def send_document(s, cid, file_id, caption=""):
    return await _post(s, "sendDocument", chat_id=str(cid),
                       document=file_id, caption=str(caption)[:1024])

async def send_photo(s, cid, file_id, caption=""):
    return await _post(s, "sendPhoto", chat_id=str(cid),
                       photo=file_id, caption=str(caption)[:1024])

# ── Keyboards ──────────────────────────────────────────────────────────────
def inline(rows):
    return {"inline_keyboard": [
        [{"text": str(t), "callback_data": str(d)} for t, d in row]
        for row in rows
    ]}

def reply_kb(rows, one_time=False):
    return {
        "keyboard": [[{"text": str(t)} for t in row] for row in rows],
        "resize_keyboard": True,
        "one_time_keyboard": one_time,
    }

def remove_kb():
    return {"remove_keyboard": True}

def paginate(items, selected, prefix, page=0, cols=2):
    per   = 8
    chunk = items[page*per:(page+1)*per]
    rows, row = [], []
    for item in chunk:
        tick = "✅ " if item in selected else ""
        row.append((f"{tick}{item}", f"{prefix}:{item}"))
        if len(row) == cols:
            rows.append(row); row = []
    if row:
        rows.append(row)
    nav = []
    if page > 0:                  nav.append(("◀️ قبلی", f"{prefix}:PAGE:{page-1}"))
    if (page+1)*per < len(items): nav.append(("▶️ بعدی", f"{prefix}:PAGE:{page+1}"))
    if nav: rows.append(nav)
    rows.append([("✔️ تأیید", f"{prefix}:DONE")])
    return inline(rows)

# ── Helpers ────────────────────────────────────────────────────────────────
def msg_text(m):   return (m.get("text") or m.get("caption") or "").strip()
def msg_doc(m):    return m.get("document") or {}
def msg_photo(m):  return m.get("photo") or []
def msg_uid(m):    return m.get("from", {}).get("id", 0)
def msg_cid(m):    return m.get("chat", {}).get("id", 0)
def cb_uid(cb):    return cb.get("from", {}).get("id", 0)
def cb_cid(cb):    return cb.get("message", {}).get("chat", {}).get("id", 0)
def cb_mid(cb):    return cb.get("message", {}).get("message_id", 0)
