"""Per-user email linking: the confirm-by-code flow, its limits, and aiming send_email at the owner's address."""

import json
import logging
from typing import Any, Dict, List

import aiosmtplib
import httpx
import pytest
from sqlalchemy import select

from app.agent import tools as agent_tools
from app.agent.planner import MissionPlanner
from app.agent.store import MissionStore
from app.agent.tools import ToolRegistry, ToolSpec
from app.api.v1 import agent as agent_api
from app.config import settings
from app.email_link import mailer, service
from app.models.email_link import EmailLink, EmailLinkCode
from app.schemas.agent import MissionStatus, StepStatus
from app.security import auth
from app.security.rate_limiter import limiter
from app.smtp import tls_options
from app.triage.llm_engine import LLMTriageEngine

ALICE_MAIL, BOB_MAIL = "alice@example.com", "bob@example.org"


@pytest.fixture(autouse=True)
def email_setup(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", "x" * 40)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "*")
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", False)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(settings, "RESEND_API_KEY", None)
    monkeypatch.setattr(settings, "EMAIL_LINK_TTL_SECONDS", 600)
    monkeypatch.setattr(settings, "EMAIL_LINK_MAX_ATTEMPTS", 5)
    monkeypatch.setattr(settings, "EMAIL_LINK_MAX_CODES_PER_HOUR", 3)
    limiter.reset()


@pytest.fixture
def mails(monkeypatch) -> List[Dict[str, Any]]:
    """The code emails that would have been sent, captured instead of sent."""
    sent: List[Dict[str, Any]] = []

    async def capture(address: str, login: str, code: str, minutes: int) -> bool:
        sent.append({"address": address, "login": login, "code": code, "minutes": minutes})
        return True

    monkeypatch.setattr(mailer, "send_code", capture)
    return sent


def _bearer(login: str) -> Dict[str, str]:
    return {"Authorization": "Bearer " + auth.issue_token(auth.KIND_SESSION, 600, sub=login)}


async def _ask(client: httpx.AsyncClient, login: str, address: str) -> httpx.Response:
    return await client.post("/api/v1/email/link", json={"address": address}, headers=_bearer(login))


async def _confirm(client: httpx.AsyncClient, login: str, code: str) -> httpx.Response:
    return await client.post("/api/v1/email/confirm", json={"code": code}, headers=_bearer(login))


async def _link(client: httpx.AsyncClient, mails, login: str, address: str) -> None:
    assert (await _ask(client, login, address)).status_code == 200
    assert (await _confirm(client, login, mails[-1]["code"])).status_code == 200


# --- the link flow -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linking_needs_a_signed_in_user(client: httpx.AsyncClient):
    assert (await client.get("/api/v1/email/status")).status_code == 401
    assert (await client.post("/api/v1/email/link", json={"address": ALICE_MAIL})).status_code == 401
    assert (await client.post("/api/v1/email/confirm", json={"code": "123456"})).status_code == 401
    assert (await client.delete("/api/v1/email/link")).status_code == 401


@pytest.mark.asyncio
async def test_linking_says_so_when_the_server_cannot_send_mail(client: httpx.AsyncClient, monkeypatch, mails):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    status = await client.get("/api/v1/email/status", headers=_bearer("alice"))
    assert status.json() == {"configured": False, "linked": False, "address": None, "linked_at": None}
    assert (await _ask(client, "alice", ALICE_MAIL)).status_code == 503
    assert mails == []


@pytest.mark.asyncio
@pytest.mark.parametrize("address", [
    "nobody", "a@b", "@example.com", "a b@example.com", "Alice <a@example.com>",
    "a@example.com, b@example.com", "a@example.com\nBcc: x@example.org", "", "x" * 300 + "@example.com",
])
async def test_only_one_plain_address_is_accepted(client: httpx.AsyncClient, mails, address):
    response = await _ask(client, "alice", address)
    assert response.status_code == 422
    assert mails == []


@pytest.mark.asyncio
async def test_the_code_goes_to_the_typed_address_and_confirming_links_it(client: httpx.AsyncClient, db_session, mails):
    response = await _ask(client, "Alice", " Alice@Example.COM ")
    assert response.status_code == 200 and response.json() == {"expires_in": 600}
    assert mails[0]["address"] == ALICE_MAIL and mails[0]["login"] == "Alice" and mails[0]["minutes"] == 10
    code = mails[0]["code"]
    assert len(code) == 6 and code.isdigit()

    # Only a hash is kept, and nothing is linked until the code comes back.
    assert (await db_session.execute(select(EmailLink))).first() is None
    assert (await db_session.execute(select(EmailLinkCode.code_hash))).scalar_one() != code

    confirmed = await _confirm(client, "alice", code)
    assert confirmed.status_code == 200
    assert confirmed.json()["linked"] is True and confirmed.json()["address"] == "a***e@example.com"
    assert ALICE_MAIL not in confirmed.text  # the address is shown back masked

    status = (await client.get("/api/v1/email/status", headers=_bearer("alice"))).json()
    assert status["linked"] is True and status["address"] == "a***e@example.com"
    assert (await db_session.execute(select(EmailLink.address))).scalar_one() == ALICE_MAIL
    assert (await db_session.execute(select(EmailLinkCode))).first() is None  # the code was spent


@pytest.mark.asyncio
async def test_a_code_works_once(client: httpx.AsyncClient, mails):
    await _ask(client, "alice", ALICE_MAIL)
    code = mails[-1]["code"]
    assert (await _confirm(client, "alice", code)).status_code == 200
    assert (await _confirm(client, "alice", code)).status_code == 400


@pytest.mark.asyncio
async def test_a_wrong_code_fails_and_too_many_guesses_spend_the_code(client: httpx.AsyncClient, db_session, mails):
    await _ask(client, "alice", ALICE_MAIL)
    real = mails[-1]["code"]
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(5):
        limiter.reset()
        assert (await _confirm(client, "alice", wrong)).status_code == 400
    limiter.reset()
    # Out of attempts: even the right code is refused now.
    assert (await _confirm(client, "alice", real)).status_code == 400
    assert (await db_session.execute(select(EmailLink))).first() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["", "12345", "1234567", "abcdef", "12 456", "١٢٣٤٥٦"])
