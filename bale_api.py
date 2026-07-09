"""Bale HTTP API - همراکار

Async wrapper around Bale Messenger Bot API.
Provides: send_message, edit_message_text, get_updates, inline/reply keyboards, pagination.
"""

import asyncio
import json
import aiohttp
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)
_BASE = ""
_BOT_USERNAME = ""
_PLATFORM = "bale"  # current active platform name

# ── Multi-provider session registry ──
_provider_sessions: Dict[str, aiohttp.ClientSession] = {}
_provider_bases: Dict[str, str] = {}
# Session id → full base URL (with token) for per-provider routing
_session_urls: Dict[int, str] = {}


def register_provider(platform: str, session: aiohttp.ClientSession, base_url: str):
    """Register a provider's session for cross-platform message routing."""
    _provider_sessions[platform] = session
    _provider_bases[platform] = base_url
    _session_urls[id(session)] = base_url  # per-session URL to avoid global race


def unregister_provider(platform: str):
    """Remove a provider from the registry."""
    session = _provider_sessions.pop(platform, None)
    _provider_bases.pop(platform, None)
    if session is not None:
        _session_urls.pop(id(session), None)


def get_provider_session(platform: str):
    """Get session for a specific platform (used for cross-platform sends)."""
    return _provider_sessions.get(platform)


def get_all_providers():
    """Return list of (platform_name, session, base_url) for all registered providers."""
    result = []
    for platform, session in _provider_sessions.items():
        base_url = _provider_bases.get(platform, "")
        result.append((platform, session, base_url))
    return result


async def send_to_all_providers(cid, text, reply_markup=None):
    """Send a message to a chat ID via ALL registered providers.
    Used for channel publishing where the same @channel exists on Bale and Telegram.

    Returns list of (platform, ok) tuples.
    """
    global _BASE
    results = []
    for platform, session, base_url in get_all_providers():
        saved_base = _BASE
        try:
            _BASE = base_url
            resp = await send_message(session, cid, text, reply_markup)
            results.append((platform, resp.get("ok", False)))
        except Exception as e:
            log.error(f"send_to_all_providers [{platform}] to {cid}: {e}")
            results.append((platform, False))
        finally:
            _BASE = saved_base
    return results


# ── Rate limiting for send_message (per-provider token buckets) ──
_MSG_LAST: Dict[str, float] = {}
_MSG_MIN_INTERVAL = 0.05  # 50ms between sends (~20 msg/s max)


def _get_rate_limit_key() -> str:
    """Return a rate-limit key based on current active BASE URL."""
    return _BASE or "default"


def set_token(t: str, base_url: str = "https://tapi.bale.ai/bot") -> None:
    """Store the bot token and build the base API URL."""
    global _BASE
    _BASE = f"{base_url}{t}"


def set_bot_username(u: str) -> None:
    """Store the bot username for generating share links."""
    global _BOT_USERNAME
    _BOT_USERNAME = u


def set_platform(p: str) -> None:
    """Set current active platform name (bale/telegram)."""
    global _PLATFORM
    _PLATFORM = p


def get_platform() -> str:
    """Get current active platform name."""
    return _PLATFORM


async def send_to_user(
    cid: int,
    text: str,
    reply_markup=None,
    user_platform: Optional[str] = None,
    default_session=None,
):
    """Send message to a user, routing to the correct provider based on their platform.

    Args:
        cid: Target chat ID.
        text: Message text.
        reply_markup: Keyboard markup.
        user_platform: The user's platform ('bale' or 'telegram'). If None, uses current provider.
        default_session: Fallback session if provider-specific one isn't available.

    Returns:
        API response dict.
    """
    # Determine which session to use
    session = None
    if user_platform and user_platform in _provider_sessions:
        session = _provider_sessions[user_platform]
    elif default_session is not None:
        session = default_session
    else:
        # Fallback: use first available provider session
        for s in _provider_sessions.values():
            session = s
            break

    if session is None:
        return {"ok": False, "description": "No provider session available"}

    # Validate session is still usable (not closed)
    if getattr(session, "closed", False):
        log.warning(
            f"send_to_user: session for platform={user_platform} is closed, unregistering"
        )
        if user_platform:
            unregister_provider(user_platform)
        # Fall back to current provider
        if default_session and not getattr(default_session, "closed", False):
            session = default_session
        else:
            # Try any other available session
            for plat, s in list(_provider_sessions.items()):
                if not getattr(s, "closed", False):
                    session = s
                    user_platform = plat
                    break
            else:
                return {"ok": False, "description": "All provider sessions are closed"}

    # Temporarily switch BASE to the target platform
    global _BASE
    saved_base = _BASE
    try:
        if user_platform and user_platform in _provider_bases:
            _BASE = _provider_bases[user_platform]
        return await send_message(session, cid, text, reply_markup)
    except Exception as e:
        log.error(f"send_to_user failed for cid={cid} platform={user_platform}: {e}")
        return {"ok": False, "description": str(e)}
    finally:
        _BASE = saved_base


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
    # Use per-session base URL if registered, otherwise fall back to global _BASE
    base_url = _session_urls.get(id(s), _BASE)
    url = f"{base_url}/{method}"
    last_err = None

    for attempt in range(retries + 1):
        try:
            async with s.post(
                url, json=kw, timeout=aiohttp.ClientTimeout(total=60)
            ) as r:
                try:
                    body = await r.json()
                except json.decoder.JSONDecodeError:
                    body = {
                        "ok": False,
                        "description": f"Invalid JSON response (status {r.status})",
                    }
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
    # Per-provider token bucket: enforce minimum interval between sends
    global _MSG_LAST
    key = _get_rate_limit_key()
    now = time.monotonic()
    last = _MSG_LAST.get(key, 0.0)
    elapsed = now - last
    if elapsed < _MSG_MIN_INTERVAL:
        await asyncio.sleep(_MSG_MIN_INTERVAL - elapsed)
    _MSG_LAST[key] = time.monotonic()

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
