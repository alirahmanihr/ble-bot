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