async def test_garbage_never_links_anything(client: httpx.AsyncClient, db_session, mails, code):
    await _ask(client, "alice", ALICE_MAIL)
    assert (await _confirm(client, "alice", code)).status_code == 400
    assert (await db_session.execute(select(EmailLink))).first() is None


@pytest.mark.asyncio
async def test_an_expired_code_does_not_link(client: httpx.AsyncClient, monkeypatch, mails):
    monkeypatch.setattr(settings, "EMAIL_LINK_TTL_SECONDS", -1)
    await _ask(client, "alice", ALICE_MAIL)
    assert (await _confirm(client, "alice", mails[-1]["code"])).status_code == 400


@pytest.mark.asyncio
async def test_a_code_only_works_for_the_login_that_asked(client: httpx.AsyncClient, db_session, mails):
    await _ask(client, "alice", ALICE_MAIL)
    limiter.reset()
    # Bob somehow gets Alice's code: it does nothing for him.
    assert (await _confirm(client, "bob", mails[-1]["code"])).status_code == 400
    assert (await db_session.execute(select(EmailLink))).first() is None


@pytest.mark.asyncio
async def test_only_the_newest_code_works(client: httpx.AsyncClient, mails):
    await _ask(client, "alice", ALICE_MAIL)
    first = mails[-1]["code"]
    limiter.reset()
    await _ask(client, "alice", "other@example.com")
    second = mails[-1]
    limiter.reset()
    if first != second["code"]:
        assert (await _confirm(client, "alice", first)).status_code == 400
        limiter.reset()
    assert (await _confirm(client, "alice", second["code"])).status_code == 200
    link = (await client.get("/api/v1/email/status", headers=_bearer("alice"))).json()
    assert link["address"] == "o***r@example.com"


