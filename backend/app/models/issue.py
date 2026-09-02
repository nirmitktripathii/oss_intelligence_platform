"""SQLAlchemy ORM models for Issues and Bounties."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Issue(Base):
    __tablename__ = "issues"

    # Natural PK: "repo_owner/repo_name#issue_number"
    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    repo_owner: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    repo_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    # Long-description handling: when body exceeds settings.LLM_BODY_MAX_CHARS it is
    # condensed once (single flash-lite call at index time) into a <cap summary that
    # every AI feature reuses instead of re-summarizing per request. NULL => the body
    # already fits, or no LLM was available (read path falls back to body[:cap]).
    body_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # sha256 of the exact body that produced body_summary; lets a re-scrape skip the
    # LLM call when the description is unchanged (compute once).
    body_summary_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    
    # Categorization
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="Web")
    tech_stack: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium", index=True)
    estimated_hours: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    
    # Bounty details
    has_bounty: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    bounty_amount_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    bounty_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bounty_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hourly_roi: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    
    # GitHub metadata
    state: Mapped[str] = mapped_column(String(20), default="open", index=True)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    labels: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    github_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    triage_report: Mapped[Optional["TriageReport"]] = relationship(
        "TriageReport", back_populates="issue", uselist=False, cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "issue_number": self.issue_number,
            "title": self.title,
            "body": self.body or "",
            "body_summary": self.body_summary,
            "html_url": self.html_url,
            "author": self.author,
            "domain": self.domain,
            "tech_stack": self.tech_stack or [],
            "difficulty": self.difficulty,
            "estimated_hours": self.estimated_hours,
            "has_bounty": self.has_bounty,
            "bounty_amount_usd": self.bounty_amount_usd,
            "bounty_source": self.bounty_source,
            "bounty_url": self.bounty_url,
            "hourly_roi": self.hourly_roi,
            "state": self.state,
            "comments_count": self.comments_count,
            "labels": self.labels or [],
            "github_created_at": self.github_created_at,
            "github_updated_at": self.github_updated_at,
            "indexed_at": self.indexed_at,
        }
