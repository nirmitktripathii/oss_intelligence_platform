"""
Email linking: lets a signed-in user choose the one address the agent may email.

1. ``POST /email/link {address}`` (signed in) mails a six-digit code to that address.
2. ``POST /email/confirm {code}`` with the code stores the address against the login.
3. ``send_email`` then goes to that address only. The model never names the recipient: the agent
   layer looks it up from the signed-in owner of the conversation (see ``app/agent/planner.py``).

Typing someone else's address only makes the platform send them one code mail that says who asked
and that it can be ignored; nothing is ever sent to an address that has not entered its code.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.email_link import mailer, service
from app.security.auth import AuthUser, require_writer
from app.security.rate_limiter import limiter

logger = logging.getLogger("gitscout.email_link")

router = APIRouter(prefix="/email", tags=["Email"])


class EmailStatus(BaseModel):
    configured: bool                     # this server can send confirmation codes
    linked: bool
    address: Optional[str] = None        # masked: a***e@example.com
    linked_at: Optional[datetime] = None


class LinkRequest(BaseModel):
    address: str = Field(max_length=254)


class LinkStarted(BaseModel):
    expires_in: int                      # seconds


class ConfirmRequest(BaseModel):
    code: str = Field(max_length=16)


def _rate_limit() -> str:
    return settings.NOTIFY_RATE_LIMIT


@router.get("/status", response_model=EmailStatus, summary="Is an email address linked for the signed-in user?")
async def link_status(user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db)):
    link = await service.link_for(db, user.login)
    return EmailStatus(
        configured=mailer.configured(), linked=link is not None,
        address=service.mask(link.address) if link else None, linked_at=link.linked_at if link else None,
    )


@router.post("/link", response_model=LinkStarted, summary="Mail a confirmation code to an address")
@limiter.limit(_rate_limit)
async def start_link(
    request: Request, response: Response, body: LinkRequest,
    user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db),
):
    if not mailer.configured():
        raise HTTPException(status_code=503, detail="Email is not set up on this server.")
    address = service.normalize_address(body.address)
    if address is None:
        raise HTTPException(status_code=422, detail="Enter one plain email address.")
    try:
        code, ttl = await service.create_code(db, user.login, address)
    except service.TooManyCodes:
        raise HTTPException(status_code=429, detail="Too many codes asked for this hour. Try again later.")
    if not await mailer.send_code(address, user.login, code, ttl // 60):
        # The failure is ours, not the user's: forget the code so the try does not count toward the caps.
        await service.discard_code(db, user.login, address, code)
        raise HTTPException(
            status_code=503, detail="Could not send the email. The problem is on our side, not with your address.",
        )
    return LinkStarted(expires_in=ttl)


@router.post("/confirm", response_model=EmailStatus, summary="Confirm the address with the emailed code")
@limiter.limit(_rate_limit)
async def confirm(
    request: Request, response: Response, body: ConfirmRequest,
    user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db),
):
    address = await service.confirm_code(db, user.login, body.code)
    if address is None:
        raise HTTPException(status_code=400, detail="That code is wrong or has expired. Ask for a new one.")
    link = await service.link_for(db, user.login)
    return EmailStatus(
        configured=mailer.configured(), linked=True, address=service.mask(address),
        linked_at=link.linked_at if link else None,
    )


@router.delete("/link", summary="Unlink the email address")
@limiter.limit(_rate_limit)
async def unlink(
    request: Request, response: Response,
    user: AuthUser = Depends(require_writer), db: AsyncSession = Depends(get_db),
):
    return {"status": "success", "was_linked": await service.unlink_login(db, user.login)}