@pytest.mark.asyncio
async def test_codes_are_capped_per_address(client: httpx.AsyncClient, mails):
    # Different people typing one victim's address cannot make the platform mail them without end.
    for login in ("u1", "u2", "u3"):
        assert (await _ask(client, login, ALICE_MAIL)).status_code == 200
    limiter.reset()
    assert (await _ask(client, "u4", ALICE_MAIL)).status_code == 429
    assert len(mails) == 3


@pytest.mark.asyncio
async def test_codes_are_capped_per_login(client: httpx.AsyncClient, mails):
    for i in range(3):
        assert (await _ask(client, "spammer", f"victim{i}@example.com")).status_code == 200
    limiter.reset()
    assert (await _ask(client, "spammer", "victim9@example.com")).status_code == 429
    assert len(mails) == 3


@pytest.mark.asyncio
async def test_a_mail_that_cannot_be_sent_is_reported(client: httpx.AsyncClient, monkeypatch):
    async def fail(*args, **kwargs) -> bool:
        return False

    monkeypatch.setattr(mailer, "send_code", fail)
    assert (await _ask(client, "alice", ALICE_MAIL)).status_code == 503


@pytest.mark.asyncio
async def test_a_mail_that_cannot_be_sent_does_not_use_up_the_caps(client: httpx.AsyncClient, monkeypatch, db_session):
    # A blocked mail server must not lock the user out for an hour: each failed try is forgotten.
    async def fail(*args, **kwargs) -> bool:
        return False

    async def ok(*args, **kwargs) -> bool:
        return True

    monkeypatch.setattr(mailer, "send_code", fail)
    for _ in range(4):
        assert (await _ask(client, "alice", ALICE_MAIL)).status_code == 503
        limiter.reset()
    assert (await db_session.execute(select(EmailLinkCode))).first() is None
    monkeypatch.setattr(mailer, "send_code", ok)
    assert (await _ask(client, "alice", ALICE_MAIL)).status_code == 200


@pytest.mark.parametrize("port, implicit", [(465, True), (2465, True), (587, False), (2525, False), (2587, False)])
def test_the_tls_mode_follows_the_port(port, implicit):
    # Only 465 and 2465 start encrypted; every other port must upgrade before the password is sent.
    assert tls_options(port) == {"use_tls": implicit, "start_tls": not implicit}


