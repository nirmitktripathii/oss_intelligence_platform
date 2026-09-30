"""Agent planner endpoints: start a mission, read it, and answer its approval gate."""

import logging
from fastapi import APIRouter, HTTPException, Request, Response
from app.agent.planner import MissionNotFound, MissionPlanner, MissionStateError
from app.agent.store import mission_store
from app.agent.tools import AgentConfigError, ToolRegistry, configured_registry
from app.config import settings
from app.schemas.agent import (
    AgentTool,
    AgentToolsResponse,
    ApprovalRequest,
    Mission,
    MissionCreateRequest,
)
from app.security.rate_limiter import limiter

logger = logging.getLogger("gitscout.agent")

router = APIRouter(prefix="/agent", tags=["Agent Planner"])


def _mission_rate_limit() -> str:
    # One mission fans out into several LLM and tool calls, so it gets its own, tighter limit.
    return settings.AGENT_RATE_LIMIT


def _registry() -> ToolRegistry:
    try:
        registry = configured_registry()
    except AgentConfigError as exc:
        logger.error("[AGENT] %s", exc)
        raise HTTPException(status_code=503, detail="The agent planner is misconfigured.")
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="The agent planner is not configured (set AGENT_MCP_SERVERS).",
        )
    return registry


@router.get("/tools", response_model=AgentToolsResponse, summary="List the Planner's Tools")
async def list_tools():
    """Every tool the planner can reach, and whether it pauses for the user's approval."""
    catalog = await _registry().catalog()
    return AgentToolsResponse(
        tools=[
            AgentTool(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
                requires_approval=t.requires_approval,
            )
            for t in catalog
        ]
    )


@router.post("/missions", response_model=Mission, summary="Start a Mission")
@limiter.limit(_mission_rate_limit)
async def create_mission(request: Request, response: Response, req: MissionCreateRequest):
    """
    Plan and run a spoken request. Returns once the mission completes, fails, or reaches a
    tool that needs the user's approval (status ``awaiting_approval``).
    """
    return await MissionPlanner(_registry()).start(req.utterance, req.session_id)


@router.get("/missions/{mission_id}", response_model=Mission, summary="Get a Mission")
async def get_mission(mission_id: str):
    mission = await mission_store.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return mission


@router.post("/missions/{mission_id}/approval", response_model=Mission, summary="Approve or Reject a Pending Action")
@limiter.limit(_mission_rate_limit)
async def resolve_approval(request: Request, response: Response, mission_id: str, req: ApprovalRequest):
    """
    Answer a mission's approval gate. Approving runs the pending tool with the arguments
    shown in the mission's last step; rejecting skips it. Either way the mission continues.
    """
    try:
        return await MissionPlanner(_registry()).resolve_approval(mission_id, req.approved, req.reason)
    except MissionNotFound:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    except MissionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
