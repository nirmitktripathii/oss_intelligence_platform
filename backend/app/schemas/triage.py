"""Pydantic v2 schemas for AI Triage & AST File Localization."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RankedFile(BaseModel):
    """An AST candidate re-ordered by the LLM with a newcomer-readable 'why this file'."""

    model_config = ConfigDict(extra="allow")

    file_path: str
    priority: int = Field(2, ge=1, le=3, description="1 primary edit site, 2 supporting, 3 test/config")
    reason: str = ""


class GroundedReproduction(BaseModel):
    """LLM reproduction script grounded in the localized files' real source."""

    model_config = ConfigDict(extra="allow")

    language: Optional[str] = None
    filename: Optional[str] = None
    code: Optional[str] = None
    cli_command: Optional[str] = None
    expected_failure: Optional[str] = None
    provider: Optional[str] = None


class GroundedPatch(BaseModel):
    """LLM unified-diff patch for the primary edit site, grounded in real source."""

    model_config = ConfigDict(extra="allow")

    primary_file: Optional[str] = None
    diff_snippet: Optional[str] = None
    explanation: Optional[str] = None
    regression_risk: Optional[str] = None
    provider: Optional[str] = None


class ContributingSummary(BaseModel):
    """Concrete rule bullets distilled from the repo's REAL CONTRIBUTING guide, with its source."""

    model_config = ConfigDict(extra="allow")

    guidelines: List[str] = Field(default_factory=list)
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    provider: Optional[str] = None


class SemanticAnalysis(BaseModel):
    """Structured output of the LLM enhancement layer. Present only when llm_enhanced is True."""

    model_config = ConfigDict(extra="allow")

    schema_version: Optional[str] = None
    semantic_root_cause: Optional[str] = None
    affected_subsystems: List[str] = Field(default_factory=list)
    investigation_entrypoint: Optional[str] = None
    rationale: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    provider: Optional[str] = Field(None, example="gemini:gemini-3.5-flash-lite")
    grounded_files: List[str] = Field(default_factory=list)
    # Grounded enrichment layers (any may be None => that card keeps its deterministic floor).
    localized_reranked: List[RankedFile] = Field(default_factory=list)
    reproduction: Optional[GroundedReproduction] = None
    patch: Optional[GroundedPatch] = None
    contributing: Optional[ContributingSummary] = None


class LocalizedFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_path: str = Field(..., example="fastapi/routing.py")
    line_range: Optional[str] = Field(None, example="145-180")
    confidence: float = Field(..., ge=0.0, le=1.0, example=0.92)
    rationale: str = Field(..., example="Stack trace and method signature match handler routing")


class FixPlanStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_number: int
    title: str
    description: str
    code_snippet: Optional[str] = None
    verification_command: Optional[str] = None


class TriageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    issue_id: str
    summary: str
    root_cause_analysis: str
    localized_files: List[LocalizedFile] = Field(default_factory=list)
    reproduction_code: str
    reproduction_lang: str = "python"
    reproduction_instructions: str
    fix_plan_steps: List[FixPlanStep] = Field(default_factory=list)
    contributing_guidelines_summary: Optional[str] = None

    # Canonical issue-body metadata. The raw body remains on IssueResponse; this field is
    # only the optional condensed form used by AI synthesis for oversized descriptions.
    body_summary: Optional[str] = None

    # AI enhancement layer — false/None means the deterministic AST floor was served as-is.
    llm_enhanced: bool = False
    llm_analysis: Optional[SemanticAnalysis] = None
    triage_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    created_at: datetime
    updated_at: Optional[datetime] = None
