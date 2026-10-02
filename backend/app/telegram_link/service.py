"""
Linking a signed-in GitHub login to a Telegram chat.

The flow proves both ends. The signed-in user asks for a one-time code (so we know the login), then
opens ``t.me/<bot>?start=<code>`` and presses Start in Telegram (so we know the chat). Neither side
can be filled in by anyone else: the code is unguessable, expires, works once, and is only stored
as a hash; the chat id comes from Telegram's own webhook call, which is authenticated by a secret.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.telegram import TelegramLink, TelegramLinkCode

# What a /start payload may contain (Telegram allows A-Z a-z 0-9 _ - up to 64 characters).
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def _key(login: str) -> str:
    return login.strip().lower()


async def create_code(db: AsyncSession, login: str) -> Tuple[str, int]:
    """A fresh one-time code for ``login`` and its lifetime in seconds. Replaces any earlier code."""
    ttl = int(settings.TELEGRAM_LINK_TTL_SECONDS)
    await db.execute(delete(TelegramLinkCode).where(
        (TelegramLinkCode.expires_at <= _now()) | (TelegramLinkCode.login == _key(login))
    ))
    code = secrets.token_urlsafe(24)  # 32 URL-safe characters, within the 64 Telegram allows
    db.add(TelegramLinkCode(code_hash=_hash(code), login=_key(login), expires_at=_now() + timedelta(seconds=ttl)))
    await db.commit()
    return code, ttl


async def redeem_code(db: AsyncSession, code: str, chat_id: str) -> Optional[str]:
    """
    Link ``chat_id`` to the login the code was issued for, and return that login; ``None`` if the
    code is malformed, unknown, expired or already used. The code is spent either way it matches.
    """
    if not CODE_PATTERN.fullmatch(code or ""):
        return None
    row = (await db.execute(select(TelegramLinkCode).where(
        TelegramLinkCode.code_hash == _hash(code), TelegramLinkCode.expires_at > _now()
    ))).scalar_one_or_none()
    if row is None:
        return None
    login = row.login
    await db.delete(row)
    # A login has one chat and a chat has one login: linking again replaces whatever was there.
    await db.execute(delete(TelegramLink).where((TelegramLink.login == login) | (TelegramLink.chat_id == chat_id)))
    db.add(TelegramLink(login=login, chat_id=chat_id))
    await db.commit()
    return login


async def chat_for(db: AsyncSession, login: Optional[str]) -> Optional[str]:
    """The chat this login linked, or ``None``."""
    if not login:
        return None
    return (await db.execute(select(TelegramLink.chat_id).where(TelegramLink.login == _key(login)))).scalar_one_or_none()


async def linked_at(db: AsyncSession, login: str) -> Optional[datetime]:
    return (await db.execute(select(TelegramLink.linked_at).where(TelegramLink.login == _key(login)))).scalar_one_or_none()


async def unlink_login(db: AsyncSession, login: str) -> bool:
    """Remove this login's link (and any code still waiting). Whether there was a link."""
    await db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.login == _key(login)))
    result = await db.execute(delete(TelegramLink).where(TelegramLink.login == _key(login)))
    await db.commit()
    return bool(result.rowcount)


async def unlink_chat(db: AsyncSession, chat_id: str) -> List[str]:
    """Remove every link to this chat (the person in it said /stop). The logins that were linked."""
    logins = list((await db.execute(select(TelegramLink.login).where(TelegramLink.chat_id == chat_id))).scalars())
    if logins:
        await db.execute(delete(TelegramLink).where(TelegramLink.chat_id == chat_id))
        await db.commit()
    return logins
