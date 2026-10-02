"""Per-user Telegram linking: the link flow, the webhook, and aiming reports at the owner's own chat."""

import json
from typing import Any, Dict, List

import httpx
import pytest
from sqlalchemy import select

from app.agent import tools as agent_tools
from app.agent.planner import MissionPlanner
from app.agent.store import MissionStore
from app.agent.tools import ToolRegistry, ToolSpec
from app.api.v1 import agent as agent_api
from app.config import settings
from app.models.telegram import TelegramLink, TelegramLinkCode
from app.schemas.agent import MissionStatus, StepStatus
from app.security import auth
from app.security.rate_limiter import limiter
from app.telegram_link import bot
from app.triage.llm_engine import LLMTriageEngine

SECRET = "hook-secret_123"
HEADER = "X-Telegram-Bot-Api-Secret-Token"
ALICE_CHAT, BOB_CHAT = 111222333, 444555666


@pytest.fixture(autouse=True)
def telegram_setup(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", "x" * 40)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "*")
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", False)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "dmc_test_bot")
    monkeypatch.setattr(settings, "TELEGRAM_LINK_TTL_SECONDS", 600)
    limiter.reset()


@pytest.fixture
def replies(monkeypatch) -> List[tuple]:
    """What the bot would say, captured instead of sent."""
    said: List[tuple] = []

    async def capture(chat_id: str, text: str) -> bool:
        said.append((chat_id, text))
        return True

    monkeypatch.setattr(bot, "send_text", capture)
    return said


def _bearer(login: str) -> Dict[str, str]:
    return {"Authorization": "Bearer " + auth.issue_token(auth.KIND_SESSION, 600, sub=login)}


def _update(text: str, chat_id: int = ALICE_CHAT, chat_type: str = "private") -> Dict[str, Any]:
    return {"update_id": 1, "message": {"text": text, "chat": {"id": chat_id, "type": chat_type}}}


async def _post_update(client: httpx.AsyncClient, update: Dict[str, Any], secret: str = SECRET) -> httpx.Response:
    return await client.post("/api/v1/telegram/webhook", json=update, headers={HEADER: secret})


async def _start_link(client: httpx.AsyncClient, login: str) -> str:
    response = await client.post("/api/v1/telegram/link", headers=_bearer(login))
    assert response.status_code == 200, response.text
    url = response.json()["url"]
    assert url.startswith("https://t.me/dmc_test_bot?start=")
    return url.split("start=", 1)[1]


async def _link(client: httpx.AsyncClient, login: str, chat_id: int) -> None:
    code = await _start_link(client, login)
    assert (await _post_update(client, _update(f"/start {code}", chat_id))).status_code == 200


# --- the link flow -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linking_needs_a_signed_in_user(client: httpx.AsyncClient):
    assert (await client.get("/api/v1/telegram/status")).status_code == 401
    assert (await client.post("/api/v1/telegram/link")).status_code == 401
    assert (await client.delete("/api/v1/telegram/link")).status_code == 401


@pytest.mark.asyncio
async def test_linking_says_so_when_the_server_is_not_set_up(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    status = await client.get("/api/v1/telegram/status", headers=_bearer("alice"))
    assert status.json() == {"configured": False, "linked": False, "linked_at": None}
    assert (await client.post("/api/v1/telegram/link", headers=_bearer("alice"))).status_code == 503


@pytest.mark.asyncio
async def test_pressing_start_links_the_chat_to_the_account(client: httpx.AsyncClient, db_session, replies):
    code = await _start_link(client, "Alice")
    # Only a hash of the code is kept.
    stored = (await db_session.execute(select(TelegramLinkCode.code_hash))).scalars().all()
    assert len(stored) == 1 and code not in stored

    assert (await _post_update(client, _update(f"/start {code}"))).json() == {"ok": True}

    status = (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()
    assert status["configured"] is True and status["linked"] is True and status["linked_at"]
    link = (await db_session.execute(select(TelegramLink))).scalar_one()
    assert (link.login, link.chat_id) == ("alice", str(ALICE_CHAT))
    # The bot names the account, so someone who pressed Start for another person's link can see it.
    assert replies[-1][0] == str(ALICE_CHAT)
    assert "alice" in replies[-1][1] and "/stop" in replies[-1][1]


@pytest.mark.asyncio
async def test_a_code_works_once(client: httpx.AsyncClient, replies):
    code = await _start_link(client, "alice")
    await _post_update(client, _update(f"/start {code}", ALICE_CHAT))
    await _post_update(client, _update(f"/start {code}", BOB_CHAT))  # someone else, with the used code

    assert "expired or was already used" in replies[-1][1]
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("bob"))).json()["linked"] is False


@pytest.mark.asyncio
async def test_an_expired_code_does_not_link(client: httpx.AsyncClient, monkeypatch, replies):
    monkeypatch.setattr(settings, "TELEGRAM_LINK_TTL_SECONDS", -1)
    code = await _start_link(client, "alice")
    await _post_update(client, _update(f"/start {code}"))

    assert "expired or was already used" in replies[-1][1]
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["/start", "/start nope", "/start " + "a" * 200, "/start ../../etc", "hello"])
async def test_garbage_never_links_anything(client: httpx.AsyncClient, db_session, replies, text):
    assert (await _post_update(client, _update(text))).status_code == 200
    assert (await db_session.execute(select(TelegramLink))).first() is None


