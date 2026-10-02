"""ORM models for linking a signed-in GitHub login to a Telegram chat."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TelegramLink(Base):
    """One signed-in user's Telegram chat. A login has one chat, and a chat belongs to one login."""

    __tablename__ = "telegram_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)  # lower case
    chat_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TelegramLinkCode(Base):
    """A one-time code behind a ``t.me/<bot>?start=<code>`` link. Only its hash is stored."""

    __tablename__ = "telegram_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    login: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # lower case
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
