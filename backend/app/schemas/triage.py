"""Pydantic v2 schemas for AI Triage & AST File Localization."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
    created_at: datetime
    updated_at: Optional[datetime] = None
