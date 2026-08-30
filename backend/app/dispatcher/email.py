"""Transactional Email Notifier via Resend API with aiosmtplib fallback."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from typing import Optional
import aiosmtplib
import httpx
from app.config import settings
from app.dispatcher.base import AlertPayload, BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Dispatches HTML email alerts to subscribers."""

    def __init__(
        self,
        resend_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        self.resend_api_key = resend_api_key or settings.RESEND_API_KEY
        self.from_email = from_email or settings.RESEND_FROM_EMAIL or settings.SMTP_FROM_EMAIL

    async def send_alert(self, destination: str, payload: AlertPayload) -> bool:
        """Send formatted HTML email alert to recipient."""
        subject = f"[GitScout] New {payload.domain} Issue: {payload.title[:60]}"
        html_content = self._render_email_html(payload)

        # 1. Try Resend API if API Key is configured
        if self.resend_api_key:
            success = await self._send_via_resend(destination, subject, html_content)
            if success:
                return True

        # 2. Try SMTP fallback if SMTP Host is configured
        if settings.SMTP_HOST:
            success = await self._send_via_smtp(destination, subject, html_content)
            if success:
                return True

        # 3. Development simulation mode
        logger.info(f"[SIMULATED EMAIL] Alert -> {destination}: {subject}")
        return True

    async def send_test_message(self, destination: str, message: str) -> bool:
        """Send verification test email."""
        subject = "[GitScout] Notification Test"
        html_content = f"<h2>GitScout Email Test</h2><p>{message}</p>"

        if self.resend_api_key:
            return await self._send_via_resend(destination, subject, html_content)
        if settings.SMTP_HOST:
            return await self._send_via_smtp(destination, subject, html_content)

        logger.info(f"[SIMULATED EMAIL] Test message -> {destination}: {message}")
        return True

    async def _send_via_resend(self, to_email: str, subject: str, html_body: str) -> bool:
        headers = {
            "Authorization": f"Bearer {self.resend_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post("https://api.resend.com/emails", json=body, headers=headers)
                res.raise_for_status()
                return True
        except Exception as exc:
            logger.warning(f"Resend email dispatch failed to {to_email}: {exc}")
            return False

    async def _send_via_smtp(self, to_email: str, subject: str, html_body: str) -> bool:
        message = MIMEMultipart("alternative")
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=(settings.SMTP_PORT == 465),
                start_tls=(settings.SMTP_PORT == 587),
                timeout=10.0,
            )
            return True
        except Exception as exc:
            logger.error(f"SMTP dispatch failed to {to_email}: {exc}")
            return False

    def _render_email_html(self, payload: AlertPayload) -> str:
        bounty_badge = ""
        if payload.bounty_usd and payload.bounty_usd > 0:
            roi = f" (${payload.hourly_roi:.0f}/hr)" if payload.hourly_roi else ""
            bounty_badge = f"<div style='background:#10B981;color:#fff;padding:8px 12px;border-radius:6px;display:inline-block;margin-bottom:12px;'>💰 Bounty: ${payload.bounty_usd:,.0f} USD{roi}</div>"

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1f2937; background-color: #f9fafb; padding: 24px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; padding: 24px;">
                <div style="font-size: 12px; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                    GitScout Issue Alert • {payload.domain}
                </div>
                <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #111827;">{payload.title}</h2>
                {bounty_badge}
                <div style="background: #f3f4f6; border-radius: 6px; padding: 12px; font-size: 14px; margin-bottom: 16px;">
                    <p style="margin: 0 0 6px 0;"><strong>Repository:</strong> {payload.repo}</p>
                    <p style="margin: 0 0 6px 0;"><strong>Difficulty:</strong> {payload.difficulty} (~{payload.estimated_hours} hours)</p>
                    <p style="margin: 0;"><strong>Tech Stack:</strong> {', '.join(payload.tech_stack) if payload.tech_stack else 'OSS'}</p>
                </div>
                <p style="color: #4b5563; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
                    {payload.summary}
                </p>
                <div style="text-align: center;">
                    <a href="{payload.html_url}" style="background: #111827; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; display: inline-block; margin-right: 8px;">View on GitHub</a>
                    <a href="{settings.FRONTEND_URL}/issues/{payload.issue_id}" style="background: #6366F1; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; display: inline-block;">Open AI Triage</a>
                </div>
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 24px 0 12px 0;">
                <p style="font-size: 11px; color: #9ca3af; text-align: center; margin: 0;">
                    You are receiving this because you subscribed on GitScout. <a href="{settings.FRONTEND_URL}/settings" style="color: #6366F1;">Manage Preferences</a>
                </p>
            </div>
        </body>
        </html>
        """
