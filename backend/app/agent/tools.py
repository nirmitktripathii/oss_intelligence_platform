"""
Tool layer for the agent planner.

Every tool the planner can use comes from an MCP server over Streamable HTTP — the same
surface Alexa+ (or any MCP client) sees. Adding a capability (Git/CI, email) is therefore a
config change (AGENT_MCP_SERVERS), not a planner change.

Approval policy is decided HERE, on the planner's side, and is default-deny: a tool runs
without the user's confirmation only if the operator listed it in that server's
``auto_approve``. A server's own claims about its tools (e.g. readOnlyHint) are not trusted
for this, so a newly added or renamed tool can never start running unattended.
"""

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Protocol
from app.config import settings

logger = logging.getLogger("gitscout.agent")

_SERVER_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class ToolError(Exception):
    """A tool could not be run, or ran and reported an error. Safe to show the model."""


class AgentConfigError(Exception):
    """AGENT_MCP_SERVERS is present but malformed."""


@dataclass(frozen=True)
class ToolSpec:
    name: str                       # qualified: "<server>.<tool>"
    description: str
    input_schema: Dict[str, Any]
    requires_approval: bool


class ToolSource(Protocol):
    name: str

    async def list_tools(self) -> List[ToolSpec]: ...

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Any: ...


class McpToolSource:
    """
    One MCP server. ``target`` is its Streamable HTTP URL (or, in tests, an in-process
    ``MCPServer``). A fresh client is opened per operation: it costs a handshake but keeps
    the source stateless, so a dropped connection never poisons later missions.
    """

    def __init__(self, name: str, target: Any, auto_approve: Iterable[str] = (),
                 timeout: Optional[float] = None):
        self.name = name
        self._target = target
        self._auto_approve: FrozenSet[str] = frozenset(auto_approve)
        self._timeout = float(
            timeout if timeout is not None else getattr(settings, "AGENT_TOOL_TIMEOUT_SECONDS", 90.0)
        )

    def _client(self):
        from mcp import Client  # lazy: only deployments that enable the agent pay the import cost

        return Client(self._target, read_timeout_seconds=self._timeout)

    async def list_tools(self) -> List[ToolSpec]:
        async with self._client() as client:
            listed = await client.list_tools()
        return [
            ToolSpec(
                name=f"{self.name}.{tool.name}",
                description=(tool.description or "").strip(),
                input_schema=tool.input_schema or {},
                requires_approval=tool.name not in self._auto_approve,
            )
            for tool in listed.tools
        ]

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Any:
        async with self._client() as client:
            result = await client.call_tool(tool, arguments)
        text = "\n".join(
            block.text for block in (result.content or []) if getattr(block, "text", None)
        )
        if result.is_error:
            raise ToolError(text or "the tool reported an error")
        if result.structured_content is not None:
            return result.structured_content
        try:
            return json.loads(text)
        except ValueError:
            return text


class ToolRegistry:
    """The planner's view of every configured tool source."""

    def __init__(self, sources: Iterable[ToolSource]):
        self._sources: Dict[str, ToolSource] = {s.name: s for s in sources}

    async def catalog(self) -> List[ToolSpec]:
        """All reachable tools. An unreachable server is skipped so the others still work."""
        tools: List[ToolSpec] = []
        for source in self._sources.values():
            try:
                tools.extend(await source.list_tools())
            except Exception as exc:
                logger.warning("[AGENT] tool source %r is unreachable: %r", source.name, exc)
        return tools

    async def call(self, qualified_name: str, arguments: Dict[str, Any]) -> Any:
        server, _, tool = qualified_name.partition(".")
        source = self._sources.get(server)
        if source is None or not tool:
            raise ToolError(f"unknown tool '{qualified_name}'")
        return await source.call_tool(tool, arguments)


@lru_cache(maxsize=4)
def _parse_servers(raw: str) -> ToolRegistry:
    try:
        entries = json.loads(raw)
    except ValueError as exc:
        raise AgentConfigError(f"AGENT_MCP_SERVERS is not valid JSON: {exc}") from exc
    if not isinstance(entries, list) or not entries:
        raise AgentConfigError("AGENT_MCP_SERVERS must be a non-empty JSON list")

    sources: List[ToolSource] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise AgentConfigError("each AGENT_MCP_SERVERS entry must be an object")
        name, url = entry.get("name"), entry.get("url")
        auto_approve = entry.get("auto_approve", [])
        if not isinstance(name, str) or not _SERVER_NAME_RE.match(name):
            raise AgentConfigError(f"invalid server name {name!r} (lowercase letters, digits, underscore)")
        if any(s.name == name for s in sources):
            raise AgentConfigError(f"duplicate server name {name!r}")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise AgentConfigError(f"server {name!r} needs an http(s) url")
        if not isinstance(auto_approve, list) or not all(isinstance(t, str) for t in auto_approve):
            raise AgentConfigError(f"server {name!r}: auto_approve must be a list of tool names")
        sources.append(McpToolSource(name, url, auto_approve))
    return ToolRegistry(sources)


def configured_registry() -> Optional[ToolRegistry]:
    """
    The registry described by AGENT_MCP_SERVERS, or ``None`` when the agent is not
    configured. Raises :class:`AgentConfigError` when the setting is present but malformed.
    """
    raw = (getattr(settings, "AGENT_MCP_SERVERS", None) or "").strip()
    return _parse_servers(raw) if raw else None
