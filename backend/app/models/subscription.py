"""SQLAlchemy ORM models for Multi-Channel Notification Subscriptions."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # telegram, discord, email, whatsapp
    destination: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    
    # Filter preferences
    domains: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=None)
    min_bounty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    difficulty: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=None)
    tech_stacks: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=None)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel,
            "destination": self.destination,
            "domains": self.domains,
            "min_bounty": self.min_bounty,
            "difficulty": self.difficulty,
            "tech_stacks": self.tech_stacks,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
