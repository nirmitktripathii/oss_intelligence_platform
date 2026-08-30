"""SQLAlchemy ORM models for AI Triage & AST File Localization."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TriageReport(Base):
    __tablename__ = "triage_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("issues.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    
    # List of localized files with confidence scores and rationale
    localized_files: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Reproduction snippet
    reproduction_code: Mapped[str] = mapped_column(Text, nullable=False)
    reproduction_lang: Mapped[str] = mapped_column(String(50), default="python", nullable=False)
    reproduction_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Step-by-step fix plan conforming to CONTRIBUTING.md
    fix_plan_steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    contributing_guidelines_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    issue: Mapped["Issue"] = relationship("Issue", back_populates="triage_report")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "summary": self.summary,
            "root_cause_analysis": self.root_cause_analysis,
            "localized_files": self.localized_files or [],
            "reproduction_code": self.reproduction_code,
            "reproduction_lang": self.reproduction_lang,
            "reproduction_instructions": self.reproduction_instructions,
            "fix_plan_steps": self.fix_plan_steps or [],
            "contributing_guidelines_summary": self.contributing_guidelines_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
