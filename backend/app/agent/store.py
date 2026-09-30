"""
Mission persistence for the agent planner.

Missions are written to Redis (shared across workers, survives a restart) and mirrored in a
bounded in-process map, so the agent still works when no Redis is configured (local dev; with
more than one worker, Redis is required for a request to find another worker's missions).

A session (one conversation) is the unit of ownership. Creating one returns a secret token
exactly once; only its hash is stored. Reading a mission, or approving its pending tool,
requires that token — a mission id alone grants nothing.
"""

import hashlib
import hmac
import secrets
import uuid
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
from app.cache import get_cached_json, set_cached_json
from app.config import settings
from app.schemas.agent import Mission

_LOCAL_MAX_MISSIONS = 200
_LOCAL_MAX_SESSIONS = 200
_SESSION_MAX_MISSIONS = 50


def _mission_key(mission_id: str) -> str:
    return f"gitscout:agent:mission:{mission_id}"


def _session_key(session_id: str) -> str:
    return f"gitscout:agent:session:{session_id}"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SessionNotFound(Exception):
    pass


class MissionStore:
    def __init__(self) -> None:
        self._missions: "OrderedDict[str, dict]" = OrderedDict()
        self._sessions: "OrderedDict[str, dict]" = OrderedDict()

    @staticmethod
    def _ttl() -> int:
        return int(getattr(settings, "AGENT_MISSION_TTL_SECONDS", 86400))

    # ── Missions ─────────────────────────────────────────────────────────── #

    async def save(self, mission: Mission) -> None:
        # The session token is a one-time secret for the caller; it is never persisted.
        data = mission.model_dump(mode="json", exclude={"session_token"})
        self._missions[mission.id] = data
        self._missions.move_to_end(mission.id)
        while len(self._missions) > _LOCAL_MAX_MISSIONS:
            self._missions.popitem(last=False)
        await set_cached_json(_mission_key(mission.id), data, ttl_seconds=self._ttl())

    async def get(self, mission_id: str) -> Optional[Mission]:
        data = await get_cached_json(_mission_key(mission_id)) or self._missions.get(mission_id)
        return Mission.model_validate(data) if data else None

    # ── Sessions ─────────────────────────────────────────────────────────── #

    async def _session(self, session_id: str) -> Optional[dict]:
        data = await get_cached_json(_session_key(session_id))
        if isinstance(data, dict) and "token_hash" in data:
            return data
        return self._sessions.get(session_id)

    async def _save_session(self, session_id: str, record: dict) -> None:
        self._sessions[session_id] = record
        self._sessions.move_to_end(session_id)
        while len(self._sessions) > _LOCAL_MAX_SESSIONS:
            self._sessions.popitem(last=False)
        await set_cached_json(_session_key(session_id), record, ttl_seconds=self._ttl())

    async def create_session(self) -> Tuple[str, str]:
        """Start a conversation. Returns ``(session_id, token)``; the token is shown only here."""
        session_id, token = uuid.uuid4().hex, secrets.token_urlsafe(32)
        await self._save_session(session_id, {"token_hash": _hash(token), "missions": []})
        return session_id, token

    async def check_session(self, session_id: str, token: Optional[str]) -> bool:
        record = await self._session(session_id)
        if record is None or not token:
            return False
        return hmac.compare_digest(record["token_hash"], _hash(token))

    async def add_to_session(self, mission: Mission) -> None:
        record = await self._session(mission.session_id)
        if record is None:
            raise SessionNotFound(mission.session_id)
        ids = [i for i in record.get("missions", []) if i != mission.id]
        record = {**record, "missions": (ids + [mission.id])[-_SESSION_MAX_MISSIONS:]}
        await self._save_session(mission.session_id, record)

    async def recent(self, session_id: str, limit: int, exclude: Optional[str] = None) -> List[Mission]:
        """The session's latest missions, oldest first, skipping ``exclude``."""
        record = await self._session(session_id)
        if limit <= 0 or record is None:
            return []
        ids = [i for i in record.get("missions", []) if i != exclude][-limit:]
        missions = [await self.get(i) for i in ids]
        return [m for m in missions if m is not None]


mission_store = MissionStore()
