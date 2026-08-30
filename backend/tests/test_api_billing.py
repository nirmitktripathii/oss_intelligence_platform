"""Unit tests for Billing, Checkout sessions and Webhook processing."""

import hashlib
import hmac
import json
import pytest
import httpx
from app.config import settings


@pytest.mark.asyncio
async def test_create_dodo_checkout_session(client: httpx.AsyncClient):
    """Initiate a Dodo Payments checkout session."""
    payload = {
        "plan_id": "pro_monthly",
        "customer_email": "developer@example.com",
        "provider": "dodopayments",
    }
    response = await client.post("/api/v1/billing/checkout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "dodopayments"
    assert "checkout_url" in data
    assert "dodo_sess_" in data["session_id"]
    assert data["customer_email"] == "developer@example.com"


@pytest.mark.asyncio
async def test_create_lemonsqueezy_checkout_session(client: httpx.AsyncClient):
    """Initiate a Lemon Squeezy checkout session."""
    payload = {
        "plan_id": "team_yearly",
        "customer_email": "team_lead@example.com",
        "provider": "lemonsqueezy",
    }
    response = await client.post("/api/v1/billing/checkout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "lemonsqueezy"
    assert "checkout_url" in data
    assert "ls_sess_" in data["session_id"]


@pytest.mark.asyncio
async def test_get_billing_status_pro_user(client: httpx.AsyncClient, seed_sample_issues):
    """Check subscription status for an active Pro subscriber."""
    response = await client.get("/api/v1/billing/status?email=pro_user@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["is_pro"] is True
    assert data["status"] == "active"
    assert data["plan_id"] == "pro_monthly"


@pytest.mark.asyncio
async def test_get_billing_status_free_user(client: httpx.AsyncClient, seed_sample_issues):
    """Check subscription status for a free tier developer."""
    response = await client.get("/api/v1/billing/status?email=free_dev@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["is_pro"] is False


@pytest.mark.asyncio
async def test_dodo_webhook_success(client: httpx.AsyncClient):
    """Process a verified payment.succeeded webhook from Dodo Payments."""
    webhook_payload = {
        "type": "payment.succeeded",
        "data": {
            "subscription_id": "sub_dodo_999",
            "product_id": "pro_yearly",
            "customer": {"email": "new_pro@example.com"},
        },
    }
    raw_json = json.dumps(webhook_payload).encode("utf-8")
    signature = hmac.new(
        (settings.DODO_PAYMENTS_WEBHOOK_KEY or "").encode("utf-8"),
        raw_json,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/billing/webhooks/dodo",
        content=raw_json,
        headers={"x-dodo-signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True

    # Check status endpoint now shows Pro
    status_res = await client.get("/api/v1/billing/status?email=new_pro@example.com")
    assert status_res.json()["is_pro"] is True


@pytest.mark.asyncio
async def test_lemonsqueezy_webhook_success(client: httpx.AsyncClient):
    """Process an order_created webhook from Lemon Squeezy."""
    webhook_payload = {
        "meta": {"event_name": "order_created"},
        "data": {
            "id": "ls_sub_888",
            "attributes": {
                "user_email": "ls_user@example.com",
                "variant_name": "pro_monthly",
            },
        },
    }
    raw_json = json.dumps(webhook_payload).encode("utf-8")
    signature = hmac.new(
        (settings.LEMON_SQUEEZY_WEBHOOK_SECRET or "").encode("utf-8"),
        raw_json,
        hashlib.sha256,
    ).hexdigest()

    response = await client.post(
        "/api/v1/billing/webhooks/lemonsqueezy",
        content=raw_json,
        headers={"x-signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["processed"] is True

    status_res = await client.get("/api/v1/billing/status?email=ls_user@example.com")
    assert status_res.json()["is_pro"] is True