@pytest.mark.asyncio
async def test_the_confirmation_mail_uses_an_alternate_port_with_starttls(monkeypatch):
    seen: Dict[str, Any] = {}

    async def fake_send(message, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(settings, "SMTP_PORT", 2525)
    monkeypatch.setattr(mailer.aiosmtplib, "send", fake_send)
    assert await mailer.send_code(ALICE_MAIL, "alice", "123456", 10) is True
    assert seen["port"] == 2525 and seen["start_tls"] is True and seen["use_tls"] is False


@pytest.mark.asyncio
async def test_a_blocked_port_is_named_in_the_log(monkeypatch, caplog):
    async def dropped(message, **kwargs):
        raise aiosmtplib.SMTPConnectTimeoutError("Timed out connecting to smtp.example.com on port 587")

    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(mailer.aiosmtplib, "send", dropped)
    with caplog.at_level(logging.WARNING, logger="gitscout.email_link"):
        assert await mailer.send_code(ALICE_MAIL, "alice", "123456", 10) is False
    assert "smtp.example.com:587" in caplog.text
    assert "blocked on Render's free tier" in caplog.text


@pytest.mark.asyncio
async def test_relinking_replaces_the_address(client: httpx.AsyncClient, db_session, mails):
    await _link(client, mails, "alice", ALICE_MAIL)
    limiter.reset()
    await _link(client, mails, "alice", "new@example.net")
    assert (await db_session.execute(select(EmailLink.address))).scalars().all() == ["new@example.net"]


@pytest.mark.asyncio
async def test_unlink_endpoint(client: httpx.AsyncClient, db_session, mails):
    await _link(client, mails, "alice", ALICE_MAIL)
    limiter.reset()
    assert (await client.delete("/api/v1/email/link", headers=_bearer("alice"))).json() == {"status": "success", "was_linked": True}
    assert (await client.delete("/api/v1/email/link", headers=_bearer("alice"))).json()["was_linked"] is False
    assert (await db_session.execute(select(EmailLink))).first() is None


@pytest.mark.asyncio
async def test_the_confirmation_mail_names_who_asked_and_says_to_ignore_it(monkeypatch):
    seen: List[Any] = []

    async def fake_send(message, **kwargs):
        seen.append(message)

    monkeypatch.setattr(mailer.aiosmtplib, "send", fake_send)
    assert await mailer.send_code(ALICE_MAIL, "mallory", "123456", 10) is True
    body = seen[0].get_content()
    assert seen[0]["To"] == ALICE_MAIL and "123456" in body
    assert "mallory" in body and "ignore this email" in body


def test_masking_hides_most_of_the_address():
    assert service.mask("alice@example.com") == "a***e@example.com"
    assert service.mask("ab@example.com") == "ab@example.com"


# --- emails go to the owner's own confirmed address -------------------------------------------


class MailSource:
    """A tool source shaped like the Email Orchestrator: an inbox reader and an approval-gated send_email."""

    name = "email"

    def __init__(self):
        self.calls: List[tuple] = []

    async def list_tools(self) -> List[ToolSpec]:
        return [
            ToolSpec("email.inbox_summary", "Summarise the inbox.", {"type": "object"}, False),
            ToolSpec(
                name="email.send_email",
                description="Send an email.",
                input_schema={
                    "type": "object",
                    "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
                    "required": ["to", "subject", "body"],
                },
                requires_approval=True,
            ),
        ]

    async def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        return {"sent": True}


def _reply_tool(**arguments) -> str:
    return json.dumps({"thought": "Email.", "tool": "email.send_email", "arguments": arguments})


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
def mail_source(monkeypatch):
    source = MailSource()
    monkeypatch.setattr(agent_api, "configured_registry", lambda: ToolRegistry([source]))
    return source


def _planner(source, email_to=None) -> MissionPlanner:
    return MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=4, email_to=email_to)


def _tools_section(prompt: str) -> str:
    return prompt.split("## Tools", 1)[1].split("## Current request", 1)[0]


@pytest.mark.asyncio
async def test_the_model_cannot_see_or_set_the_recipient(llm):
    source = MailSource()
    catalog = {spec.name: spec for spec in await ToolRegistry([source]).catalog()}
    assert "to" not in catalog["email.send_email"].input_schema["properties"]
    assert "to" not in catalog["email.send_email"].input_schema["required"]

    llm.script += [_reply_tool(subject="Fixed", body="ok", to="attacker@evil.example")]
    mission = await _planner(source, email_to=ALICE_MAIL).start("email me")

    # Nothing the model said about the recipient is shown on the approval card, or used.
    assert mission.steps[0].arguments == {"subject": "Fixed", "body": "ok"}
    assert "attacker" not in json.dumps(mission.model_dump(mode="json"))


@pytest.mark.asyncio
async def test_approving_aims_the_email_at_the_confirmed_address(llm):
    source = MailSource()
    planner = _planner(source, email_to=ALICE_MAIL)
    llm.script += [_reply_tool(subject="Fixed", body="ok", to="attacker@evil.example"), _reply_final("Sent.")]

    mission = await planner.start("email me")
    assert mission.status == MissionStatus.AWAITING_APPROVAL
    done = await planner.resolve_approval(mission.id, True)

    assert done.status == MissionStatus.COMPLETED
    assert source.calls == [("send_email", {"subject": "Fixed", "body": "ok", "to": ALICE_MAIL})]
    assert ALICE_MAIL not in json.dumps(done.model_dump(mode="json"))  # the address is not stored in the mission


@pytest.mark.asyncio
async def test_declining_sends_nothing(llm):
    source = MailSource()
    planner = _planner(source, email_to=ALICE_MAIL)
    llm.script += [_reply_tool(subject="Fixed", body="ok"), _reply_final("Okay, not sent.")]
    mission = await planner.start("email me")
    await planner.resolve_approval(mission.id, False)
    assert source.calls == []


