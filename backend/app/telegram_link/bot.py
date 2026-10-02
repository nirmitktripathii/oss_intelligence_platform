"""
The Telegram Bot API calls the linking flow needs. The bot token is in every URL, so nothing here
logs or raises a URL, a response body, or a token: failures are reported by exception type only.
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("gitscout.telegram")
logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO line for a request is the URL, token included

_API = "https://api.telegram.org"
_username: Optional[str] = None


def configured() -> bool:
    """Can linking work here? Needs the bot token and the secret that authenticates its webhook."""
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_WEBHOOK_SECRET)


async def _call(method: str, payload: Optional[dict] = None) -> Optional[dict]:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(f"{_API}/bot{token}/{method}", json=payload or {})
    except httpx.HTTPError as exc:
        logger.warning("[TELEGRAM] %s failed (%s)", method, type(exc).__name__)
        return None
    if res.status_code != 200:
        logger.warning("[TELEGRAM] %s refused (HTTP %s)", method, res.status_code)
        return None
    try:
        body = res.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) and body.get("ok") else None


async def bot_username() -> Optional[str]:
    """The bot's @name (without the @): from settings, else asked of Telegram once and remembered."""
    global _username
    if settings.TELEGRAM_BOT_USERNAME:
        return settings.TELEGRAM_BOT_USERNAME.lstrip("@")
    if _username is None:
        body = await _call("getMe")
        name = ((body or {}).get("result") or {}).get("username")
        _username = name if isinstance(name, str) and name else None
    return _username


async def send_text(chat_id: str, text: str) -> bool:
    """Plain text (no markup) to one chat."""
    body = await _call("sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})
    return body is not None


async def register_webhook() -> bool:
    """Tell Telegram to deliver this bot's messages to TELEGRAM_WEBHOOK_URL, signed with the secret."""
    if not (configured() and settings.TELEGRAM_WEBHOOK_URL):
        return False
    body = await _call("setWebhook", {
        "url": settings.TELEGRAM_WEBHOOK_URL,
        "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
        "allowed_updates": ["message"],
        "drop_pending_updates": False,
    })
    return body is not None
