"""Multi-Channel Notification subscription management and test dispatch endpoints."""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.config import settings
from app.dispatcher.router import ChannelNotConfigured, notification_router
from app.models.subscription import NotificationSubscription
from app.schemas.notification import (
    SubscriptionCreate,
    SubscriptionResponse,
    TestNotificationRequest,
    TestNotificationResponse,
)
from app.security.auth import AuthUser, require_writer
from app.security.rate_limiter import limiter

router = APIRouter(tags=["Notifications"])


def _notify_rate_limit() -> str:
    return settings.NOTIFY_RATE_LIMIT


@router.post(
    "/notifications/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to Multi-Channel Alerts",
)
@limiter.limit(_notify_rate_limit)
async def create_subscription(
    request: Request,
    response: Response,
    sub_in: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to real-time issue and bounty alerts via Telegram, Discord, Email, or WhatsApp.

    Open to anyone, but the destination must be well formed for its channel and the call is
    rate limited. Listing and removing subscriptions need a signed-in user.
    """
    # Check existing subscription for channel + destination
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.channel == sub_in.channel.value,
        NotificationSubscription.destination == sub_in.destination.strip(),
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.domains = sub_in.domains
        existing.min_bounty = sub_in.min_bounty
        existing.difficulty = sub_in.difficulty
        existing.tech_stacks = sub_in.tech_stacks
        existing.is_active = True
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        return SubscriptionResponse.model_validate(existing.to_dict())

    new_sub = NotificationSubscription(
        channel=sub_in.channel.value,
        destination=sub_in.destination.strip(),
        domains=sub_in.domains,
        min_bounty=sub_in.min_bounty,
        difficulty=sub_in.difficulty,
        tech_stacks=sub_in.tech_stacks,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)

    return SubscriptionResponse.model_validate(new_sub.to_dict())


@router.get(
    "/notifications/subscriptions",
    response_model=List[SubscriptionResponse],
    summary="List Active Subscriptions",
)
async def list_subscriptions(db: AsyncSession = Depends(get_db), _user: AuthUser = Depends(require_writer)):
    """List all registered notification alerts (they hold people's chat ids and email addresses)."""
    stmt = select(NotificationSubscription).order_by(NotificationSubscription.id.desc())
    res = await db.execute(stmt)
    subs = res.scalars().all()
    return [SubscriptionResponse.model_validate(s.to_dict()) for s in subs]


@router.post(
    "/notifications/test",
    response_model=TestNotificationResponse,
    summary="Test Notification Channel",
)
@limiter.limit(_notify_rate_limit)
async def test_notification(request: Request, response: Response, req: TestNotificationRequest, _user: AuthUser = Depends(require_writer)):
    """
    Send one verification message to a Telegram, Discord, Email, or WhatsApp destination.

    Needs a signed-in user: this sends real messages. If the channel has no credentials on this
    server nothing is sent and the answer says so (status "not_configured"), never "delivered".
    """
    try:
        delivered = await notification_router.dispatch_test_message(
            channel=req.channel,
            destination=req.destination,
            message=req.custom_message,
        )
    except ChannelNotConfigured:
        return TestNotificationResponse(
            status="not_configured",
            channel=req.channel,
            destination=req.destination,
            message=f"{req.channel.value} is not set up on this server, so nothing was sent.",
            delivered=False,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="The test message could not be sent.")
    return TestNotificationResponse(
        status="success" if delivered else "failed",
        channel=req.channel,
        destination=req.destination,
        message=req.custom_message or "Test message dispatched.",
        delivered=delivered,
    )


@router.delete("/notifications/{subscription_id}", summary="Unsubscribe Alert")
async def delete_subscription(
    subscription_id: int, db: AsyncSession = Depends(get_db), _user: AuthUser = Depends(require_writer)
):
    """Delete or deactivate a notification subscription."""
    stmt = select(NotificationSubscription).where(NotificationSubscription.id == subscription_id)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found.")

    await db.delete(sub)
    await db.commit()
    return {"status": "success", "message": f"Subscription {subscription_id} removed."}