@pytest.mark.asyncio
async def test_a_new_code_replaces_the_old_one(client: httpx.AsyncClient, replies):
    first = await _start_link(client, "alice")
    second = await _start_link(client, "alice")
    await _post_update(client, _update(f"/start {first}"))
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is False
    await _post_update(client, _update(f"/start {second}"))
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is True


@pytest.mark.asyncio
async def test_only_private_chats_can_be_linked(client: httpx.AsyncClient, replies):
    code = await _start_link(client, "alice")
    await _post_update(client, _update(f"/start {code}", -100123456789, chat_type="supergroup"))
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is False
    assert replies == []


@pytest.mark.asyncio
async def test_relinking_replaces_and_a_chat_has_one_owner(client: httpx.AsyncClient, db_session, replies):
    await _link(client, "alice", ALICE_CHAT)
    await _link(client, "alice", BOB_CHAT)  # alice moves to another chat
    assert (await db_session.execute(select(TelegramLink.chat_id))).scalars().all() == [str(BOB_CHAT)]

    await _link(client, "carol", BOB_CHAT)  # the person in that chat links it to a different account
    rows = (await db_session.execute(select(TelegramLink))).scalars().all()
    assert [(r.login, r.chat_id) for r in rows] == [("carol", str(BOB_CHAT))]


@pytest.mark.asyncio
async def test_stop_unlinks_the_chat(client: httpx.AsyncClient, replies):
    await _link(client, "alice", ALICE_CHAT)
    await _post_update(client, _update("/stop@dmc_test_bot"))

    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is False
    assert "Unlinked" in replies[-1][1]
    await _post_update(client, _update("/stop"))
    assert "not linked" in replies[-1][1]


@pytest.mark.asyncio
async def test_unlink_endpoint(client: httpx.AsyncClient, replies):
    await _link(client, "alice", ALICE_CHAT)
    await _link(client, "bob", BOB_CHAT)

    assert (await client.delete("/api/v1/telegram/link", headers=_bearer("alice"))).json()["was_linked"] is True
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("alice"))).json()["linked"] is False
    assert (await client.get("/api/v1/telegram/status", headers=_bearer("bob"))).json()["linked"] is True
    assert (await client.delete("/api/v1/telegram/link", headers=_bearer("alice"))).json()["was_linked"] is False


# --- the webhook only believes Telegram --------------------------------------------------------


@pytest.mark.asyncio
async def test_the_webhook_refuses_calls_without_the_secret(client: httpx.AsyncClient, db_session, replies):
    code = await _start_link(client, "alice")
    update = _update(f"/start {code}")

    assert (await client.post("/api/v1/telegram/webhook", json=update)).status_code == 403
    assert (await _post_update(client, update, secret="wrong")).status_code == 403
    assert (await _post_update(client, update, secret=SECRET[:-1])).status_code == 403
    assert (await db_session.execute(select(TelegramLink))).first() is None
    assert replies == []


