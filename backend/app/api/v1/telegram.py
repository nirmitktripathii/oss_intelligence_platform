"""
Telegram linking: lets a signed-in user choose the chat that receives their mission reports.

1. ``POST /telegram/link`` (signed in) returns a ``t.me/<bot>?start=<code>`` link.
2. The user opens it and presses Start; Telegram calls ``POST /telegram/webhook`` with the code and
   the chat, and the chat is stored against the login the code was issued for.
3. Reports then go to that chat. The model never names the recipient: the agent layer looks it up
   from the signed-in owner of the conversation (see ``app/agent/planner.py``).

Only private chats can be linked. The bot says which GitHub account a chat was linked to and that
``/stop`` removes it, so someone talked into pressing Start for another person's code can see it
and undo it.
"""

import hmac
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security.auth import AuthUser, require_writer
from app.security.rate_limiter import limiter
from app.telegram_link import bot, service

logger = logging.getLogger("gitscout.telegram")

router = APIRouter(prefix="/telegram", tags=["Telegram"])


class LinkStatus(BaseModel):
    configured: bool                     # this server can link chats (bot token and webhook secret set)
    linked: bool
    linked_at: Optional[datetime] = None


class LinkStart(BaseModel):
    url: str                             # open this in Telegram and press Start
    expires_in: int                      # seconds


def _rate_limit() -> str:
    return settings.NOTIFY_RATE_LIMIT


@router.get("/status", response_model=LinkStatus, summary="Is Telegram linked for the signed-in user?")
async def link_status(user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db)):
    when = await service.linked_at(db, user.login)
    return LinkStatus(configured=bot.configured(), linked=when is not None, linked_at=when)


@router.post("/link", response_model=LinkStart, summary="Start linking a Telegram chat")
@limiter.limit(_rate_limit)
async def start_link(
    request: Request, response: Response,
    user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db),
):
    """A one-time link that connects the Telegram chat that opens it to the signed-in account."""
    if not bot.configured():
        raise HTTPException(status_code=503, detail="Telegram reports are not set up on this server.")
    name = await bot.bot_username()
    if not name:
        raise HTTPException(status_code=503, detail="Could not reach Telegram. Try again in a moment.")
    code, ttl = await service.create_code(db, user.login)
    return LinkStart(url=f"https://t.me/{name}?start={code}", expires_in=ttl)


@router.delete("/link", summary="Unlink Telegram")
@limiter.limit(_rate_limit)
async def unlink(
    request: Request, response: Response,
    user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db),
):
    return {"status": "success", "was_linked": await service.unlink_login(db, user.login)}


_HELP = (
    "This is the Developer Mission Control bot. To get mission reports here, sign in on the site, "
    "press \"Link Telegram\" and open the link it gives you."
)


async def _handle_message(db: AsyncSession, message: Dict[str, Any]) -> None:
    chat = message.get("chat") or {}
    if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
        return
    chat_id = str(chat["id"])
    command, _, argument = (message.get("text") or "").strip().partition(" ")
    command = command.split("@", 1)[0].lower()

    if command == "/start" and argument.strip():
        login = await service.redeem_code(db, argument.strip(), chat_id)
        if login:
            await bot.send_text(chat_id, (
                f"Linked to the GitHub account {login}. Mission reports from that account will be sent here. "
                "If that is not you, send /stop to unlink this chat."
            ))
        else:
            await bot.send_text(chat_id, (
                "That link has expired or was already used. Press \"Link Telegram\" on the site again for a new one."
            ))
    elif command == "/stop":
        logins = await service.unlink_chat(db, chat_id)
        await bot.send_text(chat_id, (
            "Unlinked. You will not get reports here any more." if logins else "This chat is not linked to anything."
        ))
    elif command in ("/start", "/help"):
        await bot.send_text(chat_id, _HELP)


@router.post("/webhook", include_in_schema=False)
async def webhook(
    request: Request,
    secret: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Telegram's calls. Only a request carrying the shared secret is believed."""
    expected = settings.TELEGRAM_WEBHOOK_SECRET or ""
    if not expected or not secret or not hmac.compare_digest(secret.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Forbidden.")
    try:
        update = await request.json()
        message = update.get("message") if isinstance(update, dict) else None
        if isinstance(message, dict):
            await _handle_message(db, message)
    except Exception:  # an update we cannot handle must not make Telegram retry it forever
        logger.exception("[TELEGRAM] webhook update failed")
    return {"ok": True}
