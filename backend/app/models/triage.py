"""SQLAlchemy ORM models for AI Triage & AST File Localization."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
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

    # ── AI semantic enhancement layer (nullable: absent => deterministic AST-only) ──
    # True only when a real LLM enrichment was produced and persisted.
    llm_enhanced: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    # Structured LLM output: semantic_root_cause, affected_subsystems, investigation_entrypoint,
    # rationale, confidence_score, provider (e.g. "gemini:gemini-3.5-flash-lite"), and later a grounded patch.
    llm_analysis: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Real, sortable confidence: the LLM's calibrated score when enhanced, else the top AST
    # localization confidence. Never a hardcoded placeholder. Indexed for the confidence sort.
    triage_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)

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
            "llm_enhanced": bool(self.llm_enhanced),
            "llm_analysis": self.llm_analysis or None,
            "triage_confidence": self.triage_confidence,
            # Keep the canonical raw issue body separate from the optional condensed body.
            # The relationship is normally loaded by the triage endpoint.
            "body_summary": self.issue.body_summary if self.issue else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
