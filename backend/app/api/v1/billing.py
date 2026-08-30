"""Billing, Checkout and Webhook endpoints for Dodo Payments and Lemon Squeezy."""

import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.billing.dodo import DodoPaymentsClient
from app.billing.lemonsqueezy import LemonSqueezyClient
from app.billing.webhook_handler import (
    WebhookProcessor,
    verify_dodo_signature,
    verify_lemonsqueezy_signature,
)
from app.config import settings
from app.database import get_db
from app.models.billing import BillingSubscription, CheckoutSession
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentProvider,
    SubscriptionStatusResponse,
)

router = APIRouter(tags=["Billing & Monetization"])


@router.post("/billing/checkout", response_model=CheckoutResponse, summary="Initiate Pro Tier Checkout Session")
async def create_checkout(
    req: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a hosted checkout session with Dodo Payments or Lemon Squeezy for GitScout Pro / Team tiers.
    """
    if req.provider == PaymentProvider.DODO:
        client = DodoPaymentsClient()
        session_id, checkout_url = await client.create_checkout_session(
            plan_id=req.plan_id,
            customer_email=req.customer_email,
            success_url=req.success_url,
            cancel_url=req.cancel_url,
        )
    elif req.provider == PaymentProvider.LEMON_SQUEEZY:
        ls_client = LemonSqueezyClient()
        session_id, checkout_url = await ls_client.create_checkout_session(
            plan_id=req.plan_id,
            customer_email=req.customer_email,
            success_url=req.success_url,
            cancel_url=req.cancel_url,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported payment provider: {req.provider}")

    # Record checkout session in DB
    session_obj = CheckoutSession(
        id=session_id,
        customer_email=req.customer_email,
        plan_id=req.plan_id,
        provider=req.provider.value,
        checkout_url=checkout_url,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(session_obj)
    await db.commit()

    return CheckoutResponse(
        checkout_url=checkout_url,
        session_id=session_id,
        provider=req.provider,
        plan_id=req.plan_id,
        customer_email=req.customer_email,
    )


@router.get("/billing/status", response_model=SubscriptionStatusResponse, summary="Get Subscription Status")
async def get_subscription_status(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a developer email has an active GitScout Pro or Team subscription.
    """
    stmt = select(BillingSubscription).where(BillingSubscription.customer_email == email)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()

    if not sub or sub.status != "active":
        return SubscriptionStatusResponse(
            customer_email=email,
            is_pro=False,
            status=sub.status if sub else "none",
        )

    return SubscriptionStatusResponse(
        customer_email=email,
        is_pro=True,
        plan_id=sub.plan_id,
        provider=sub.provider,
        status=sub.status,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
    )


@router.post("/billing/webhooks/dodo", summary="Dodo Payments Webhook Handler")
async def dodo_webhook(
    request: Request,
    x_dodo_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming Dodo Payments webhook notifications."""
    raw_body = await request.body()

    if not verify_dodo_signature(raw_body, x_dodo_signature, settings.DODO_PAYMENTS_WEBHOOK_KEY):
        raise HTTPException(status_code=401, detail="Invalid Dodo webhook HMAC signature.")

    try:
        event_data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")

    success = await WebhookProcessor.process_dodo_event(db, event_data)
    return {"received": True, "processed": success}


@router.post("/billing/webhooks/lemonsqueezy", summary="Lemon Squeezy Webhook Handler")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming Lemon Squeezy webhook notifications."""
    raw_body = await request.body()

    if not verify_lemonsqueezy_signature(raw_body, x_signature, settings.LEMON_SQUEEZY_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid Lemon Squeezy HMAC signature.")

    try:
        event_data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")

    success = await WebhookProcessor.process_lemonsqueezy_event(db, event_data)
    return {"received": True, "processed": success}
