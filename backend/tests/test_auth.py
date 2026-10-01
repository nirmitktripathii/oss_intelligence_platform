"""Sign-in: signed tokens, the GitHub OAuth round trip, and who may approve changes."""

import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from app.agent.planner import MissionPlanner, WriteNotAllowed
from app.agent.store import MissionStore
from app.agent.tools import ToolRegistry
from app.api.v1 import agent as agent_api
from app.api.v1 import auth as auth_api
from app.config import settings
from app.schemas.agent import MissionStatus
from app.security import auth
from tests.test_agent_planner import FakeSource, _events, _final, _tool, llm  # noqa: F401  (llm is a fixture)

SECRET = "x" * 40
CALLBACK = "https://api.example.test/api/v1/auth/github/callback"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", SECRET)
    monkeypatch.setattr(settings, "AUTH_GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "AUTH_GITHUB_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "AUTH_GITHUB_CALLBACK_URL", CALLBACK)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "Octocat")
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", False)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.test")


@pytest.fixture
def registry(monkeypatch):
    source = FakeSource()
    monkeypatch.setattr(agent_api, "configured_registry", lambda: ToolRegistry([source]))
    agent_api.limiter.reset()
    auth_api.limiter.reset()
    return source


def _bearer(login: str) -> dict:
    return {"Authorization": "Bearer " + auth.issue_token(auth.KIND_SESSION, 600, sub=login)}


def _session(mission: dict) -> dict:
    return {"X-Session-Token": mission["session_token"]}


# ── Tokens ────────────────────────────────────────────────────────────────── #


def test_token_round_trip():
    token = auth.issue_token(auth.KIND_SESSION, 60, sub="octocat")
    assert auth.verify_token(token, auth.KIND_SESSION)["sub"] == "octocat"


def test_token_of_another_kind_is_rejected():
    state = auth.issue_token(auth.KIND_STATE, 60, n="abc")
    assert auth.verify_token(state, auth.KIND_SESSION) is None


def test_expired_token_is_rejected(monkeypatch):
    token = auth.issue_token(auth.KIND_SESSION, 60, sub="octocat")
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 120)
    assert auth.verify_token(token, auth.KIND_SESSION) is None


def test_tampered_or_garbage_token_is_rejected():
    token = auth.issue_token(auth.KIND_SESSION, 60, sub="octocat")
    body, signature = token.split(".")
    forged = auth.issue_token(auth.KIND_SESSION, 60, sub="mallory").split(".")[0]
    for bad in (None, "", "abc", token + "x", f"{forged}.{signature}", "a.b.c", f"{body}."):
        assert auth.verify_token(bad, auth.KIND_SESSION) is None


def test_token_signed_with_another_secret_is_rejected(monkeypatch):
    token = auth.issue_token(auth.KIND_SESSION, 60, sub="octocat")
    monkeypatch.setattr(settings, "AUTH_SECRET", "y" * 40)
    assert auth.verify_token(token, auth.KIND_SESSION) is None


def test_short_secret_is_refused(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_SECRET", "short")
    with pytest.raises(auth.AuthNotConfigured):
        auth.issue_token(auth.KIND_SESSION, 60, sub="octocat")
    assert auth.verify_token("a.b", auth.KIND_SESSION) is None
    assert not auth.github_oauth_configured()


def test_allow_list_is_case_insensitive_and_empty_means_nobody(monkeypatch):
    assert auth.may_write(auth.AuthUser("OCTOCAT"))
    assert not auth.may_write(auth.AuthUser("mallory"))
    assert not auth.may_write(None)
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "")
    assert not auth.may_write(auth.AuthUser("octocat"))


