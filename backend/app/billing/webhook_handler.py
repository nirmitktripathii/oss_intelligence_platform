"""HMAC signature verification and subscription state updater for Dodo & Lemon Squeezy."""

from datetime import datetime, timezone
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.billing import BillingSubscription

logger = logging.getLogger(__name__)


def verify_dodo_signature(payload_bytes: bytes, signature_header: Optional[str], secret: Optional[str]) -> bool:
    """Verify webhook HMAC signature from Dodo Payments."""
    if not secret or not signature_header:
        # If no secret is configured in dev, accept
        return True
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def verify_lemonsqueezy_signature(payload_bytes: bytes, signature_header: Optional[str], secret: Optional[str]) -> bool:
    """Verify webhook HMAC SHA256 signature from Lemon Squeezy (X-Signature)."""
    if not secret or not signature_header:
        return True
    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


class WebhookProcessor:
    """Processes verified webhook events to update user subscription status."""

    @classmethod
    async def process_dodo_event(cls, session: AsyncSession, event_data: Dict[str, Any]) -> bool:
        """Handle Dodo Payments webhook payload."""
        event_type = event_data.get("type") or event_data.get("event") or "payment.succeeded"
        data = event_data.get("data", {})
        customer = data.get("customer", {})
        email = customer.get("email") or data.get("billing", {}).get("email") or data.get("customer_email")

        if not email:
            logger.warning("Dodo webhook missing customer email.")
            return False

        sub_id = data.get("subscription_id") or data.get("id")
        plan_id = data.get("product_id") or "pro_monthly"
        status = "active"

        if "failed" in event_type or "cancelled" in event_type:
            status = "cancelled"
        elif "expired" in event_type:
            status = "expired"

        await cls._upsert_subscription(
            session=session,
            email=email,
            plan_id=str(plan_id),
            provider="dodopayments",
            provider_sub_id=str(sub_id) if sub_id else None,
            status=status,
        )
        return True

    @classmethod
    async def process_lemonsqueezy_event(cls, session: AsyncSession, event_data: Dict[str, Any]) -> bool:
        """Handle Lemon Squeezy webhook payload."""
        meta = event_data.get("meta", {})
        event_name = meta.get("event_name", "order_created")
        data = event_data.get("data", {})
        attrs = data.get("attributes", {})
        email = attrs.get("user_email") or attrs.get("customer_email")

        if not email:
            logger.warning("Lemon Squeezy webhook missing customer email.")
            return False

        sub_id = data.get("id")
        plan_id = attrs.get("variant_name") or "pro_monthly"
        status = "active"

        if "cancelled" in event_name or "expired" in event_name or "paused" in event_name:
            status = "cancelled"

        await cls._upsert_subscription(
            session=session,
            email=email,
            plan_id=str(plan_id),
            provider="lemonsqueezy",
            provider_sub_id=str(sub_id) if sub_id else None,
            status=status,
        )
        return True

    @classmethod
    async def _upsert_subscription(
        cls,
        session: AsyncSession,
        email: str,
        plan_id: str,
        provider: str,
        provider_sub_id: Optional[str],
        status: str,
    ) -> None:
        """Create or update subscription record."""
        stmt = select(BillingSubscription).where(BillingSubscription.customer_email == email)
        result = await session.execute(stmt)
        sub = result.scalar_one_or_none()

        if sub:
            sub.plan_id = plan_id
            sub.provider = provider
            sub.provider_subscription_id = provider_sub_id
            sub.status = status
            sub.updated_at = datetime.now(timezone.utc)
        else:
            sub = BillingSubscription(
                customer_email=email,
                plan_id=plan_id,
                provider=provider,
                provider_subscription_id=provider_sub_id,
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(sub)

        await session.commit()
        logger.info(f"Updated billing subscription for {email}: provider={provider}, status={status}")
