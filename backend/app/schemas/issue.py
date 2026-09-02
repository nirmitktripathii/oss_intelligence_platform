"""Pydantic v2 schemas for Issues."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IssueDomain(str, Enum):
    AI_ML = "AI/ML"
    DATA = "Data"
    WEB = "Web"
    CLOUD_DEVOPS = "Cloud/DevOps"
    SECURITY = "Security"
    SYSTEMS = "Systems"


class IssueDifficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class LabelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    color: str = "6b7280"
    description: Optional[str] = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique composite identifier: owner/repo#number")
    repo_owner: str
    repo_name: str
    issue_number: int
    title: str
    body: Optional[str] = ""
    # Present only when the original body exceeded the LLM synthesis cap and a
    # precomputed summary was successfully stored. The raw `body` remains authoritative.
    body_summary: Optional[str] = None
    html_url: str
    author: str = "unknown"
    domain: IssueDomain
    tech_stack: List[str] = Field(default_factory=list)
    difficulty: IssueDifficulty
    estimated_hours: float
    has_bounty: bool = False
    bounty_amount_usd: Optional[float] = None
    bounty_source: Optional[str] = None
    bounty_url: Optional[str] = None
    hourly_roi: Optional[float] = None
    state: str = "open"
    comments_count: int = 0
    labels: List[Dict[str, Any]] = Field(default_factory=list)
    github_created_at: datetime
    github_updated_at: datetime
    indexed_at: datetime


class PaginatedIssuesResponse(BaseModel):
    items: List[IssueResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
