"""Notification Router matching subscriber preferences and broadcasting alerts."""

import asyncio
import logging
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dispatcher.base import AlertPayload, BaseNotifier
from app.dispatcher.discord import DiscordNotifier
from app.dispatcher.email import EmailNotifier
from app.dispatcher.telegram import TelegramNotifier
from app.dispatcher.whatsapp import WhatsAppNotifier
from app.models.issue import Issue
from app.models.subscription import NotificationSubscription
from app.schemas.notification import ChannelType

logger = logging.getLogger(__name__)


class NotificationRouter:
    """Routes alerts to subscribers based on matching rules across all channels."""

    def __init__(self):
        self.notifiers: Dict[str, BaseNotifier] = {
            ChannelType.TELEGRAM.value: TelegramNotifier(),
            ChannelType.DISCORD.value: DiscordNotifier(),
            ChannelType.EMAIL.value: EmailNotifier(),
            ChannelType.WHATSAPP.value: WhatsAppNotifier(),
        }

    def get_notifier(self, channel: str) -> Optional[BaseNotifier]:
        return self.notifiers.get(channel.lower())

    async def broadcast_issue_alert(self, session: AsyncSession, issue: Issue) -> int:
        """
        Query all active subscriptions, match against issue properties, and dispatch alerts.
        Returns total number of successful dispatches.
        """
        stmt = select(NotificationSubscription).where(NotificationSubscription.is_active.is_(True))
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()

        if not subscriptions:
            return 0

        # Build Alert Payload
        payload = AlertPayload(
            issue_id=issue.id,
            title=issue.title,
            repo=f"{issue.repo_owner}/{issue.repo_name}",
            html_url=issue.html_url,
            domain=issue.domain,
            tech_stack=issue.tech_stack or [],
            difficulty=issue.difficulty,
            estimated_hours=issue.estimated_hours,
            bounty_usd=issue.bounty_amount_usd,
            hourly_roi=issue.hourly_roi,
            summary=issue.body[:300] if issue.body else "",
            suggested_files=[f"{issue.repo_name}/core.py"],
        )

        dispatch_tasks = []
        for sub in subscriptions:
            if self._matches_subscription(sub, issue):
                notifier = self.get_notifier(sub.channel)
                if notifier:
                    dispatch_tasks.append(notifier.send_alert(sub.destination, payload))

        if not dispatch_tasks:
            return 0

        results = await asyncio.gather(*dispatch_tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Broadcasted alert for {issue.id} to {success_count}/{len(dispatch_tasks)} subscribers.")
        return success_count

    async def dispatch_test_message(self, channel: ChannelType, destination: str, message: Optional[str] = None) -> bool:
        """Send a test notification to verify channel pairing."""
        notifier = self.get_notifier(channel.value)
        if not notifier:
            raise ValueError(f"Unsupported notification channel: {channel}")

        test_msg = message or "Your GitScout notifications are active! You will receive alerts when matching open issues are found."
        return await notifier.send_test_message(destination, test_msg)

    def _matches_subscription(self, sub: NotificationSubscription, issue: Issue) -> bool:
        """Check if an issue satisfies subscription filters."""
        # 1. Bounty filter
        if sub.min_bounty > 0:
            if not issue.has_bounty or not issue.bounty_amount_usd or issue.bounty_amount_usd < sub.min_bounty:
                return False

        # 2. Domain filter
        if sub.domains and len(sub.domains) > 0:
            if issue.domain not in sub.domains:
                return False

        # 3. Difficulty filter
        if sub.difficulty and len(sub.difficulty) > 0:
            if issue.difficulty not in sub.difficulty:
                return False

        # 4. Tech stack filter
        if sub.tech_stacks and len(sub.tech_stacks) > 0:
            issue_stacks = set(s.lower() for s in (issue.tech_stack or []))
            required_stacks = set(s.lower() for s in sub.tech_stacks)
            if not issue_stacks.intersection(required_stacks):
                return False

        return True


notification_router = NotificationRouter()
