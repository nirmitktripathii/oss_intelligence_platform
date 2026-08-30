"""Pydantic v2 schemas for Multi-Channel Notifications."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


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
    custom_message: Optional[str] = None


class TestNotificationResponse(BaseModel):
    status: str
    channel: ChannelType
    destination: str
    message: str
    delivered: bool
