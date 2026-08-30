"""Multi-channel notification dispatcher package."""

from app.dispatcher.base import AlertPayload, BaseNotifier
from app.dispatcher.telegram import TelegramNotifier
from app.dispatcher.discord import DiscordNotifier
from app.dispatcher.email import EmailNotifier
from app.dispatcher.whatsapp import WhatsAppNotifier
from app.dispatcher.router import NotificationRouter, notification_router

__all__ = [
    "AlertPayload",
    "BaseNotifier",
    "TelegramNotifier",
    "DiscordNotifier",
    "EmailNotifier",
    "WhatsAppNotifier",
    "NotificationRouter",
    "notification_router",
]
