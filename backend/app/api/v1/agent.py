"""
Agent planner endpoints: start a mission, read it, and answer its approval gate.

Ownership: a conversation is a session, and starting one returns a secret ``session_token``
exactly once. Every later read or approval must send it as ``X-Session-Token``; a mission id
alone grants nothing. A mission that is not yours answers 404, same as one that does not exist.

Each mission endpoint has a ``/stream`` twin that answers with Server-Sent Events, so a voice
or web client can show progress ("searching...", "analysing...") instead of waiting for a
minute of silence. Events: ``mission_started``, ``thinking``, ``step``, ``tool_start``,
``tool_done``, then one final ``mission`` (the full mission) or ``error``.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Set
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from app.agent.planner import EventSink, MissionNotFound, MissionPlanner, MissionStateError
from app.agent.store import mission_store
from app.agent.tools import AgentConfigError, ToolRegistry, configured_registry
from app.config import settings
from app.schemas.agent import (
    AgentTool,
    AgentToolsResponse,
    ApprovalRequest,
    Mission,
    MissionCreateRequest,
    MissionStatus,
)
from app.security.rate_limiter import limiter

logger = logging.getLogger("gitscout.agent")

router = APIRouter(prefix="/agent", tags=["Agent Planner"])

# A streamed mission keeps running if the client disconnects; hold the task so it is not
# garbage-collected mid-run.
_background: Set["asyncio.Task[Any]"] = set()


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


async def _owned_mission(mission_id: str, x_session_token: Optional[str] = Header(None)) -> Mission:
    mission = await mission_store.get(mission_id)
    if mission is None or not await mission_store.check_session(mission.session_id, x_session_token):
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found.")
    return mission


async def _session_for(req: MissionCreateRequest, token: Optional[str]) -> Optional[str]:
    """The session to continue, or ``None`` to start a new one. Continuing needs the token."""
    if req.session_id is None:
        return None
    if not await mission_store.check_session(req.session_id, token):
        raise HTTPException(status_code=403, detail="Unknown session, or a missing or wrong X-Session-Token.")
    return req.session_id


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _stream(run: Callable[[EventSink], Awaitable[Mission]]) -> StreamingResponse:
    """Run a mission in a background task and relay its progress as Server-Sent Events."""
    queue: "asyncio.Queue[Optional[tuple]]" = asyncio.Queue()

    async def sink(event: str, data: Dict[str, Any]) -> None:
        await queue.put((event, data))

    async def worker() -> None:
        try:
            mission = await run(sink)
            await queue.put(("mission", mission.model_dump(mode="json")))
        except MissionStateError as exc:
            await queue.put(("error", {"status": 409, "detail": str(exc)}))
        except MissionNotFound:
            await queue.put(("error", {"status": 404, "detail": "Mission not found."}))
        except Exception:
            logger.exception("[AGENT] streamed mission crashed")
            await queue.put(("error", {"status": 500, "detail": "The mission failed unexpectedly."}))
        finally:
            await queue.put(None)

    task = asyncio.create_task(worker())
    _background.add(task)
    task.add_done_callback(_background.discard)

    async def events():
        while (item := await queue.get()) is not None:
            yield _sse(*item)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
async def create_mission(
    request: Request, response: Response, req: MissionCreateRequest,
    x_session_token: Optional[str] = Header(None),
):
    """
    Plan and run a spoken request. Returns once the mission completes, fails, or reaches a
    tool that needs the user's approval (status ``awaiting_approval``). A new conversation's
    response carries the one-time ``session_token``.
    """
    registry = _registry()
    session_id = await _session_for(req, x_session_token)
    return await MissionPlanner(registry).start(req.utterance, session_id)


@router.post("/missions/stream", summary="Start a Mission (Server-Sent Events)")
@limiter.limit(_mission_rate_limit)
async def create_mission_stream(
    request: Request, req: MissionCreateRequest, x_session_token: Optional[str] = Header(None),
):
    """Same as ``POST /missions``, streaming progress events; the last event is the mission."""
    registry = _registry()
    session_id = await _session_for(req, x_session_token)
    return _stream(lambda sink: MissionPlanner(registry, on_event=sink).start(req.utterance, session_id))


@router.get("/missions/{mission_id}", response_model=Mission, summary="Get a Mission")
async def get_mission(mission: Mission = Depends(_owned_mission)):
    return mission


@router.post("/missions/{mission_id}/approval", response_model=Mission, summary="Approve or Reject a Pending Action")
@limiter.limit(_mission_rate_limit)
async def resolve_approval(
    request: Request, response: Response, req: ApprovalRequest,
    mission: Mission = Depends(_owned_mission),
):
    """
    Answer a mission's approval gate. Approving runs the pending tool with the arguments
    shown in the mission's last step; rejecting skips it. Either way the mission continues.
    """
    try:
        return await MissionPlanner(_registry()).resolve_approval(mission.id, req.approved, req.reason)
    except MissionNotFound:
        raise HTTPException(status_code=404, detail=f"Mission '{mission.id}' not found.")
    except MissionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/missions/{mission_id}/approval/stream", summary="Approve or Reject (Server-Sent Events)")
@limiter.limit(_mission_rate_limit)
async def resolve_approval_stream(
    request: Request, req: ApprovalRequest, mission: Mission = Depends(_owned_mission),
):
    """Same as the approval endpoint, streaming progress events; the last event is the mission."""
    registry = _registry()
    if mission.status != MissionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=409, detail=f"mission is '{mission.status.value}', not awaiting approval")
    return _stream(
        lambda sink: MissionPlanner(registry, on_event=sink).resolve_approval(mission.id, req.approved, req.reason)
    )
