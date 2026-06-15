<<<<<<< HEAD
# 📁 file: bale_api.py
import json

# Global token storage
token = ""

def set_token(t):
    global token
    token = t

def get_base_url():
    return f"https://tapi.bale.ai/bot{token}"

async def get_me(session):
    url = f"{get_base_url()}/getMe"
    async with session.get(url) as resp:
        return await resp.json()

async def get_updates(session, offset=0):
    url = f"{get_base_url()}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    async with session.get(url, params=params) as resp:
        return await resp.json()

async def send_message(session, chat_id, text, reply_markup=None):
    url = f"{get_base_url()}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup is not None:
        if isinstance(reply_markup, dict):
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        else:
            payload["reply_markup"] = reply_markup
            
    async with session.post(url, json=payload) as resp:
        return await resp.json()

async def answer_cb(session, callback_query_id):
    url = f"{get_base_url()}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    async with session.post(url, json=payload) as resp:
        return await resp.json()

async def edit_reply_markup(session, chat_id, message_id, reply_markup=None):
    url = f"{get_base_url()}/editMessageReplyMarkup"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if reply_markup is not None:
        if isinstance(reply_markup, dict):
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        else:
            payload["reply_markup"] = reply_markup
            
    async with session.post(url, json=payload) as resp:
        return await resp.json()


# --- Keyboard Helpers ---

def inline(nested_list):
    keyboard = []
    for row in nested_list:
        keyboard_row = []
        for text, data in row:
            keyboard_row.append({"text": text, "callback_data": data})
        keyboard.append(keyboard_row)
    return {"inline_keyboard": keyboard}

def reply_kb(nested_list):
    keyboard = []
    for row in nested_list:
        keyboard_row = []
        for btn in row:
            keyboard_row.append({"text": btn})
        keyboard.append(keyboard_row)
    return {"keyboard": keyboard, "resize_keyboard": True}

def remove_kb():
    return {"remove_keyboard": True}


def paginate(items, selected_list, prefix, page, cols=2, page_size=6):
    total_items = len(items)
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]
    
    keyboard = []
    row = []
    for item in page_items:
        label = f"✅ {item}" if item in selected_list else item
        row.append({"text": label, "callback_data": f"{prefix}:{item}"})
        if len(row) == cols:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ قبلی", "callback_data": f"{prefix}:PAGE:{page-1}"})
        
    nav_row.append({"text": "📥 ثبت و بستن", "callback_data": f"{prefix}:DONE"})
    
    if end_idx < total_items:
        nav_row.append({"text": "بعدی ➡️", "callback_data": f"{prefix}:PAGE:{page+1}"})
        
    keyboard.append(nav_row)
    return {"inline_keyboard": keyboard}


# --- Message and Callback Extractors ---

def msg_text(msg):
    return msg.get("text", "")

def msg_doc(msg):
    if "document" in msg:
        return msg["document"]
    elif "photo" in msg:
        photos = msg["photo"]
        if photos:
            return photos[-1]
    return None

def msg_uid(msg):
    return msg.get("from", {}).get("id")

def msg_cid(msg):
    return msg.get("chat", {}).get("id")

def cb_uid(cb):
    return cb.get("from", {}).get("id")

def cb_cid(cb):
    return cb.get("message", {}).get("chat", {}).get("id")

def cb_mid(cb):
    return cb.get("message", {}).get("message_id")
=======
"""بله HTTP API"""
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
                          timeout=aiohttp.ClientTimeout(total=20)) as r:
            d = await r.json()
            if not d.get("ok"): log.debug(f"{method}: {d.get('description')}")
            return d
    except asyncio.TimeoutError: return {"ok":False}
    except Exception as e: log.error(f"{method}: {e}"); return {"ok":False}

async def get_me(s): return await _post(s, "getMe")
async def get_updates(s, offset=0, timeout=25, limit=100):
    return await _post(s, "getUpdates", offset=offset, timeout=timeout, limit=limit)
async def send_message(s, cid, text, reply_markup=None):
    return await _post(s, "sendMessage", chat_id=str(cid), text=str(text)[:4096],
                       reply_markup=reply_markup, parse_mode="Markdown")
async def edit_message_text(s, cid, mid, text, reply_markup=None):
    return await _post(s, "editMessageText", chat_id=str(cid), message_id=mid,
                       text=str(text)[:4096], reply_markup=reply_markup, parse_mode="Markdown")
async def edit_reply_markup(s, cid, mid, reply_markup=None):
    return await _post(s, "editMessageReplyMarkup", chat_id=str(cid),
                       message_id=mid, reply_markup=reply_markup)
async def answer_cb(s, cb_id, text=None, alert=False):
    return await _post(s, "answerCallbackQuery", callback_query_id=cb_id,
                       text=text, show_alert=alert)
async def send_document(s, cid, file_id, caption=""):
    return await _post(s, "sendDocument", chat_id=str(cid), document=file_id, caption=caption[:1024])

def inline(rows):
    return {"inline_keyboard": [[{"text": str(t), "callback_data": str(d)} for t,d in row] for row in rows]}
def reply_kb(rows):
    return {"keyboard": [[{"text": str(t)} for t in row] for row in rows], "resize_keyboard": True}
def remove_kb():
    return {"remove_keyboard": True}
def paginate(items, sel, prefix, page=0, cols=2):
    per=10
    chunk=items[page*per:(page+1)*per]
    rows=[]
    row=[]
    for item in chunk:
        tick="✅ " if item in sel else ""
        row.append((f"{tick}{item}", f"{prefix}:{item}"))
        if len(row)==cols: rows.append(row); row=[]
    if row: rows.append(row)
    nav=[]
    if page>0: nav.append(("◀️ قبلی", f"{prefix}:PAGE:{page-1}"))
    if (page+1)*per<len(items): nav.append(("▶️ بعدی", f"{prefix}:PAGE:{page+1}"))
    if nav: rows.append(nav)
    rows.append([("✔️ تأیید", f"{prefix}:DONE")])
    return inline(rows)

def msg_text(msg): return (msg.get("text") or msg.get("caption") or "").strip()
def msg_doc(msg): return msg.get("document") or {}
def msg_uid(msg): return msg.get("from",{}).get("id",0)
def msg_cid(msg): return msg.get("chat",{}).get("id",0)
def cb_uid(cb): return cb.get("from",{}).get("id",0)
def cb_cid(cb): return cb.get("message",{}).get("chat",{}).get("id",0)
def cb_mid(cb): return cb.get("message",{}).get("message_id",0)
def fmt_salary(n):
    if not n: return "توافقی"
    s = str(int(n))
    return ",".join([s[max(0,i-3):i] for i in range(len(s),0,-3)][::-1])
>>>>>>> b5b8e6b86e8330ffa1cb6ebdffd753fca440247f
