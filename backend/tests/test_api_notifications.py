"""Unit tests for the Notifications API endpoints."""

import httpx
import pytest

from app.config import settings
from app.dispatcher.router import notification_router
from app.security import auth
from app.security.rate_limiter import limiter

WEBHOOK = "https://discord.com/api/webhooks/123456789012345678/abcDEF_ghi-JKLmno0123456789"


@pytest.fixture(autouse=True)
def signed_in_setup(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", "x" * 40)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "octocat")
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", False)
    monkeypatch.setattr(settings, "NOTIFY_RATE_LIMIT", "6/minute")
    limiter.reset()


def _bearer(login: str = "octocat") -> dict:
    return {"Authorization": "Bearer " + auth.issue_token(auth.KIND_SESSION, 600, sub=login)}


@pytest.fixture
def telegram_ready(monkeypatch):
    """Telegram looks configured, and what it would post is captured instead of sent."""
    sent = []

    async def capture(self, chat_id, text, reply_markup=None):
        sent.append((chat_id, text))
        return True

    notifier = notification_router.get_notifier("telegram")
    monkeypatch.setattr(notifier, "bot_token", "test-token")
    monkeypatch.setattr(notifier, "api_url", "https://telegram.invalid/bottest-token")
    monkeypatch.setattr(type(notifier), "_post_message", capture)
    return sent


@pytest.mark.asyncio
async def test_create_notification_subscription(client: httpx.AsyncClient):
    """Register a new Discord webhook subscription."""
    payload = {
        "channel": "discord",
        "destination": WEBHOOK,
        "domains": ["AI/ML", "Web"],
        "min_bounty": 100.0,
        "difficulty": ["Easy", "Medium"],
        "tech_stacks": ["Python", "FastAPI"],
    }
    response = await client.post("/api/v1/notifications/subscribe", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["channel"] == "discord"
    assert data["destination"] == WEBHOOK
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
    response = await client.get("/api/v1/notifications/subscriptions", headers=_bearer())
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["channel"] == "telegram"


@pytest.mark.asyncio
async def test_test_notification_dispatch(client: httpx.AsyncClient, telegram_ready):
    """Dispatch a test message to verify pairing."""
    payload = {
        "channel": "telegram",
        "destination": "987654321",
        "custom_message": "Pairing test verification.",
    }
    response = await client.post("/api/v1/notifications/test", json=payload, headers=_bearer())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["delivered"] is True


@pytest.mark.asyncio
async def test_delete_subscription(client: httpx.AsyncClient, seed_sample_issues):
    """Unsubscribe from alerts."""
    response = await client.delete("/api/v1/notifications/1", headers=_bearer())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify 404 when deleting already removed subscription
    response_404 = await client.delete("/api/v1/notifications/1", headers=_bearer())
    assert response_404.status_code == 404


# --- who may do what ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sending_listing_and_deleting_need_sign_in(client: httpx.AsyncClient, seed_sample_issues):
    test = {"channel": "telegram", "destination": "987654321"}
    assert (await client.post("/api/v1/notifications/test", json=test)).status_code == 401
    assert (await client.get("/api/v1/notifications/subscriptions")).status_code == 401
    assert (await client.delete("/api/v1/notifications/1")).status_code == 401
    # Still there afterwards.
    assert len((await client.get("/api/v1/notifications/subscriptions", headers=_bearer())).json()) >= 1


@pytest.mark.asyncio
async def test_a_signed_in_user_who_is_not_allowed_is_refused(client: httpx.AsyncClient):
    test = {"channel": "telegram", "destination": "987654321"}
    response = await client.post("/api/v1/notifications/test", json=test, headers=_bearer("mallory"))
    assert response.status_code == 403
    assert (await client.get("/api/v1/notifications/subscriptions", headers=_bearer("mallory"))).status_code == 403


@pytest.mark.asyncio
async def test_anonymous_agent_writes_do_not_open_the_message_relay(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", True)
    test = {"channel": "email", "destination": "someone@example.com"}
    assert (await client.post("/api/v1/notifications/test", json=test)).status_code == 401


@pytest.mark.asyncio
async def test_subscribing_stays_open_to_anyone(client: httpx.AsyncClient):
    response = await client.post(
        "/api/v1/notifications/subscribe", json={"channel": "email", "destination": "dev@example.com"}
    )
    assert response.status_code == 201


# --- destinations ------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "channel,destination",
    [
        ("discord", "http://169.254.169.254/latest/meta-data/"),  # not Discord, and a metadata address
        ("discord", "https://discord.com.evil.example/api/webhooks/123456789/abcdefghijk"),
        ("discord", "https://evil.example/api/webhooks/123456789/abcdefghijk"),
        ("email", "a@example.com, b@example.com"),
        ("email", "victim@example.com\nBcc: other@example.com"),
        ("email", "not-an-address"),
        ("telegram", "hello"),
        ("telegram", "123"),
        ("whatsapp", "12345"),
    ],
)
async def test_destinations_must_fit_their_channel(client: httpx.AsyncClient, channel, destination):
    body = {"channel": channel, "destination": destination}
    assert (await client.post("/api/v1/notifications/subscribe", json=body)).status_code == 422
    assert (await client.post("/api/v1/notifications/test", json=body, headers=_bearer())).status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "channel,destination",
    [("telegram", "-1001234567890"), ("telegram", "@gitscout_alerts"), ("email", "dev+tag@example.co.uk"), ("whatsapp", "+14155550123")],
)
async def test_ordinary_destinations_are_accepted(client: httpx.AsyncClient, channel, destination):
    body = {"channel": channel, "destination": f"  {destination}  "}
    response = await client.post("/api/v1/notifications/subscribe", json=body)
    assert response.status_code == 201
    assert response.json()["destination"] == destination


# --- honest results ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_unconfigured_channel_is_not_reported_as_delivered(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(notification_router.get_notifier("telegram"), "bot_token", "")
    body = {"channel": "telegram", "destination": "987654321"}
    response = await client.post("/api/v1/notifications/test", json=body, headers=_bearer())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_configured"
    assert data["delivered"] is False


@pytest.mark.asyncio
async def test_a_failed_send_is_reported_as_failed(client: httpx.AsyncClient, telegram_ready, monkeypatch):
    async def refuse(self, chat_id, text, reply_markup=None):
        return False

    monkeypatch.setattr(type(notification_router.get_notifier("telegram")), "_post_message", refuse)
    body = {"channel": "telegram", "destination": "987654321"}
    data = (await client.post("/api/v1/notifications/test", json=body, headers=_bearer())).json()
    assert (data["status"], data["delivered"]) == ("failed", False)


@pytest.mark.asyncio
async def test_the_test_message_text_is_escaped_and_capped(client: httpx.AsyncClient, telegram_ready):
    body = {"channel": "telegram", "destination": "987654321", "custom_message": "<a href='http://evil.example'>hi</a>"}
    assert (await client.post("/api/v1/notifications/test", json=body, headers=_bearer())).status_code == 200
    _, text = telegram_ready[0]
    assert "<a href" not in text and "&lt;a href" in text

    body["custom_message"] = "x" * 301
    assert (await client.post("/api/v1/notifications/test", json=body, headers=_bearer())).status_code == 422


@pytest.mark.asyncio
async def test_alerts_are_rate_limited(client: httpx.AsyncClient, telegram_ready):
    body = {"channel": "telegram", "destination": "987654321"}
    codes = [(await client.post("/api/v1/notifications/test", json=body, headers=_bearer())).status_code for _ in range(7)]
    assert codes[:6] == [200] * 6
    assert codes[6] == 429

    codes = [
        (await client.post("/api/v1/notifications/subscribe", json={"channel": "telegram", "destination": "55555"})).status_code
        for _ in range(7)
    ]
    assert codes[-1] == 429
