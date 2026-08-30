"""Pydantic v2 schemas for Funded Bounties."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.issue import IssueDifficulty, IssueDomain


class BountyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_id: str
    repo_owner: str
    repo_name: str
    issue_number: int
    title: str
    html_url: str
    domain: IssueDomain
    tech_stack: List[str] = Field(default_factory=list)
    difficulty: IssueDifficulty
    estimated_hours: float
    bounty_amount_usd: float
    bounty_source: str
    bounty_url: Optional[str] = None
    hourly_roi: float
    github_created_at: datetime


class BountyListResponse(BaseModel):
    items: List[BountyResponse]
    total: int
    total_bounty_usd: float
    average_hourly_roi: float
