"""Pydantic v2 schemas for Billing and Monetization."""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class PaymentProvider(str, Enum):
    DODO = "dodopayments"
    LEMON_SQUEEZY = "lemonsqueezy"


class PlanTier(str, Enum):
    PRO_MONTHLY = "pro_monthly"
    PRO_YEARLY = "pro_yearly"
    TEAM_MONTHLY = "team_monthly"
    TEAM_YEARLY = "team_yearly"


class CheckoutRequest(BaseModel):
    plan_id: str = Field(default="pro_monthly", example="pro_monthly")
    customer_email: EmailStr = Field(..., example="developer@example.com")
    provider: PaymentProvider = Field(default=PaymentProvider.DODO)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    provider: PaymentProvider
    plan_id: str
    customer_email: str


class WebhookEvent(BaseModel):
    event_type: str
    provider: PaymentProvider
    data: Dict[str, Any]
    signature: Optional[str] = None


class SubscriptionStatusResponse(BaseModel):
    customer_email: str
    is_pro: bool
    plan_id: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    current_period_end: Optional[str] = None
