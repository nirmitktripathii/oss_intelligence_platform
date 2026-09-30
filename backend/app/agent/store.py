"""
Mission persistence for the agent planner.

Missions are written to Redis (shared across workers, survives a restart) and mirrored in a
bounded in-process map, so the agent still works when no Redis is configured (local dev).
"""

from collections import OrderedDict
from typing import Dict, List, Optional
from app.cache import get_cached_json, set_cached_json
from app.config import settings
from app.schemas.agent import Mission

_LOCAL_MAX_MISSIONS = 200
_SESSION_MAX_MISSIONS = 50


def _mission_key(mission_id: str) -> str:
    return f"gitscout:agent:mission:{mission_id}"


def _session_key(session_id: str) -> str:
    return f"gitscout:agent:session:{session_id}"


class MissionStore:
    def __init__(self) -> None:
        self._missions: "OrderedDict[str, dict]" = OrderedDict()
        self._sessions: Dict[str, List[str]] = {}

    @staticmethod
    def _ttl() -> int:
        return int(getattr(settings, "AGENT_MISSION_TTL_SECONDS", 86400))

    async def save(self, mission: Mission) -> None:
        data = mission.model_dump(mode="json")
        self._missions[mission.id] = data
        self._missions.move_to_end(mission.id)
        while len(self._missions) > _LOCAL_MAX_MISSIONS:
            self._missions.popitem(last=False)
        await set_cached_json(_mission_key(mission.id), data, ttl_seconds=self._ttl())

    async def get(self, mission_id: str) -> Optional[Mission]:
        data = await get_cached_json(_mission_key(mission_id)) or self._missions.get(mission_id)
        return Mission.model_validate(data) if data else None

    async def _session_ids(self, session_id: str) -> List[str]:
        ids = await get_cached_json(_session_key(session_id))
        return ids if isinstance(ids, list) else list(self._sessions.get(session_id, []))

    async def add_to_session(self, mission: Mission) -> None:
        ids = [i for i in await self._session_ids(mission.session_id) if i != mission.id]
        ids = (ids + [mission.id])[-_SESSION_MAX_MISSIONS:]
        self._sessions[mission.session_id] = ids
        await set_cached_json(_session_key(mission.session_id), ids, ttl_seconds=self._ttl())

    async def recent(self, session_id: str, limit: int, exclude: Optional[str] = None) -> List[Mission]:
        """The session's latest missions, oldest first, skipping ``exclude``."""
        if limit <= 0:
            return []
        ids = [i for i in await self._session_ids(session_id) if i != exclude][-limit:]
        missions = [await self.get(i) for i in ids]
        return [m for m in missions if m is not None]


mission_store = MissionStore()
