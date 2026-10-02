"""
Sends the confirmation code. This is the only email the platform itself sends to an address a user
typed, so unlike the alert notifier it never "simulates" success: if nothing is set up to send, it
says so and the endpoint answers 503, rather than telling the user a mail is on its way.

SMTP is used when configured (a Gmail app password reaches any recipient). Resend is the fallback,
but without a verified domain Resend only delivers to its account owner, so it is a poor first choice.
"""

import logging
from email.message import EmailMessage

import aiosmtplib
import httpx

from app.config import settings

logger = logging.getLogger("gitscout.email_link")


def configured() -> bool:
    smtp = bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)
    return smtp or bool(settings.RESEND_API_KEY)


def _sender() -> str:
    return settings.SMTP_FROM_EMAIL if settings.SMTP_HOST else settings.RESEND_FROM_EMAIL


async def send_code(address: str, login: str, code: str, minutes: int) -> bool:
    """Mail ``code`` to ``address``. ``False`` if it could not be sent; the reason is logged, not returned."""
    subject = "Your Developer Mission Control confirmation code"
    text = (
        f"The GitHub account {login} asked to receive emails from Developer Mission Control at this address.\n\n"
        f"Confirmation code: {code}\n\n"
        f"It works for {minutes} minutes. If this was not you, ignore this email: nothing will be sent "
        "to you unless the code is entered."
    )
    if settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = _sender(), address, subject
        message.set_content(text)
        try:
            await aiosmtplib.send(
                message, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME, password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT == 465), start_tls=(settings.SMTP_PORT != 465), timeout=15.0,
            )
            return True
        except Exception as exc:
            logger.warning("[EMAIL-LINK] SMTP send failed: %s", type(exc).__name__)
    if settings.RESEND_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    json={"from": settings.RESEND_FROM_EMAIL, "to": [address], "subject": subject, "text": text},
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.warning("[EMAIL-LINK] Resend send failed: %s", type(exc).__name__)
    return False
