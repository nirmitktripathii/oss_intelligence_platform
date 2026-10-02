"""Pydantic v2 schemas for Multi-Channel Notifications."""

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


# What a destination may look like, per channel. The server sends to whatever passes, so each
# pattern is as narrow as the channel allows: a Telegram chat, a Discord webhook on Discord's own
# hosts (never an arbitrary URL), one plain email address, one phone number.
_DESTINATIONS = {
    ChannelType.TELEGRAM: (re.compile(r"^(-?[0-9]{5,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$"), "a Telegram chat id or @channel name"),
    ChannelType.DISCORD: (
        re.compile(r"^https://(?:(?:ptb|canary)\.)?discord(?:app)?\.com/api/webhooks/[0-9]{5,25}/[A-Za-z0-9_-]{10,200}$"),
        "a Discord webhook URL (https://discord.com/api/webhooks/...)",
    ),
    ChannelType.EMAIL: (re.compile(r"^[^@\s<>,;:\"'()\[\]\\]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$"), "one email address"),
    ChannelType.WHATSAPP: (re.compile(r"^(whatsapp:)?\+[0-9]{8,15}$"), "a phone number in international format (+...)"),
}


def check_destination(channel: ChannelType, destination: str) -> str:
    """The trimmed destination, or ``ValueError`` saying what that channel expects."""
    value = (destination or "").strip()
    pattern, expected = _DESTINATIONS[channel]
    if len(value) > 300 or not pattern.fullmatch(value):
        raise ValueError(f"The destination for {channel.value} must be {expected}.")
    return value


class SubscriptionCreate(BaseModel):
    channel: ChannelType
    destination: str = Field(
        ...,
        description="Telegram Chat ID, Discord Webhook URL, Email address, or WhatsApp phone number",
    )
    domains: Optional[List[str]] = Field(default=None, description="Optional domain filters")
    min_bounty: float = Field(default=0.0, ge=0.0, description="Minimum bounty USD threshold")
    difficulty: Optional[List[str]] = Field(default=None, description="Allowed difficulties")
    tech_stacks: Optional[List[str]] = Field(default=None, description="Preferred tech stacks")

    @model_validator(mode="after")
    def _destination_fits_channel(self):
        self.destination = check_destination(self.channel, self.destination)
        return self


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: ChannelType
    destination: str
    domains: Optional[List[str]] = None
    min_bounty: float = 0.0
    difficulty: Optional[List[str]] = None
    tech_stacks: Optional[List[str]] = None
    is_active: bool = True
    created_at: str


class TestNotificationRequest(BaseModel):
    channel: ChannelType
    destination: str
    custom_message: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _destination_fits_channel(self):
        self.destination = check_destination(self.channel, self.destination)
        return self


class TestNotificationResponse(BaseModel):
    # "success", "failed", or "not_configured" (the channel has no credentials on this server,
    # so nothing was sent).
    status: str
    channel: ChannelType
    destination: str
    message: str
    delivered: bool
