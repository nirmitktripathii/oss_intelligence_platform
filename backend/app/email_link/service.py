"""
Linking a signed-in GitHub login to an email address it owns.

The agent may email a user, but only at an address that user proved they control. The signed-in
user types an address and we mail a six-digit code to it; typing the code back proves the mailbox.
The address a send goes to is then this stored one, never something the model or the request names.

Because anyone signed in could type someone else's address, a code mail is rate limited per address
and per login, says who asked, and tells the reader to ignore it if it was not them. A code is
short, so it expires, allows only a few wrong guesses, and is stored as a hash.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email_link import EmailLink, EmailLinkCode

# One plain address: no display name, no angle brackets, no list, no whitespace. Matches the check
# the Email Orchestrator makes again on its side.
ADDRESS_PATTERN = re.compile(r"^[A-Za-z0-9._%+'-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
CODE_PATTERN = re.compile(r"^[0-9]{6}$")
HOUR = timedelta(hours=1)


class TooManyCodes(Exception):
    """Too many codes asked for this address or by this login in the last hour."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _key(login: str) -> str:
    return login.strip().lower()


def normalize_address(raw: str) -> Optional[str]:
    """The address in canonical form, or ``None`` if it is not one plain email address."""
    address = (raw or "").strip().lower()
    if not address or len(address) > 254 or not ADDRESS_PATTERN.fullmatch(address):
        return None
    return address


def _hash(login: str, address: str, code: str) -> str:
    # Bound to the login and address so a code cannot be replayed for another pairing.
    return hashlib.sha256(f"{_key(login)}|{address}|{code}".encode()).hexdigest()


async def create_code(db: AsyncSession, login: str, address: str) -> Tuple[str, int]:
    """
    A fresh code for ``login`` to confirm ``address`` (already normalised), and its lifetime in
    seconds. Raises :class:`TooManyCodes` past the hourly caps. An earlier code stops working.
    """
    now = _now()
    await db.execute(delete(EmailLinkCode).where(EmailLinkCode.created_at <= now - HOUR))
    cap = int(settings.EMAIL_LINK_MAX_CODES_PER_HOUR)
    for column, value in ((EmailLinkCode.address, address), (EmailLinkCode.login, _key(login))):
        count = (await db.execute(select(func.count()).select_from(EmailLinkCode).where(column == value))).scalar_one()
        if count >= cap:
            await db.commit()
            raise TooManyCodes()
    # Older codes are kept (they count toward the caps) but never checked: confirm_code uses the newest.
    code = f"{secrets.randbelow(1_000_000):06d}"
    ttl = int(settings.EMAIL_LINK_TTL_SECONDS)
    db.add(EmailLinkCode(login=_key(login), address=address, code_hash=_hash(login, address, code),
                         expires_at=now + timedelta(seconds=ttl), created_at=now))
    await db.commit()
    return code, ttl


async def discard_code(db: AsyncSession, login: str, address: str, code: str) -> None:
    """Forget a code whose mail could not be sent, so a failure on our side does not use up the caps."""
    await db.execute(delete(EmailLinkCode).where(EmailLinkCode.code_hash == _hash(login, address, code)))
    await db.commit()


async def confirm_code(db: AsyncSession, login: str, code: str) -> Optional[str]:
    """
    Link the address the newest live code was sent to, and return it; ``None`` if the code is wrong,
    expired or out of attempts. A wrong guess uses an attempt, and the code is spent on the last one.
    """
    code = (code or "").strip()
    if not CODE_PATTERN.fullmatch(code):
        return None
    now = _now()
    row = (await db.execute(
        select(EmailLinkCode)
        .where(EmailLinkCode.login == _key(login), EmailLinkCode.expires_at > now)
        .order_by(EmailLinkCode.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if row is None or row.attempts >= int(settings.EMAIL_LINK_MAX_ATTEMPTS):
        return None
    if not hmac.compare_digest(row.code_hash, _hash(login, row.address, code)):
        row.attempts += 1
        await db.commit()
        return None
    address = row.address
    await db.execute(delete(EmailLinkCode).where(EmailLinkCode.login == _key(login)))
    await db.execute(delete(EmailLink).where(EmailLink.login == _key(login)))
    db.add(EmailLink(login=_key(login), address=address))
    await db.commit()
    return address


async def address_for(db: AsyncSession, login: Optional[str]) -> Optional[str]:
    """The address this login confirmed, or ``None``."""
    if not login:
        return None
    return (await db.execute(select(EmailLink.address).where(EmailLink.login == _key(login)))).scalar_one_or_none()


async def link_for(db: AsyncSession, login: str) -> Optional[EmailLink]:
    return (await db.execute(select(EmailLink).where(EmailLink.login == _key(login)))).scalar_one_or_none()


async def unlink_login(db: AsyncSession, login: str) -> bool:
    """Remove this login's address (and any code still waiting). Whether there was one."""
    await db.execute(delete(EmailLinkCode).where(EmailLinkCode.login == _key(login)))
    result = await db.execute(delete(EmailLink).where(EmailLink.login == _key(login)))
    await db.commit()
    return bool(result.rowcount)


def mask(address: str) -> str:
    """``alice@example.com`` -> ``a***e@example.com`` for showing back to the user."""
    local, _, domain = address.partition("@")
    shown = local if len(local) <= 2 else f"{local[0]}***{local[-1]}"
    return f"{shown}@{domain}"