@pytest.mark.asyncio
async def test_the_webhook_is_closed_when_no_secret_is_configured(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    assert (await client.post("/api/v1/telegram/webhook", json=_update("/stop"))).status_code == 403
    assert (await _post_update(client, _update("/stop"), secret="")).status_code == 403


@pytest.mark.asyncio
async def test_a_malformed_update_is_acknowledged_not_retried(client: httpx.AsyncClient, replies):
    for body in ({"message": "text"}, {"message": {"chat": "x"}}, {"edited_message": {}}, [1, 2]):
        response = await client.post("/api/v1/telegram/webhook", json=body, headers={HEADER: SECRET})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_registering_the_webhook_sends_the_secret_and_never_logs_the_token(monkeypatch, caplog):
    seen: List[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": True})

    real = httpx.AsyncClient
    monkeypatch.setattr(bot.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_URL", "https://api.example/api/v1/telegram/webhook")

    assert await bot.register_webhook() is True
    body = json.loads(seen[0].content)
    assert seen[0].url.path.endswith("/setWebhook")
    assert body["secret_token"] == SECRET and body["url"] == "https://api.example/api/v1/telegram/webhook"
    assert body["allowed_updates"] == ["message"]

    monkeypatch.setattr(bot.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(
        lambda r: httpx.Response(401, json={"ok": False})), **kw))
    assert await bot.register_webhook() is False
    assert "test-token" not in caplog.text


@pytest.mark.asyncio
async def test_registering_is_skipped_unless_everything_is_set(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_URL", None)
    assert await bot.register_webhook() is False
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_URL", "https://api.example/hook")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    assert await bot.register_webhook() is False


# --- reports go to the owner's own chat --------------------------------------------------------


class ReportSource:
    """A tool source shaped like Git/CI: one approval-gated send_report that takes a chat_id."""

    name = "gitci"

    def __init__(self):
        self.calls: List[tuple] = []

    async def list_tools(self) -> List[ToolSpec]:
        return [ToolSpec(
            name="gitci.send_report",
            description="Send a report.",
            input_schema={
                "type": "object",
                "properties": {"title": {"type": "string"}, "summary": {"type": "string"}, "chat_id": {"type": "string"}},
                "required": ["title", "summary"],
            },
            requires_approval=True,
        )]

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return {"sent": True}


def _reply_tool(**arguments) -> str:
    return json.dumps({"thought": "Report.", "tool": "gitci.send_report", "arguments": arguments})


def _reply_final(speech: str = "Done.") -> str:
    return json.dumps({"thought": "Wrap up.", "final": {"speech": speech, "display": ""}})


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


@pytest.fixture
def report_source(monkeypatch):
    source = ReportSource()
    monkeypatch.setattr(agent_api, "configured_registry", lambda: ToolRegistry([source]))
    return source


def _planner(source, chat_id=None) -> MissionPlanner:
    return MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, report_chat_id=chat_id)


@pytest.mark.asyncio
async def test_the_model_cannot_see_or_set_the_recipient(llm):
    source = ReportSource()
    catalog = await ToolRegistry([source]).catalog()
    assert "chat_id" not in catalog[0].input_schema["properties"]

    llm.script += [_reply_tool(title="Fixed", summary="ok", chat_id="999999999")]
    mission = await _planner(source, chat_id=str(ALICE_CHAT)).start("report it")

    # Nothing the model said is shown on the approval card, and nothing it said is used.
    assert mission.steps[0].arguments == {"title": "Fixed", "summary": "ok"}
    assert "chat_id" not in llm.prompts[0]


@pytest.mark.asyncio
async def test_approving_aims_the_report_at_the_linked_chat(llm):
    source = ReportSource()
    planner = _planner(source, chat_id=str(ALICE_CHAT))
    llm.script += [_reply_tool(title="Fixed", summary="ok", chat_id="999999999"), _reply_final("Sent.")]

    mission = await planner.start("report it")
    assert mission.status == MissionStatus.AWAITING_APPROVAL
    done = await planner.resolve_approval(mission.id, True)

    assert done.status == MissionStatus.COMPLETED
    assert source.calls == [("send_report", {"title": "Fixed", "summary": "ok", "chat_id": str(ALICE_CHAT)})]
    assert "chat_id" not in json.dumps(done.model_dump(mode="json"))  # the chat id is not stored in the mission


@pytest.mark.asyncio
async def test_without_a_link_the_report_tool_is_not_offered(llm):
    source = ReportSource()
    llm.script += [_reply_tool(title="Fixed", summary="ok")]
    mission = await _planner(source, chat_id=None).start("fix it and tell me")

    # The only tool is gone, so there is nothing to run, and the model was never asked.
    assert mission.status == MissionStatus.FAILED
    assert source.calls == [] and llm.prompts == []


@pytest.mark.asyncio
async def test_an_unlinked_user_is_told_to_link_telegram(llm):
    class Both(ReportSource):
        async def list_tools(self):
            return await super().list_tools() + [ToolSpec("gitci.show_diff", "Diff.", {"type": "object"}, False)]

    source = Both()
    llm.script += [_reply_final("Done. Link Telegram to get a report.")]
    await _planner(source, chat_id=None).start("fix it and send me a report")

    prompt = llm.prompts[0]
    tools_section = prompt.split("## Tools", 1)[1].split("## Current request", 1)[0]
    assert "send_report" not in tools_section and "gitci.show_diff" in tools_section
    assert 'press "Link Telegram"' in prompt

    llm.prompts.clear()
    llm.script += [_reply_final()]
    await _planner(source, chat_id=str(ALICE_CHAT)).start("fix it and send me a report")
    assert "send_report" in llm.prompts[0] and "Link Telegram" not in llm.prompts[0]


@pytest.mark.asyncio
async def test_unlinking_before_approval_stops_the_report(llm):
    source = ReportSource()
    store = MissionStore()
    llm.script += [_reply_tool(title="Fixed", summary="ok"), _reply_final("Could not report.")]
    mission = await MissionPlanner(ToolRegistry([source]), store=store, report_chat_id=str(ALICE_CHAT)).start("report")

    done = await MissionPlanner(ToolRegistry([source]), store=store, report_chat_id=None).resolve_approval(mission.id, True)

    assert source.calls == []  # nothing was sent anywhere
    assert done.steps[0].status == StepStatus.FAILED
    assert "not linked" in done.steps[0].error


@pytest.mark.asyncio
async def test_the_registry_drops_a_recipient_the_caller_slipped_in():
    source = ReportSource()
    registry = ToolRegistry([source])

    await registry.call("gitci.send_report", {"title": "t", "summary": "s", "chat_id": "666666666"})
    await registry.call("gitci.send_report", {"title": "t", "summary": "s"}, server_set={"chat_id": "123456789", "other": "x"})

    assert source.calls[0][1] == {"title": "t", "summary": "s"}
    assert source.calls[1][1] == {"title": "t", "summary": "s", "chat_id": "123456789"}
    assert agent_tools.is_report_tool("anything.send_report") and not agent_tools.is_report_tool("gitci.show_diff")


@pytest.mark.asyncio
async def test_each_user_s_report_goes_to_their_own_chat(client: httpx.AsyncClient, report_source, llm, replies):
    await _link(client, "alice", ALICE_CHAT)
    await _link(client, "bob", BOB_CHAT)
    agent_api.limiter.reset()

    # Alice's model is talked into naming Bob's chat; the report still goes to Alice's.
    llm.script += [_reply_tool(title="Fixed", summary="ok", chat_id=str(BOB_CHAT))]
    created = (await client.post("/api/v1/agent/missions", json={"utterance": "report"}, headers=_bearer("alice"))).json()
    assert created["status"] == "awaiting_approval"

    llm.script += [_reply_final("Sent.")]
    headers = {**_bearer("alice"), "X-Session-Token": created["session_token"]}
    approved = await client.post(f"/api/v1/agent/missions/{created['id']}/approval", json={"approved": True}, headers=headers)
    assert approved.json()["status"] == "completed"
    assert report_source.calls == [("send_report", {"title": "Fixed", "summary": "ok", "chat_id": str(ALICE_CHAT)})]

    # Bob cannot approve Alice's mission, so he cannot make it run against his own link either.
    llm.script += [_reply_tool(title="Again", summary="ok")]
    again = (await client.post("/api/v1/agent/missions", json={"utterance": "report"}, headers=_bearer("alice"))).json()
    stolen = await client.post(
        f"/api/v1/agent/missions/{again['id']}/approval", json={"approved": True},
        headers={**_bearer("bob"), "X-Session-Token": again["session_token"]},
    )
    assert stolen.status_code == 403
    assert len(report_source.calls) == 1


@pytest.mark.asyncio
async def test_the_tools_endpoint_hides_the_recipient_argument(client: httpx.AsyncClient, report_source):
    tools = (await client.get("/api/v1/agent/tools")).json()["tools"]
    schema = tools[0]["input_schema"]
    assert "chat_id" not in schema["properties"]
