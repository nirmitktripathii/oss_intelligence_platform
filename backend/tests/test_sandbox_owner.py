"""Whose saved sandbox work sandbox_clone brings back is the signed-in user's, set by the server.

The Git/CI server saves a user's unfinished work under their GitHub login and restores it on their
next clone. If the model could name the owner, one user's mission (or an issue's text steering it)
could pull another user's work into its sandbox, so the login is injected here and hidden from it.
"""

import json
from typing import Any, Dict, List

import httpx
import pytest

from app.agent import tools as agent_tools
from app.agent.planner import PLANNER_SYSTEM_PROMPT, MissionPlanner
from app.agent.store import MissionStore
from app.agent.tools import ToolRegistry, ToolSpec
from app.api.v1 import agent as agent_api
from app.config import settings
from app.schemas.agent import MissionStatus
from app.security import auth
from app.security.rate_limiter import limiter
from app.triage.llm_engine import LLMTriageEngine


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", "x" * 40)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "*")
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", False)
    limiter.reset()


def _bearer(login: str) -> Dict[str, str]:
    return {"Authorization": "Bearer " + auth.issue_token(auth.KIND_SESSION, 600, sub=login)}


class CloneSource:
    """A tool source shaped like Git/CI: an approval-gated sandbox_clone that takes an owner."""

    name = "gitci"

    def __init__(self):
        self.calls: List[tuple] = []

    async def list_tools(self) -> List[ToolSpec]:
        return [ToolSpec(
            name="gitci.sandbox_clone",
            description="Clone a repo.",
            input_schema={
                "type": "object",
                "properties": {"repo_url": {"type": "string"}, "fresh": {"type": "boolean"},
                               "owner": {"type": "string"}},
                "required": ["repo_url"],
            },
            requires_approval=True,
        )]

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return {"sandbox_id": "0123456789ab"}


REPO = "https://github.com/o/r"


def _clone(**arguments) -> str:
    return json.dumps({"thought": "Clone.", "tool": "gitci.sandbox_clone", "arguments": {"repo_url": REPO, **arguments}})


def _final() -> str:
    return json.dumps({"thought": "Done.", "final": {"speech": "Done.", "display": ""}})


@pytest.fixture
def llm(monkeypatch):
    script: List[str] = []
    prompts: List[str] = []

    async def fake(prompt, system_prompt=None, temperature=0.2):
        prompts.append(prompt)
        return (script.pop(0), "gemini:test") if script else None

    monkeypatch.setattr(LLMTriageEngine, "query_llm_with_provenance", staticmethod(fake))
    fake.script, fake.prompts = script, prompts
    return fake


@pytest.mark.asyncio
async def test_the_model_cannot_see_or_set_the_owner(llm):
    source = CloneSource()
    catalog = await ToolRegistry([source]).catalog()
    assert set(catalog[0].input_schema["properties"]) == {"repo_url", "fresh"}

    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, workspace_owner="alice")
    llm.script += [_clone(owner="bob"), _final()]
    mission = await planner.start("fix the bug")
    assert mission.steps[0].arguments == {"repo_url": REPO}  # the approval card shows nothing of "bob"

    done = await planner.resolve_approval(mission.id, True)
    assert done.status == MissionStatus.COMPLETED
    assert source.calls == [("sandbox_clone", {"repo_url": REPO, "owner": "alice"})]


@pytest.mark.asyncio
async def test_fresh_is_the_model_s_to_pass(llm):
    source = CloneSource()
    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, workspace_owner="alice")
    llm.script += [_clone(fresh=True), _final()]
    await planner.resolve_approval((await planner.start("start over")).id, True)
    assert source.calls == [("sandbox_clone", {"repo_url": REPO, "fresh": True, "owner": "alice"})]


@pytest.mark.asyncio
async def test_without_a_signed_in_owner_the_clone_is_anonymous(llm):
    source = CloneSource()
    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4)
    llm.script += [_clone(owner="bob"), _final()]
    await planner.resolve_approval((await planner.start("fix")).id, True)
    assert source.calls == [("sandbox_clone", {"repo_url": REPO})]  # nothing saved or restored


@pytest.mark.asyncio
async def test_the_registry_drops_an_owner_the_caller_slipped_in():
    source = CloneSource()
    registry = ToolRegistry([source])
    await registry.call("gitci.sandbox_clone", {"repo_url": REPO, "owner": "bob"})
    assert source.calls[0][1] == {"repo_url": REPO}
    assert agent_tools.is_clone_tool("any.sandbox_clone") and not agent_tools.is_clone_tool("gitci.show_diff")


def test_the_rules_say_to_continue_saved_work():
    assert '"resumed"' in PLANNER_SYSTEM_PROMPT and "fresh=true" in PLANNER_SYSTEM_PROMPT
    assert "call sandbox_clone again" in PLANNER_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_the_api_clones_as_the_signed_in_login(client: httpx.AsyncClient, llm, monkeypatch):
    source = CloneSource()
    monkeypatch.setattr(agent_api, "configured_registry", lambda: ToolRegistry([source]))

    llm.script += [_clone(owner="mallory")]
    created = (await client.post("/api/v1/agent/missions", json={"utterance": "fix it"}, headers=_bearer("Alice"))).json()
    assert created["status"] == "awaiting_approval"

    llm.script += [_final()]
    headers = {**_bearer("Alice"), "X-Session-Token": created["session_token"]}
    approved = await client.post(f"/api/v1/agent/missions/{created['id']}/approval", json={"approved": True}, headers=headers)
    assert approved.json()["status"] == "completed"
    assert source.calls == [("sandbox_clone", {"repo_url": REPO, "owner": "alice"})]
