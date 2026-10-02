"""
Agent planner endpoints: start a mission, read it, and answer its approval gate.

Ownership: a conversation is a session, and starting one returns a secret ``session_token``
exactly once. Every later read or approval must send it as ``X-Session-Token``; a mission id
alone grants nothing. A mission that is not yours answers 404, same as one that does not exist.

Sign-in: anyone may run read-only tools. A tool that changes things is hidden from, and refused
to, anyone who is not signed in as an allowed GitHub login (``Authorization: Bearer ...``, see
``/auth``), and only the user who started a conversation may approve its changes.

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
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.planner import EventSink, MissionNotFound, MissionPlanner, MissionStateError, WriteNotAllowed
from app.agent.store import mission_store
from app.agent.tools import AgentConfigError, ToolRegistry, configured_registry
from app.config import settings
from app.database import get_db
from app.schemas.agent import (
    AgentTool,
    AgentToolsResponse,
    ApprovalRequest,
    Mission,
    MissionCreateRequest,
    MissionStatus,
)
from app.security.auth import AuthUser, may_write, optional_user
from app.security.rate_limiter import limiter
from app.telegram_link import service as telegram_links

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


async def _can_write(user: Optional[AuthUser], session_id: Optional[str]) -> bool:
    """May this caller run tools that change things in this conversation?"""
    if settings.AGENT_ALLOW_ANONYMOUS_WRITES:
        return True
    if not may_write(user) or user is None:
        return False
    if session_id is None:  # a new conversation will belong to this user
        return True
    owner = await mission_store.session_owner(session_id)
    return owner is not None and owner.lower() == user.login.lower()


async def _report_chat(db: AsyncSession, user: Optional[AuthUser], can_write: bool) -> Optional[str]:
    """
    The Telegram chat this signed-in user linked, for the planner to aim ``send_report`` at; ``None``
    if they have not linked one. Only someone who may write has a use for it, and it is always the
    caller's own, never anything taken from the request body or the model.
    """
    if not can_write or user is None:
        return None
    return await telegram_links.chat_for(db, user.login)


async def _require_write_rights(user: Optional[AuthUser], mission: Mission) -> None:
    """Approving a change needs a signed-in, allowed user who owns the conversation."""
    if await _can_write(user, mission.session_id):
        return
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to approve this.", headers={"WWW-Authenticate": "Bearer"})
    raise HTTPException(status_code=403, detail="This account may not approve changes in this conversation.")


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
    x_session_token: Optional[str] = Header(None), user: Optional[AuthUser] = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Plan and run a spoken request. Returns once the mission completes, fails, or reaches a
    tool that needs the user's approval (status ``awaiting_approval``). A new conversation's
    response carries the one-time ``session_token``.
    """
    registry = _registry()
    session_id = await _session_for(req, x_session_token)
    can_write = await _can_write(user, session_id)
    planner = MissionPlanner(registry, can_write=can_write, report_chat_id=await _report_chat(db, user, can_write))
    return await planner.start(req.utterance, session_id, owner=user.login if user else None)


@router.post("/missions/stream", summary="Start a Mission (Server-Sent Events)")
@limiter.limit(_mission_rate_limit)
async def create_mission_stream(
    request: Request, req: MissionCreateRequest, x_session_token: Optional[str] = Header(None),
    user: Optional[AuthUser] = Depends(optional_user), db: AsyncSession = Depends(get_db),
):
    """Same as ``POST /missions``, streaming progress events; the last event is the mission."""
    registry = _registry()
    session_id = await _session_for(req, x_session_token)
    can_write = await _can_write(user, session_id)
    report_chat = await _report_chat(db, user, can_write)
    owner = user.login if user else None
    return _stream(
        lambda sink: MissionPlanner(registry, on_event=sink, can_write=can_write, report_chat_id=report_chat).start(
            req.utterance, session_id, owner
        )
    )


@router.get("/missions/{mission_id}", response_model=Mission, summary="Get a Mission")
async def get_mission(mission: Mission = Depends(_owned_mission)):
    return mission


@router.post("/missions/{mission_id}/approval", response_model=Mission, summary="Approve or Reject a Pending Action")
@limiter.limit(_mission_rate_limit)
async def resolve_approval(
    request: Request, response: Response, req: ApprovalRequest,
    mission: Mission = Depends(_owned_mission), user: Optional[AuthUser] = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Answer a mission's approval gate. Approving runs the pending tool with the arguments
    shown in the mission's last step; rejecting skips it. Either way the mission continues.
    """
    if req.approved:
        await _require_write_rights(user, mission)
    try:
        can_write = await _can_write(user, mission.session_id)
        planner = MissionPlanner(
            _registry(), can_write=can_write, report_chat_id=await _report_chat(db, user, can_write)
        )
        return await planner.resolve_approval(mission.id, req.approved, req.reason)
    except WriteNotAllowed as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except MissionNotFound:
        raise HTTPException(status_code=404, detail=f"Mission '{mission.id}' not found.")
    except MissionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/missions/{mission_id}/approval/stream", summary="Approve or Reject (Server-Sent Events)")
@limiter.limit(_mission_rate_limit)
async def resolve_approval_stream(
    request: Request, req: ApprovalRequest, mission: Mission = Depends(_owned_mission),
    user: Optional[AuthUser] = Depends(optional_user), db: AsyncSession = Depends(get_db),
):
    """Same as the approval endpoint, streaming progress events; the last event is the mission."""
    registry = _registry()
    if mission.status != MissionStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=409, detail=f"mission is '{mission.status.value}', not awaiting approval")
    if req.approved:
        await _require_write_rights(user, mission)
    can_write = await _can_write(user, mission.session_id)
    report_chat = await _report_chat(db, user, can_write)
    return _stream(
        lambda sink: MissionPlanner(registry, on_event=sink, can_write=can_write, report_chat_id=report_chat).resolve_approval(
            mission.id, req.approved, req.reason
        )
    )