# ── /auth endpoints ───────────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_me_reports_the_callers_state(client: httpx.AsyncClient, registry):
    anonymous = (await client.get("/api/v1/auth/me")).json()
    assert anonymous == {"signed_in": False, "login": None, "can_write": False, "sign_in_available": True}

    allowed = (await client.get("/api/v1/auth/me", headers=_bearer("octocat"))).json()
    assert allowed["signed_in"] and allowed["login"] == "octocat" and allowed["can_write"]

    other = (await client.get("/api/v1/auth/me", headers=_bearer("mallory"))).json()
    assert other["signed_in"] and not other["can_write"]

    junk = (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"})).json()
    assert junk["signed_in"] is False


@pytest.mark.asyncio
async def test_login_is_503_when_unconfigured(client: httpx.AsyncClient, registry, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_GITHUB_CLIENT_SECRET", None)
    assert (await client.get("/api/v1/auth/github/login")).status_code == 503
    assert (await client.get("/api/v1/auth/me")).json()["sign_in_available"] is False


@pytest.mark.asyncio
async def test_login_redirects_to_github_with_a_bound_state(client: httpx.AsyncClient, registry):
    response = await client.get("/api/v1/auth/github/login", follow_redirects=False)

    assert response.status_code == 302
    target = urlparse(response.headers["location"])
    query = parse_qs(target.query)
    assert f"{target.scheme}://{target.netloc}{target.path}" == auth_api.GITHUB_AUTHORIZE
    assert query["client_id"] == ["client-id"] and query["redirect_uri"] == [CALLBACK]
    assert "scope=&" in target.query or target.query.endswith("scope=")  # empty scope: public profile only
    nonce = response.cookies.get(auth_api.STATE_COOKIE)
    assert nonce and auth.verify_token(query["state"][0], auth.KIND_STATE)["n"] == nonce
    assert "httponly" in response.headers["set-cookie"].lower()


async def _begin(client: httpx.AsyncClient) -> str:
    response = await client.get("/api/v1/auth/github/login", follow_redirects=False)
    # The cookie is Secure (the callback is https), so the http test client will not send it back
    # by itself; hand it over the way a browser on https would.
    client.cookies.set(auth_api.STATE_COOKIE, response.cookies.get(auth_api.STATE_COOKIE), domain="testserver.local")  # cookiejar names dotless hosts "<host>.local"
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


@pytest.mark.asyncio
@respx.mock
async def test_callback_signs_the_user_in(client: httpx.AsyncClient, registry):
    state = await _begin(client)
    respx.post(auth_api.GITHUB_TOKEN_URL).respond(json={"access_token": "gho_test"})
    respx.get(auth_api.GITHUB_USER_URL).respond(json={"login": "octocat"})

    response = await client.get(
        "/api/v1/auth/github/callback", params={"code": "abc", "state": state}, follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://app.example.test/alexa#token=")
    token = location.split("#token=", 1)[1]
    assert auth.verify_token(token, auth.KIND_SESSION)["sub"] == "octocat"
    assert "gho_test" not in location  # GitHub's own token is never handed on


@pytest.mark.asyncio
@respx.mock
async def test_callback_rejects_a_state_from_another_browser(client: httpx.AsyncClient, registry):
    state = await _begin(client)
    client.cookies.clear()  # the browser completing the flow is not the one that began it
    exchange = respx.post(auth_api.GITHUB_TOKEN_URL).respond(json={"access_token": "gho_test"})

    response = await client.get(
        "/api/v1/auth/github/callback", params={"code": "abc", "state": state}, follow_redirects=False,
    )

    assert response.headers["location"].endswith("/alexa?auth_error=state")
    assert not exchange.called


@pytest.mark.asyncio
async def test_callback_rejects_a_forged_state(client: httpx.AsyncClient, registry):
    await _begin(client)
    for state in ("", "forged.state", auth.issue_token(auth.KIND_SESSION, 60, n="x")):
        response = await client.get(
            "/api/v1/auth/github/callback", params={"code": "abc", "state": state}, follow_redirects=False,
        )
        assert response.headers["location"].endswith("auth_error=state")


@pytest.mark.asyncio
@respx.mock
async def test_callback_reports_github_failures(client: httpx.AsyncClient, registry):
    state = await _begin(client)
    respx.post(auth_api.GITHUB_TOKEN_URL).respond(json={"error": "bad_verification_code"})
    bad_code = await client.get(
        "/api/v1/auth/github/callback", params={"code": "abc", "state": state}, follow_redirects=False,
    )
    assert bad_code.headers["location"].endswith("auth_error=exchange")

    state = await _begin(client)
    respx.post(auth_api.GITHUB_TOKEN_URL).respond(json={"access_token": "gho_test"})
    respx.get(auth_api.GITHUB_USER_URL).mock(side_effect=httpx.ConnectError("down"))
    unreachable = await client.get(
        "/api/v1/auth/github/callback", params={"code": "abc", "state": state}, follow_redirects=False,
    )
    assert unreachable.headers["location"].endswith("auth_error=github")


# ── Who may run tools that change things ──────────────────────────────────── #


@pytest.mark.asyncio
async def test_anonymous_callers_only_see_read_only_tools(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    llm.script += [_final("Nothing to change.")]

    created = await client.post("/api/v1/agent/missions", json={"utterance": "open a PR"})

    assert created.status_code == 200
    prompt = llm.prompts[0]
    assert "demo.search" in prompt and "demo.open_pr" not in prompt
    assert "not signed in" in prompt


@pytest.mark.asyncio
async def test_signed_in_allowed_user_sees_and_approves_changes(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    llm.script += [_tool("demo.open_pr", title="Fix crash")]
    headers = _bearer("octocat")
    mission = (await client.post("/api/v1/agent/missions", json={"utterance": "open a PR"}, headers=headers)).json()
    assert mission["status"] == "awaiting_approval"
    assert "not signed in" not in llm.prompts[0]

    llm.script += [_final("Opened.")]
    approved = await client.post(
        f"/api/v1/agent/missions/{mission['id']}/approval",
        json={"approved": True}, headers={**headers, **_session(mission)},
    )

    assert approved.status_code == 200 and approved.json()["status"] == "completed"
    assert registry.calls == [("open_pr", {"title": "Fix crash"})]


async def _gated_mission(client, llm, headers):  # noqa: F811
    llm.script += [_tool("demo.open_pr", title="Fix crash")]
    mission = (await client.post("/api/v1/agent/missions", json={"utterance": "open a PR"}, headers=headers)).json()
    assert mission["status"] == "awaiting_approval"
    return mission


@pytest.mark.asyncio
async def test_approving_needs_sign_in(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    mission = await _gated_mission(client, llm, _bearer("octocat"))
    url = f"/api/v1/agent/missions/{mission['id']}/approval"

    anonymous = await client.post(url, json={"approved": True}, headers=_session(mission))

    assert anonymous.status_code == 401
    assert registry.calls == []


@pytest.mark.asyncio
async def test_a_user_off_the_allow_list_cannot_approve(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    mission = await _gated_mission(client, llm, _bearer("octocat"))
    url = f"/api/v1/agent/missions/{mission['id']}/approval"

    response = await client.post(url, json={"approved": True}, headers={**_bearer("mallory"), **_session(mission)})

    assert response.status_code == 403
    assert registry.calls == []


@pytest.mark.asyncio
async def test_only_the_owner_can_approve(client: httpx.AsyncClient, registry, llm, monkeypatch):  # noqa: F811
    monkeypatch.setattr(settings, "AUTH_ALLOWED_LOGINS", "octocat,hubot")
    mission = await _gated_mission(client, llm, _bearer("octocat"))
    url = f"/api/v1/agent/missions/{mission['id']}/approval"

    # hubot is allowed to write, and even holds the session token, but the conversation is octocat's
    response = await client.post(url, json={"approved": True}, headers={**_bearer("hubot"), **_session(mission)})

    assert response.status_code == 403
    assert registry.calls == []


@pytest.mark.asyncio
async def test_stream_approval_is_gated_the_same_way(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    mission = await _gated_mission(client, llm, _bearer("octocat"))
    url = f"/api/v1/agent/missions/{mission['id']}/approval/stream"

    anonymous = await client.post(url, json={"approved": True}, headers=_session(mission))

    assert anonymous.status_code == 401
    assert registry.calls == []


@pytest.mark.asyncio
async def test_anyone_with_the_session_token_can_reject(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    mission = await _gated_mission(client, llm, _bearer("octocat"))
    url = f"/api/v1/agent/missions/{mission['id']}/approval"
    llm.script += [_final("Okay, I left it alone.")]

    response = await client.post(url, json={"approved": False}, headers=_session(mission))

    assert response.status_code == 200
    assert registry.calls == []


@pytest.mark.asyncio
async def test_someone_elses_conversation_stays_read_only(client: httpx.AsyncClient, registry, llm):  # noqa: F811
    first = await _gated_mission(client, llm, _bearer("octocat"))
    llm.script += [_final("Looked around.")]

    # a signed-in but unlisted user continuing the conversation gets the read-only tool set
    followup = await client.post(
        "/api/v1/agent/missions", json={"utterance": "and now?"}, headers={**_bearer("mallory"), **_session(first)},
    )

    assert followup.status_code == 200
    assert "demo.open_pr" not in llm.prompts[-1]


@pytest.mark.asyncio
async def test_anonymous_writes_flag_restores_local_demo_behaviour(
    client: httpx.AsyncClient, registry, llm, monkeypatch,  # noqa: F811
):
    monkeypatch.setattr(settings, "AGENT_ALLOW_ANONYMOUS_WRITES", True)
    mission = await _gated_mission(client, llm, {})
    llm.script += [_final("Opened.")]

    response = await client.post(
        f"/api/v1/agent/missions/{mission['id']}/approval", json={"approved": True}, headers=_session(mission),
    )

    assert response.status_code == 200 and registry.calls == [("open_pr", {"title": "Fix crash"})]


# ── Planner, without HTTP ─────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_read_only_planner_refuses_to_approve(llm):  # noqa: F811
    source = FakeSource()
    writer = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=3)
    llm.script += [_tool("demo.open_pr", title="Fix crash")]
    mission = await writer.start("open a PR", owner="octocat")
    assert mission.status == MissionStatus.AWAITING_APPROVAL

    reader = MissionPlanner(ToolRegistry([source]), store=writer.store, max_steps=3, can_write=False)
    with pytest.raises(WriteNotAllowed):
        await reader.resolve_approval(mission.id, True)
    assert source.calls == []
    assert await writer.store.session_owner(mission.session_id) == "octocat"


@pytest.mark.asyncio
async def test_read_only_planner_cannot_call_a_gated_tool_even_if_the_model_asks(llm):  # noqa: F811
    source = FakeSource()
    planner = MissionPlanner(ToolRegistry([source]), store=MissionStore(), max_steps=3, can_write=False)
    llm.script += [_tool("demo.open_pr", title="Fix crash"), _final("I could not do that.")]

    mission = await planner.start("open a PR")

    assert mission.status != MissionStatus.AWAITING_APPROVAL
    assert source.calls == []
