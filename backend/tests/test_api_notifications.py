"""Unit tests for the Notifications API endpoints."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_create_notification_subscription(client: httpx.AsyncClient):
    """Register a new Discord webhook subscription."""
    payload = {
        "channel": "discord",
        "destination": "https://discord.com/api/webhooks/test/12345",
        "domains": ["AI/ML", "Web"],
        "min_bounty": 100.0,
        "difficulty": ["Easy", "Medium"],
        "tech_stacks": ["Python", "FastAPI"],
    }
    response = await client.post("/api/v1/notifications/subscribe", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["channel"] == "discord"
    assert data["destination"] == "https://discord.com/api/webhooks/test/12345"
    assert data["min_bounty"] == 100.0
    assert data["is_active"] is True
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_upsert_existing_subscription(client: httpx.AsyncClient, seed_sample_issues):
    """Re-subscribing with identical channel and destination updates existing filters."""
    payload = {
        "channel": "telegram",
        "destination": "123456789",
        "domains": ["Data", "Systems"],
        "min_bounty": 200.0,
    }
    response = await client.post("/api/v1/notifications/subscribe", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["channel"] == "telegram"
    assert data["min_bounty"] == 200.0
    assert "Data" in data["domains"]


@pytest.mark.asyncio
async def test_list_subscriptions(client: httpx.AsyncClient, seed_sample_issues):
    """List all registered subscriptions."""
    response = await client.get("/api/v1/notifications/subscriptions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["channel"] == "telegram"


@pytest.mark.asyncio
async def test_test_notification_dispatch(client: httpx.AsyncClient, monkeypatch):
    """Dispatch a test message to verify pairing."""
    from app.dispatcher.telegram import TelegramNotifier

    async def mock_post(self, *args, **kwargs):
        return True

    monkeypatch.setattr(TelegramNotifier, "_post_message", mock_post)

    payload = {
        "channel": "telegram",
        "destination": "987654321",
        "custom_message": "Pairing test verification.",
    }
    response = await client.post("/api/v1/notifications/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["delivered"] is True


@pytest.mark.asyncio
async def test_delete_subscription(client: httpx.AsyncClient, seed_sample_issues):
    """Unsubscribe from alerts."""
    response = await client.delete("/api/v1/notifications/1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify 404 when deleting already removed subscription
    response_404 = await client.delete("/api/v1/notifications/1")
    assert response_404.status_code == 404