@pytest.mark.asyncio
async def test_without_a_confirmed_address_the_send_tool_is_not_offered_and_the_user_is_told(llm):
    source = MailSource()
    llm.script += [_reply_final("Done. Link an email address to get one.")]
    await _planner(source, email_to=None).start("summarise my inbox and email me")

    prompt = llm.prompts[0]
    assert "send_email" not in _tools_section(prompt) and "email.inbox_summary" in _tools_section(prompt)
    assert "has not confirmed an email address" in prompt

    llm.prompts.clear()
    llm.script += [_reply_final()]
    await _planner(source, email_to=ALICE_MAIL).start("summarise my inbox and email me")
    assert "send_email" in _tools_section(llm.prompts[0])
    assert "has not confirmed" not in llm.prompts[0] and "never ask for or pass an address" in llm.prompts[0]


@pytest.mark.asyncio
async def test_unlinking_before_approval_stops_the_email(llm):
    source = MailSource()
    store = MissionStore()
    llm.script += [_reply_tool(subject="Fixed", body="ok"), _reply_final("Could not email.")]
    mission = await MissionPlanner(ToolRegistry([source]), store=store, email_to=ALICE_MAIL).start("email me")

    done = await MissionPlanner(ToolRegistry([source]), store=store, email_to=None).resolve_approval(mission.id, True)

    assert source.calls == []  # nothing was sent anywhere
    assert done.steps[0].status == StepStatus.FAILED
    assert "No email address is confirmed" in done.steps[0].error


@pytest.mark.asyncio
async def test_the_registry_drops_a_recipient_the_caller_slipped_in():
    source = MailSource()
    registry = ToolRegistry([source])

    await registry.call("email.send_email", {"subject": "s", "body": "b", "to": "x@evil.example"})
    await registry.call("email.send_email", {"subject": "s", "body": "b"}, server_set={"to": ALICE_MAIL, "other": "x"})

    assert source.calls[0][1] == {"subject": "s", "body": "b"}
    assert source.calls[1][1] == {"subject": "s", "body": "b", "to": ALICE_MAIL}
    assert agent_tools.is_email_tool("anything.send_email") and not agent_tools.is_email_tool("email.inbox_summary")


@pytest.mark.asyncio
async def test_each_user_s_email_goes_to_their_own_address(client: httpx.AsyncClient, mail_source, llm, mails):
    await _link(client, mails, "alice", ALICE_MAIL)
    limiter.reset()
    await _link(client, mails, "bob", BOB_MAIL)
    limiter.reset()

    # Alice's model is talked into naming Bob's address; the email still goes to Alice's.
    llm.script += [_reply_tool(subject="Summary", body="ok", to=BOB_MAIL)]
    created = (await client.post("/api/v1/agent/missions", json={"utterance": "email me"}, headers=_bearer("alice"))).json()
    assert created["status"] == "awaiting_approval"

    # Bob cannot approve Alice's mission, so he cannot make it run against his own address either.
    headers_bob = {**_bearer("bob"), "X-Session-Token": created["session_token"]}
    denied = await client.post(f"/api/v1/agent/missions/{created['id']}/approval", json={"approved": True}, headers=headers_bob)
    assert denied.status_code in (403, 404)
    assert mail_source.calls == []

    llm.script += [_reply_final("Sent.")]
    headers = {**_bearer("alice"), "X-Session-Token": created["session_token"]}
    approved = await client.post(f"/api/v1/agent/missions/{created['id']}/approval", json={"approved": True}, headers=headers)
    assert approved.json()["status"] == "completed"
    assert mail_source.calls == [("send_email", {"subject": "Summary", "body": "ok", "to": ALICE_MAIL})]


@pytest.mark.asyncio
async def test_a_user_with_no_address_gets_no_send_tool_over_http(client: httpx.AsyncClient, mail_source, llm):
    llm.script += [_reply_final("Link an email address first.")]
    created = (await client.post("/api/v1/agent/missions", json={"utterance": "email me"}, headers=_bearer("carol"))).json()
    assert created["status"] == "completed"
    assert "send_email" not in _tools_section(llm.prompts[0])
    assert mail_source.calls == []
