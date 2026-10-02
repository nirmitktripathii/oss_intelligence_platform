"""Whose saved sandbox work is listed, restored or deleted is the signed-in user's, set by the server.

The Git/CI server saves a user's unfinished work under their GitHub login, one record per branch.
If the model could name the owner, one user's mission (or an issue's text steering it) could pull
another user's work into its sandbox, or delete it, so the login is injected here and hidden from it.
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


def _spec(name: str, properties: Dict[str, Any], required: List[str], approval: bool) -> ToolSpec:
    return ToolSpec(name=f"gitci.{name}", description=name, requires_approval=approval,
                    input_schema={"type": "object", "properties": properties, "required": required})


class CloneSource:
    """A tool source shaped like Git/CI: the saved-work tools, each taking an owner."""

    name = "gitci"

    def __init__(self):
        self.calls: List[tuple] = []

    async def list_tools(self) -> List[ToolSpec]:
        text, owner = {"type": "string"}, {"owner": {"type": "string"}}
        return [
            _spec("sandbox_clone", {"repo_url": text, "branch": text, **owner}, ["repo_url"], True),
            _spec("list_saved_work", {"repo_url": text, **owner}, [], False),
            _spec("delete_saved_work", {"repo_url": text, "branch": text, **owner}, ["repo_url", "branch"], True),
        ]

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
    catalog = {spec.name: spec for spec in await ToolRegistry([source]).catalog()}
    assert set(catalog["gitci.sandbox_clone"].input_schema["properties"]) == {"repo_url", "branch"}
    assert set(catalog["gitci.list_saved_work"].input_schema["properties"]) == {"repo_url"}
    assert set(catalog["gitci.delete_saved_work"].input_schema["properties"]) == {"repo_url", "branch"}

    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, workspace_owner="alice")
    llm.script += [_clone(owner="bob"), _final()]
    mission = await planner.start("fix the bug")
    assert mission.steps[0].arguments == {"repo_url": REPO}  # the approval card shows nothing of "bob"

    done = await planner.resolve_approval(mission.id, True)
    assert done.status == MissionStatus.COMPLETED
    assert source.calls == [("sandbox_clone", {"repo_url": REPO, "owner": "alice"})]


@pytest.mark.asyncio
async def test_the_branch_to_resume_is_the_model_s_to_pass(llm):
    source = CloneSource()
    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, workspace_owner="alice")
    llm.script += [_clone(branch="fix-a"), _final()]
    await planner.resolve_approval((await planner.start("continue fix-a")).id, True)
    assert source.calls == [("sandbox_clone", {"repo_url": REPO, "branch": "fix-a", "owner": "alice"})]


def _call(tool: str, **arguments) -> str:
    return json.dumps({"thought": "Saved work.", "tool": f"gitci.{tool}", "arguments": arguments})


@pytest.mark.asyncio
async def test_listing_and_deleting_saved_work_act_on_the_signed_in_user_only(llm):
    source = CloneSource()
    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, workspace_owner="alice")
    llm.script += [_call("list_saved_work", owner="bob"), _call("delete_saved_work", repo_url=REPO, branch="fix-a",
                                                                owner="bob"), _final()]
    mission = await planner.start("free some space")  # listing is read-only; deleting waits for approval
    assert mission.status == MissionStatus.AWAITING_APPROVAL
    assert mission.steps[-1].arguments == {"repo_url": REPO, "branch": "fix-a"}
    await planner.resolve_approval(mission.id, True)
    assert source.calls == [("list_saved_work", {"owner": "alice"}),
                            ("delete_saved_work", {"repo_url": REPO, "branch": "fix-a", "owner": "alice"})]


@pytest.mark.asyncio
async def test_without_a_signed_in_owner_there_is_no_saved_work_to_offer(llm):
    planner = MissionPlanner(ToolRegistry([CloneSource()]), store=MissionStore(), max_steps=2)
    llm.script += [_final()]
    await planner.start("what have I saved?")
    assert "list_saved_work" not in llm.prompts[0] and "delete_saved_work" not in llm.prompts[0]
    assert "gitci.sandbox_clone" in llm.prompts[0]


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
    assert agent_tools.is_workspace_tool("any.sandbox_clone") and agent_tools.is_workspace_tool("x.delete_saved_work")
    assert not agent_tools.is_workspace_tool("gitci.show_diff")


def test_the_rules_say_how_to_continue_and_free_saved_work():
    assert '"resumed"' in PLANNER_SYSTEM_PROMPT and "with branch set to that branch" in PLANNER_SYSTEM_PROMPT
    assert "never reuse the name of a saved branch" in PLANNER_SYSTEM_PROMPT
    assert "delete only those they name" in PLANNER_SYSTEM_PROMPT and "save_warning" in PLANNER_SYSTEM_PROMPT
    assert "call sandbox_clone again" in PLANNER_SYSTEM_PROMPT and "fresh" not in PLANNER_SYSTEM_PROMPT


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
