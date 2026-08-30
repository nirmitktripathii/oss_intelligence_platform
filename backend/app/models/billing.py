"""SQLAlchemy ORM models for Billing, Subscriptions and Checkout Sessions."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import (
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(100), nullable=False, default="pro_monthly")
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # dodopayments, lemonsqueezy
    
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, cancelled, expired, past_due
    
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "plan_id": self.plan_id,
            "provider": self.provider,
            "provider_subscription_id": self.provider_subscription_id,
            "provider_customer_id": self.provider_customer_id,
            "status": self.status,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    checkout_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, completed, expired
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "customer_email": self.customer_email,
            "plan_id": self.plan_id,
            "provider": self.provider,
            "checkout_url": self.checkout_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
