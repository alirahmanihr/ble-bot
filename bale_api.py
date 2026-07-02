"""Bale HTTP API - همراکار

Async wrapper around Bale Messenger Bot API.
Provides: send_message, edit_message_text, get_updates, inline/reply keyboards, pagination.
"""

import asyncio
import aiohttp
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)
_BASE = ""
_BOT_USERNAME = ""

# ── Rate limiting for send_message (simple token bucket) ──
_MSG_LAST = 0.0
_MSG_MIN_INTERVAL = 0.05  # 50ms between sends (~20 msg/s max)


def set_token(t: str) -> None:
    """Store the bot token and build the base API URL."""
    global _BASE
    _BASE = f"https://tapi.bale.ai/bot{t}"


def set_bot_username(u: str) -> None:
    """Store the bot username for generating share links."""
    global _BOT_USERNAME
    _BOT_USERNAME = u


def get_bot_username() -> str:
    """Return the stored bot username."""
    return _BOT_USERNAME


async def _post(
    s: aiohttp.ClientSession,
    method: str,
    raise_on_error: bool = False,
    retries: int = 0,
    **kw: Any,
) -> Dict[str, Any]:
    """Core POST to Bale API.

    Args:
        s: Active aiohttp ClientSession.
        method: API method name (e.g. 'sendMessage').
        raise_on_error: If True, raise RuntimeError on HTTP 400+ or timeout instead of returning error dict.
        retries: Number of retries on transient errors (timeout, 5xx). Max 3.
        **kw: JSON body parameters (None values are stripped).

    Returns:
        Parsed JSON response dict (always has 'ok' key).
    """
    if s is None:
        raise RuntimeError(
            f"API {method}: session is None — client session was closed or not initialized"
        )

    kw = {k: v for k, v in kw.items() if v is not None}
    url = f"{_BASE}/{method}"
    last_err = None

    for attempt in range(retries + 1):
        try:
            async with s.post(
                url, json=kw, timeout=aiohttp.ClientTimeout(total=60)
            ) as r:
                body = await r.json()
                if r.status >= 400:
                    log.error(
                        f"API {method} HTTP {r.status}: {body.get('description', body)}"
                    )
                    if raise_on_error:
                        raise RuntimeError(
                            f"API {method} HTTP {r.status}: {body.get('description', body)}"
                        )
                return body
        except asyncio.TimeoutError:
            last_err = f"timeout after 60s"
            log.error(f"API {method}: {last_err} | url={url}")
        except aiohttp.ClientError as e:
            last_err = str(e)
            log.error(f"API {method}: client error | {e}")
        except RuntimeError:
            raise  # let raise_on_error exceptions propagate
        except Exception as e:
            last_err = str(e)
            log.error(f"API {method}: unexpected error | {e}", exc_info=True)

        if attempt < retries:
            delay = 2**attempt  # exponential backoff: 1s, 2s, 4s
            log.info(f"API {method}: retry {attempt + 1}/{retries} in {delay}s")
            await asyncio.sleep(delay)

    # All retries exhausted or no retries configured
    if raise_on_error and last_err:
        raise RuntimeError(f"API {method}: {last_err}")
    return {"ok": False, "description": last_err or "unknown error"}


async def get_me(s: aiohttp.ClientSession) -> Dict[str, Any]:
    """Test bot token validity. Raises on failure (critical — bot cannot function)."""
    return await _post(s, "getMe", raise_on_error=True)


async def get_updates(
    s: aiohttp.ClientSession,
    offset: int = 0,
    timeout: int = 25,
    limit: int = 100,
) -> Dict[str, Any]:
    """Long-poll for new updates. Retries once on transient errors."""
    return await _post(
        s, "getUpdates", offset=offset, timeout=timeout, limit=limit, retries=1
    )


async def send_message(
    s: aiohttp.ClientSession,
    cid: int,
    text: str,
    reply_markup: Optional[Dict] = None,
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """Send a text message. Rate-limited at ~20 msg/s via token bucket.

    Args:
        s: ClientSession.
        cid: Target chat ID.
        text: Message body (truncated to 4096 chars). Supports Markdown.
        reply_markup: Inline or reply keyboard dict.
        raise_on_error: If True, raise on delivery failure.

    Returns:
        API response dict.
    """
    # Simple token bucket: enforce minimum interval between sends
    global _MSG_LAST
    now = time.monotonic()
    elapsed = now - _MSG_LAST
    if elapsed < _MSG_MIN_INTERVAL:
        await asyncio.sleep(_MSG_MIN_INTERVAL - elapsed)
    _MSG_LAST = time.monotonic()

    return await _post(
        s,
        "sendMessage",
        chat_id=str(cid),
        text=str(text)[:4096],
        reply_markup=reply_markup,
        parse_mode="Markdown",
        raise_on_error=raise_on_error,
        retries=1,
    )


async def edit_message_text(s, cid, mid, text, reply_markup=None):
    return await _post(
        s,
        "editMessageText",
        chat_id=str(cid),
        message_id=mid,
        text=str(text)[:4096],
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def edit_reply_markup(s, cid, mid, reply_markup=None):
    return await _post(
        s,
        "editMessageReplyMarkup",
        chat_id=str(cid),
        message_id=mid,
        reply_markup=reply_markup,
    )


async def answer_cb(s, cbid, text=None, alert=False):
    return await _post(
        s, "answerCallbackQuery", callback_query_id=cbid, text=text, show_alert=alert
    )


async def send_document(s, cid, file_id, caption=""):
    return await _post(
        s,
        "sendDocument",
        chat_id=str(cid),
        document=file_id,
        caption=str(caption)[:1024],
    )


async def send_photo(s, cid, file_id, caption=""):
    return await _post(
        s, "sendPhoto", chat_id=str(cid), photo=file_id, caption=str(caption)[:1024]
    )


# ── Keyboards ──────────────────────────────────────────────────────────────
def inline(rows):
    return {
        "inline_keyboard": [
            [{"text": str(t), "callback_data": str(d)} for t, d in row] for row in rows
        ]
    }


def reply_kb(rows, one_time=False):
    return {
        "keyboard": [[{"text": str(t)} for t in row] for row in rows],
        "resize_keyboard": True,
        "one_time_keyboard": one_time,
    }


def remove_kb():
    return {"remove_keyboard": True}


def paginate(items, selected, prefix, page=0, cols=2):
    per = 8
    chunk = items[page * per : (page + 1) * per]
    rows, row = [], []
    for item in chunk:
        tick = "✅ " if item in selected else ""
        row.append((f"{tick}{item}", f"{prefix}:{item}"))
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    nav = []
    if page > 0:
        nav.append(("◀️ قبلی", f"{prefix}:PAGE:{page - 1}"))
    if (page + 1) * per < len(items):
        nav.append(("▶️ بعدی", f"{prefix}:PAGE:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([("✔️ تأیید", f"{prefix}:DONE")])
    return inline(rows)


# ── Helpers ────────────────────────────────────────────────────────────────
def msg_text(m):
    return (m.get("text") or m.get("caption") or "").strip()


def msg_doc(m):
    return m.get("document") or {}


def msg_photo(m):
    return m.get("photo") or []


def msg_uid(m):
    return m.get("from", {}).get("id", 0)


def msg_cid(m):
    return m.get("chat", {}).get("id", 0)


def cb_uid(cb):
    return cb.get("from", {}).get("id", 0)


def cb_cid(cb):
    return cb.get("message", {}).get("chat", {}).get("id", 0)


def cb_mid(cb):
    return cb.get("message", {}).get("message_id", 0)
