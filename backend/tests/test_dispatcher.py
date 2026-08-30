"""Unit tests for Multi-Channel Dispatchers and Subscription Router."""

import pytest
from app.dispatcher.base import AlertPayload
from app.dispatcher.discord import DiscordNotifier
from app.dispatcher.email import EmailNotifier
from app.dispatcher.router import NotificationRouter
from app.dispatcher.telegram import TelegramNotifier
from app.dispatcher.whatsapp import WhatsAppNotifier
from app.models.issue import Issue
from app.models.subscription import NotificationSubscription
from app.schemas.notification import ChannelType


@pytest.mark.asyncio
async def test_alert_payload_formatting():
    """Verify AlertPayload properties."""
    payload = AlertPayload(
        issue_id="fastapi/fastapi#500",
        title="Async bug",
        repo="fastapi/fastapi",
        html_url="https://github.com/fastapi/fastapi/issues/500",
        domain="Web",
        tech_stack=["Python", "FastAPI"],
        difficulty="Medium",
        estimated_hours=2.0,
        bounty_usd=200.0,
        hourly_roi=100.0,
    )
    assert "200" in payload.formatted_bounty
    assert "100/hr" in payload.formatted_bounty


@pytest.mark.asyncio
async def test_telegram_notifier_simulated(monkeypatch):
    """Verify Telegram notifier dispatches cleanly in test mode."""
    async def mock_post(self, *args, **kwargs):
        return True

    monkeypatch.setattr(TelegramNotifier, "_post_message", mock_post)

    notifier = TelegramNotifier()
    payload = AlertPayload(
        issue_id="fastapi/fastapi#1",
        title="Test issue",
        repo="fastapi/fastapi",
        html_url="https://github.com/fastapi/fastapi/issues/1",
    )
    result = await notifier.send_alert("123456", payload)
    assert result is True

    test_res = await notifier.send_test_message("123456", "Hello")
    assert test_res is True


@pytest.mark.asyncio
async def test_discord_notifier_simulated(monkeypatch):
    """Verify Discord webhook notifier in test mode."""
    async def mock_post(self, *args, **kwargs):
        return True

    monkeypatch.setattr(DiscordNotifier, "_post_webhook", mock_post)

    notifier = DiscordNotifier()
    payload = AlertPayload(
        issue_id="langchain-ai/langchain#2",
        title="Test LangChain issue",
        repo="langchain-ai/langchain",
        html_url="https://github.com/langchain-ai/langchain/issues/2",
        domain="AI/ML",
    )
    result = await notifier.send_alert("https://discord.com/api/webhooks/dummy", payload)
    assert result is True


@pytest.mark.asyncio
async def test_email_notifier_html():
    """Verify Email notifier renders complete HTML template."""
    notifier = EmailNotifier()
    payload = AlertPayload(
        issue_id="pola-rs/polars#3",
        title="Polars panic",
        repo="pola-rs/polars",
        html_url="https://github.com/pola-rs/polars/issues/3",
        bounty_usd=300.0,
        hourly_roi=75.0,
    )
    html = notifier._render_email_html(payload)
    assert "GitScout Issue Alert" in html
    assert "Polars panic" in html
    assert "$300" in html


@pytest.mark.asyncio
async def test_whatsapp_notifier_simulated():
    """Verify WhatsApp notifier in test mode."""
    notifier = WhatsAppNotifier()
    payload = AlertPayload(
        issue_id="kubernetes/kubernetes#4",
        title="Kubelet error",
        repo="kubernetes/kubernetes",
        html_url="https://github.com/kubernetes/kubernetes/issues/4",
    )
    result = await notifier.send_alert("+1234567890", payload)
    assert result is True


@pytest.mark.asyncio
async def test_notification_router_matching():
    """Verify router subscription matching rules."""
    router = NotificationRouter()

    sub = NotificationSubscription(
        channel="discord",
        destination="https://discord.com/webhook",
        domains=["AI/ML"],
        min_bounty=100.0,
        is_active=True,
    )

    # Issue 1: Web domain (does not match AI/ML filter)
    issue_web = Issue(
        id="fastapi/fastapi#1",
        repo_owner="fastapi",
        repo_name="fastapi",
        issue_number=1,
        title="Title",
        html_url="http://url",
        domain="Web",
        has_bounty=True,
        bounty_amount_usd=200.0,
        difficulty="Easy",
        estimated_hours=1.0,
    )
    assert router._matches_subscription(sub, issue_web) is False

    # Issue 2: AI/ML domain with $200 bounty (matches)
    issue_aiml = Issue(
        id="langchain-ai/langchain#2",
        repo_owner="langchain-ai",
        repo_name="langchain",
        issue_number=2,
        title="Title",
        html_url="http://url",
        domain="AI/ML",
        has_bounty=True,
        bounty_amount_usd=200.0,
        difficulty="Easy",
        estimated_hours=1.0,
    )
    assert router._matches_subscription(sub, issue_aiml) is True
