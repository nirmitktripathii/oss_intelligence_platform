"""Discord Webhook Notifier with rich multi-field embeds."""

import logging
from typing import Optional
import httpx
from app.config import settings
from app.dispatcher.base import AlertPayload, BaseNotifier

logger = logging.getLogger(__name__)

DOMAIN_COLORS = {
    "AI/ML": 0x8B5CF6,       # Purple
    "Data": 0x3B82F6,        # Blue
    "Web": 0x10B981,         # Emerald
    "Cloud/DevOps": 0x06B6D4,# Cyan
    "Security": 0xEF4444,    # Red
    "Systems": 0xF59E0B,     # Amber
}


class DiscordNotifier(BaseNotifier):
    """Dispatches webhook alerts to Discord channels."""

    def __init__(self, default_webhook_url: Optional[str] = None):
        self.default_webhook_url = default_webhook_url or settings.DISCORD_WEBHOOK_URL

    async def send_alert(self, destination: str, payload: AlertPayload) -> bool:
        """Send rich embed to Discord webhook destination."""
        webhook_url = destination or self.default_webhook_url
        if not webhook_url or not webhook_url.startswith("http"):
            logger.info(f"[SIMULATED DISCORD] Webhook alert -> {destination}: {payload.title}")
            return True

        color = DOMAIN_COLORS.get(payload.domain, 0x6366F1)
        fields = [
            {"name": "📦 Repository", "value": f"[{payload.repo}](https://github.com/{payload.repo})", "inline": True},
            {"name": "🎯 Domain", "value": payload.domain, "inline": True},
            {"name": "⚡ Difficulty", "value": f"{payload.difficulty} (~{payload.estimated_hours}h)", "inline": True},
            {"name": "🏷️ Tech Stack", "value": ", ".join(payload.tech_stack[:4]) if payload.tech_stack else "OSS", "inline": True},
        ]

        if payload.bounty_usd and payload.bounty_usd > 0:
            roi_text = f" (${payload.hourly_roi:.0f}/hr)" if payload.hourly_roi else ""
            fields.append({"name": "💰 Bounty", "value": f"${payload.bounty_usd:,.0f} USD{roi_text}", "inline": True})

        if payload.suggested_files:
            fields.append({"name": "📁 Target File", "value": f"`{payload.suggested_files[0]}`", "inline": False})

        embed = {
            "title": f"🚀 {payload.title[:200]}",
            "url": payload.html_url,
            "description": payload.summary[:300] if payload.summary else "Live issue indexed by GitScout.",
            "color": color,
            "fields": fields,
            "footer": {"text": "GitScout OSS Terminal • Instant Issue Intelligence"},
        }

        body = {
            "username": "GitScout Radar",
            "avatar_url": "https://gitscout.dev/icon.png",
            "embeds": [embed],
        }

        return await self._post_webhook(webhook_url, body)

    async def send_test_message(self, destination: str, message: str) -> bool:
        """Send test message to Discord webhook."""
        webhook_url = destination or self.default_webhook_url
        if not webhook_url or not webhook_url.startswith("http"):
            logger.info(f"[SIMULATED DISCORD] Test webhook -> {destination}: {message}")
            return True

        body = {
            "username": "GitScout Radar",
            "content": f"🔔 **GitScout Webhook Test**: {message}",
        }
        return await self._post_webhook(webhook_url, body)

    async def _post_webhook(self, url: str, body: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=body)
                res.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Failed to dispatch Discord webhook to {url}: {exc}")
            return False
