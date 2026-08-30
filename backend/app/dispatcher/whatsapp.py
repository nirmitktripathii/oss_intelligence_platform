"""Twilio WhatsApp Pro Notifier."""

import logging
from typing import Optional
import httpx
from app.config import settings
from app.dispatcher.base import AlertPayload, BaseNotifier

logger = logging.getLogger(__name__)


class WhatsAppNotifier(BaseNotifier):
    """Dispatches high-priority WhatsApp alerts via Twilio API."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_WHATSAPP_NUMBER

    async def send_alert(self, destination: str, payload: AlertPayload) -> bool:
        """Send WhatsApp message to recipient phone number."""
        bounty_str = f"💰 Bounty: ${payload.bounty_usd:,.0f} USD ({payload.hourly_roi:.0f}/hr)\n" if payload.bounty_usd else ""
        msg_body = (
            f"🚀 *GitScout Pro Alert*\n\n"
            f"📦 *Repo:* {payload.repo}\n"
            f"🎯 *Domain:* {payload.domain} | *Difficulty:* {payload.difficulty} (~{payload.estimated_hours}h)\n"
            f"{bounty_str}"
            f"📌 *Title:* {payload.title}\n\n"
            f"🔗 View: {payload.html_url}\n"
            f"⚡ AI Triage: {settings.FRONTEND_URL}/issues/{payload.issue_id}"
        )

        return await self._dispatch_twilio_message(destination, msg_body)

    async def send_test_message(self, destination: str, message: str) -> bool:
        """Send verification test WhatsApp message."""
        body = f"🤖 *GitScout WhatsApp Test*: {message}"
        return await self._dispatch_twilio_message(destination, body)

    async def _dispatch_twilio_message(self, to_number: str, text: str) -> bool:
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.info(f"[SIMULATED WHATSAPP] Message -> {to_number}: {text[:80]}...")
            return True

        to_formatted = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        from_formatted = self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": to_formatted,
            "From": from_formatted,
            "Body": text,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                res.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Twilio WhatsApp dispatch failed to {to_number}: {exc}")
            return False
