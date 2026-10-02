"""ORM models for the email address a signed-in GitHub login has confirmed it owns."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmailLink(Base):
    """The one address a login confirmed with a code. Emails the agent sends go only here."""

    __tablename__ = "email_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)  # lower case
    address: Mapped[str] = mapped_column(String(254), nullable=False)  # lower case
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailLinkCode(Base):
    """
    A six-digit code emailed to an address someone asked to link. Only its hash is stored. Rows stay
    until they are an hour old, so the per-address and per-login hourly caps can count them.
    """

    __tablename__ = "email_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # lower case
    address: Mapped[str] = mapped_column(String(254), nullable=False, index=True)  # lower case
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
