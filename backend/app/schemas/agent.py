"""Pydantic v2 schemas for the agent planner (Developer Mission Control)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MissionStatus(str, Enum):
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    AWAITING_APPROVAL = "awaiting_approval"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"


class MissionStep(BaseModel):
    """One tool call the planner decided on, and what came of it."""

    index: int
    thought: str = ""
    tool: str = Field(..., example="gitscout.search_issues")
    arguments: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    status: StepStatus
    result: Optional[Any] = None
    error: Optional[str] = None


class Mission(BaseModel):
    """A user request and the planner's progress on it. Doubles as the API response."""

    id: str
    session_id: str
    # Secret that owns the session. Present ONLY in the response that created the session;
    # send it back as the X-Session-Token header. Never stored, never returned again.
    session_token: Optional[str] = None
    utterance: str
    status: MissionStatus = MissionStatus.RUNNING
    steps: List[MissionStep] = Field(default_factory=list)
    # What the assistant says aloud: the final answer, or the approval question while paused.
    speech: Optional[str] = None
    # Optional longer markdown for a screen (ids, links, code) — never spoken.
    display: Optional[str] = None
    error: Optional[str] = None
    # Distinct "provider:model" labels that produced this mission's decisions.
    providers: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MissionCreateRequest(BaseModel):
    utterance: str = Field(..., min_length=1, max_length=2000, example="Find me an easy Python bounty")
    # Continue an existing conversation (follow-ups see earlier turns); requires the session's
    # X-Session-Token header. Omit to start a new one — the response carries its token.
    session_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class ApprovalRequest(BaseModel):
    approved: bool
    reason: Optional[str] = Field(None, max_length=500)


class AgentTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool


class AgentToolsResponse(BaseModel):
    tools: List[AgentTool] = Field(default_factory=list)
