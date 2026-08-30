"""Telegram Bot API Notifier with HTML formatting and inline interactive keyboard."""

import logging
from typing import Optional
import httpx
from app.config import settings
from app.dispatcher.base import AlertPayload, BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Dispatches real-time alerts to Telegram users / groups."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    async def send_alert(self, destination: str, payload: AlertPayload) -> bool:
        """Send formatted alert with inline buttons to Telegram chat."""
        if not self.bot_token or not self.api_url:
            logger.info(f"[SIMULATED TELEGRAM] Alert -> Chat {destination}: {payload.title}")
            return True

        bounty_line = f"💰 <b>Bounty:</b> ${payload.bounty_usd:,.0f} ({payload.hourly_roi:.0f}/hr)\n" if payload.bounty_usd else ""
        files_line = f"📁 <b>Target:</b> <code>{payload.suggested_files[0]}</code>\n" if payload.suggested_files else ""
        stacks = ", ".join(payload.tech_stack[:4]) if payload.tech_stack else "OSS"

        text = (
            f"🚀 <b>GitScout New Issue Alert</b>\n\n"
            f"📦 <b>Repo:</b> {payload.repo}\n"
            f"🎯 <b>Domain:</b> {payload.domain} | <b>Diff:</b> {payload.difficulty} (~{payload.estimated_hours}h)\n"
            f"🏷️ <b>Stack:</b> {stacks}\n"
            f"{bounty_line}"
            f"{files_line}\n"
            f"📌 <b>Title:</b> {payload.title}\n\n"
            f"<i>{payload.summary[:180]}...</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🐙 View on GitHub", "url": payload.html_url},
                    {"text": "🔍 AI Triage Drawer", "url": f"{settings.FRONTEND_URL}/issues/{payload.issue_id}"},
                ]
            ]
        }

        return await self._post_message(chat_id=destination, text=text, reply_markup=reply_markup)

    async def send_test_message(self, destination: str, message: str) -> bool:
        """Send a simple test message."""
        if not self.bot_token or not self.api_url:
            logger.info(f"[SIMULATED TELEGRAM] Test message -> Chat {destination}: {message}")
            return True

        text = f"🤖 <b>GitScout Notification Test</b>\n\n{message}"
        return await self._post_message(chat_id=destination, text=text)

    async def _post_message(self, chat_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
        payload_data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload_data["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.api_url}/sendMessage", json=payload_data)
                res.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Failed to dispatch Telegram message to {chat_id}: {exc}")
            return False
