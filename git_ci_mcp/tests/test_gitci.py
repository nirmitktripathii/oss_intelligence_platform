"""Offline tests: tool surface, input validation, and a full local clone/branch/patch/commit flow."""

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gitci_mcp.config import Settings
from gitci_mcp.sandbox import GitCiError, SandboxManager, check_ref, parse_repo_url, validate_patch
from gitci_mcp.server import mcp

PATCH = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-hello\n+hello world\n"


def test_tools_registered_and_described():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {"sandbox_clone", "apply_patch", "run_tests", "commit_changes", "ci_status", "draft_pr"} <= names
    assert all(t.description for t in tools)


def test_repo_url_must_be_github_https():
    assert parse_repo_url("https://github.com/o/r.git") == ("o", "r")
    for bad in ("git@github.com:o/r.git", "https://evil.com/o/r", "file:///etc", "https://github.com/o/r/../x"):
        with pytest.raises(GitCiError):
            parse_repo_url(bad)


@pytest.mark.parametrize("name", ["-x", "a..b", "a b", "a.lock", "x/", ""])
def test_bad_branch_names(name):
    with pytest.raises(GitCiError):
        check_ref(name)


@pytest.mark.parametrize("path", ["../x", "/etc/passwd", "a/.git/hooks/pre-commit", "C:/x"])
def test_patch_rejects_unsafe_paths(path):
    diff = f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-a\n+b\n"
    with pytest.raises(GitCiError):
        validate_patch(diff, 10000)


def test_patch_size_and_empty():
    with pytest.raises(GitCiError):
        validate_patch("", 100)
    with pytest.raises(GitCiError):
        validate_patch(PATCH, 10)


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def test_full_local_flow(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    (origin / "a.txt").write_text("hello\n")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")

    cfg = Settings()
    cfg.sandbox_root = str(tmp_path / "sb")
    cfg.allowed_owners = ["o"]
    cfg.author_name, cfg.author_email = "Test", "test@example.com"
    mgr = SandboxManager(cfg)

    async def flow():
        with pytest.raises(GitCiError):
            await mgr.create("https://github.com/stranger/r")
        s = await mgr.create("https://github.com/o/r", source=str(origin))
        sid = s["sandbox_id"]
        await mgr.create_branch(sid, "fix/hello")
        assert (await mgr.apply_patch(sid, PATCH))["files"] == ["a.txt"]
        assert "hello world" in (await mgr.diff(sid))["diff"]
        with pytest.raises(GitCiError):
            await mgr.run_tests(sid, "rm -rf /")
        c = await mgr.commit(sid, "Fix greeting")
        st = await mgr.status(sid)
        assert st["commits_ahead_of_base"] == 1 and st["uncommitted_files"] == []
        assert c["commit"]
        with pytest.raises(GitCiError):
            await mgr.push_branch(sid, "")
        await mgr.destroy(sid)
        with pytest.raises(GitCiError):
            await mgr.status(sid)

    asyncio.run(flow())


def test_create_branch_refuses_a_name_that_already_exists_on_origin(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    (origin / "a.txt").write_text("hello\n")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")
    _git(origin, "branch", "fix-slugify")  # an earlier run's branch

    cfg = Settings()
    cfg.sandbox_root = str(tmp_path / "sb")
    cfg.allowed_owners = ["o"]
    mgr = SandboxManager(cfg)

    async def flow():
        sid = (await mgr.create("https://github.com/o/r", source=str(origin)))["sandbox_id"]
        with pytest.raises(GitCiError, match="already exists on GitHub.*fix-slugify-2"):
            await mgr.create_branch(sid, "fix-slugify")
        assert (await mgr.create_branch(sid, "fix-slugify-2"))["branch"] == "fix-slugify-2"

    asyncio.run(flow())


def test_read_only_file_tools_and_path_confinement(tmp_path):
    demo = Path(__file__).resolve().parents[2] / "demo" / "sandbox-repo"
    origin = tmp_path / "origin"
    import shutil

    shutil.copytree(demo, origin)
    _git(origin, "init", "-b", "main")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")

    cfg = Settings()
    cfg.sandbox_root = str(tmp_path / "sb")
    cfg.allowed_owners = ["o"]
    cfg.test_commands = ["python -m pytest -q"]
    mgr = SandboxManager(cfg)

    async def flow():
        sid = (await mgr.create("https://github.com/o/r", source=str(origin)))["sandbox_id"]
        assert "textkit/slug.py" in (await mgr.list_files(sid))["files"]
        assert "def slugify" in (await mgr.read_file(sid, "textkit/slug.py"))["content"]
        for bad in ("../origin/README.md", "/etc/passwd", ".git/config", "missing.py"):
            with pytest.raises(GitCiError):
                await mgr.read_file(sid, bad)

        before = await mgr.run_tests(sid, "python -m pytest -q")
        assert before["passed"] is False  # the demo bug is real

        fix = (
            "--- a/textkit/slug.py\n+++ b/textkit/slug.py\n@@ -1,8 +1,8 @@\n"
            ' """Turn a title into a URL-safe slug."""\n \n import re\n \n \n'
            ' def slugify(text: str) -> str:\n'
            '     """Lower-case the text and join its words with single hyphens."""\n'
            '-    return re.sub(r"\\s+", "-", text.strip().lower())\n'
            '+    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")\n'
        )
        await mgr.create_branch(sid, "fix/slugify")
        await mgr.apply_patch(sid, fix)
        after = await mgr.run_tests(sid, "python -m pytest -q")
        assert after["passed"] is True, after["output_tail"]

    asyncio.run(flow())


def test_edit_file_exact_match_and_recount_patch(tmp_path):
    import shutil

    demo = Path(__file__).resolve().parents[2] / "demo" / "sandbox-repo"
    origin = tmp_path / "origin"
    shutil.copytree(demo, origin)
    _git(origin, "init", "-b", "main")
    _git(origin, "add", ".")
    _git(origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")
    cfg = Settings()
    cfg.sandbox_root = str(tmp_path / "sb")
    cfg.allowed_owners = ["o"]
    cfg.test_commands = ["python -m pytest -q"]
    mgr = SandboxManager(cfg)

    async def flow():
        sid = (await mgr.create("https://github.com/o/r", source=str(origin)))["sandbox_id"]
        with pytest.raises(GitCiError):
            await mgr.edit_file(sid, "textkit/slug.py", "no such text", "x")
        with pytest.raises(GitCiError):
            await mgr.edit_file(sid, "../x", "a", "b")
        await mgr.edit_file(
            sid, "textkit/slug.py",
            'return re.sub(r"\\s+", "-", text.strip().lower())',
            'return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")',
        )
        assert (await mgr.run_tests(sid, "python -m pytest -q"))["passed"] is True
        await mgr.destroy(sid)

        # A hunk header with the wrong counts (what the model produced) is accepted thanks to --recount.
        sid = (await mgr.create("https://github.com/o/r", source=str(origin)))["sandbox_id"]
        bad_counts = (
            "--- a/textkit/slug.py\n+++ b/textkit/slug.py\n@@ -6,2 +6,3 @@\n"
            " def slugify(text: str) -> str:\n"
            '     """Lower-case the text and join its words with single hyphens."""\n'
            '-    return re.sub(r"\\s+", "-", text.strip().lower())\n'
            '+    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")\n'
        )
        await mgr.apply_patch(sid, bad_counts)
        assert (await mgr.run_tests(sid, "python -m pytest -q"))["passed"] is True

    asyncio.run(flow())


# ── Access token in front of the MCP endpoint ─────────────────────────────── #


def _asgi_ok():
    async def app(scope, receive, send):
        if scope["type"] == "http":
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
    return app


def test_bearer_middleware_only_lets_the_right_token_through():
    import httpx

    from gitci_mcp.auth import BearerAuthMiddleware

    token = "t" * 40
    app = BearerAuthMiddleware(_asgi_ok(), token)

    async def call(headers):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            return await client.post("/mcp", headers=headers)

    assert asyncio.run(call({})).status_code == 401
    assert asyncio.run(call({"Authorization": "Bearer nope"})).status_code == 401
    assert asyncio.run(call({"Authorization": token})).status_code == 401  # no scheme
    assert asyncio.run(call({"Authorization": "Basic " + token})).status_code == 401
    assert asyncio.run(call({"Authorization": "Bearer " + token})).status_code == 200
    assert asyncio.run(call({"Authorization": "bearer " + token})).status_code == 200


def test_server_refuses_to_listen_publicly_without_a_strong_token():
    from gitci_mcp.auth import require_token

    require_token("127.0.0.1", "")  # local demo: no token needed
    require_token("localhost", "")
    require_token("0.0.0.0", "t" * 40)
    with pytest.raises(RuntimeError, match="GITCI_MCP_TOKEN is required"):
        require_token("0.0.0.0", "")
    with pytest.raises(RuntimeError, match="at least 32"):
        require_token("0.0.0.0", "short")


def test_allowed_repos_pins_the_server_to_named_repos(tmp_path):
    cfg = Settings()
    cfg.sandbox_root = str(tmp_path)
    cfg.allowed_owners = ["me"]
    cfg.allowed_repos = ["me/demo"]
    manager = SandboxManager(cfg)

    manager.check_repo("me", "demo")
    manager.check_repo("ME", "Demo")  # GitHub names are case-insensitive
    with pytest.raises(GitCiError, match="not an allowed repo"):
        manager.check_repo("me", "other")
    with pytest.raises(GitCiError, match="not an allowed owner"):
        manager.check_repo("stranger", "demo")

    cfg.allowed_repos = []  # unset: any repo of an allowed owner
    manager.check_repo("me", "other")


def test_ci_status_respects_the_repo_allow_list(monkeypatch):
    from gitci_mcp import server

    monkeypatch.setattr(server.settings, "allowed_owners", ["me"])
    monkeypatch.setattr(server.settings, "allowed_repos", ["me/demo"])

    async def never(*_a, **_k):
        raise AssertionError("must not reach GitHub for a repo that is not allowed")

    monkeypatch.setattr(server._github, "ci_status", never)

    result = asyncio.run(server.ci_status("torvalds/linux", "main"))

    assert "not an allowed owner" in result["error"]


# ── send_report ───────────────────────────────────────────────────────────── #

import httpx

from gitci_mcp import report as report_mod
from gitci_mcp.report import Reporter


def _reporter(**overrides):
    cfg = Settings()
    cfg.allowed_owners = ["o"]
    cfg.allowed_repos = ["o/r"]
    cfg.telegram_bot_token, cfg.telegram_chat_id = "123:SECRET-TOKEN", "42"
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return Reporter(cfg)


@pytest.fixture
def telegram(monkeypatch):
    """Replace Telegram with a recorder; the test sets .status to simulate a refusal."""
    class Fake:
        status, calls, boom = 200, [], False

    fake = Fake()
    fake.calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if fake.boom:
            raise httpx.ConnectError("down", request=request)
        fake.calls.append((str(request.url), request.read().decode()))
        return httpx.Response(fake.status, json={"ok": fake.status == 200})

    real = httpx.AsyncClient
    monkeypatch.setattr(report_mod.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    return fake


def test_send_report_is_registered():
    assert "send_report" in {t.name for t in asyncio.run(mcp.list_tools())}


def test_report_goes_to_the_configured_chat_as_plain_text(telegram):
    result = asyncio.run(_reporter().send("Fixed slugify", "Tests pass.", "https://github.com/o/r/pull/3"))
    assert result == {"sent": True, "channel": "telegram", "characters": result["characters"]}
    url, body = telegram.calls[0]
    assert url == "https://api.telegram.org/bot123:SECRET-TOKEN/sendMessage"
    assert '"chat_id": "42"' in body or '"chat_id":"42"' in body
    assert "parse_mode" not in body
    assert "https://github.com/o/r/pull/3" in body


def test_report_needs_telegram_to_be_set_up(telegram):
    with pytest.raises(GitCiError, match="not set up"):
        asyncio.run(_reporter(telegram_chat_id="").send("t", "s"))
    assert telegram.calls == []


@pytest.mark.parametrize("url", [
    "https://evil.example/o/r/pull/1",
    "https://github.com/o/r/issues/1",
    "https://github.com/stranger/r/pull/1",   # right shape, owner not allowed
    "https://github.com/o/other/pull/1",      # right owner, repo not allowed
    "javascript:alert(1)",
])
def test_report_link_must_be_a_pull_request_in_an_allowed_repo(telegram, url):
    with pytest.raises(GitCiError):
        asyncio.run(_reporter().send("t", "s", url))
    assert telegram.calls == []


def test_report_fields_are_capped_and_cleaned():
    text = _reporter().render("T" * 500, "line\x00one\n" + "x" * 5000)
    assert len(text) < 1500
    assert "\x00" not in text


def test_telegram_failure_never_leaks_the_token(telegram):
    telegram.status = 401
    with pytest.raises(GitCiError) as refused:
        asyncio.run(_reporter().send("t", "s"))
    telegram.boom = True
    with pytest.raises(GitCiError) as unreachable:
        asyncio.run(_reporter().send("t", "s"))
    assert "SECRET-TOKEN" not in str(refused.value) + str(unreachable.value)


def test_report_rate_limit(telegram):
    rep = _reporter(report_max_per_hour=2)

    async def go():
        await rep.send("a", "s")
        await rep.send("b", "s")
        with pytest.raises(GitCiError, match="limit"):
            await rep.send("c", "s")

    asyncio.run(go())
    assert len(telegram.calls) == 2


def test_report_goes_to_the_chat_the_backend_names(telegram):
    asyncio.run(_reporter().send("Fixed slugify", "Tests pass.", chat_id="987654321"))
    _, body = telegram.calls[0]
    assert '"chat_id": "987654321"' in body or '"chat_id":"987654321"' in body
    assert "42" not in body.replace("987654321", "")


def test_a_named_chat_works_without_a_configured_fallback_chat(telegram):
    asyncio.run(_reporter(telegram_chat_id="").send("t", "s", chat_id="555000111"))
    assert len(telegram.calls) == 1


@pytest.mark.parametrize("chat_id", ["@someone", "12", "1; DROP", "123456789\n987654321", "9" * 30, "abcdef"])
def test_a_chat_id_must_be_a_telegram_chat_id(telegram, chat_id):
    with pytest.raises(GitCiError, match="chat_id"):
        asyncio.run(_reporter().send("t", "s", chat_id=chat_id))
    assert telegram.calls == []


def test_the_hourly_cap_is_per_chat(telegram):
    rep = _reporter(report_max_per_hour=1)

    async def go():
        await rep.send("a", "s", chat_id="1111111")
        await rep.send("a", "s", chat_id="2222222")  # a different person is not held up by the first
        with pytest.raises(GitCiError, match="limit"):
            await rep.send("b", "s", chat_id="1111111")

    asyncio.run(go())
    assert len(telegram.calls) == 2


def test_a_global_cap_bounds_the_bot_across_chats(telegram):
    rep = _reporter(report_max_per_hour=5, report_global_max_per_hour=2)

    async def go():
        await rep.send("a", "s", chat_id="1111111")
        await rep.send("a", "s", chat_id="2222222")
        with pytest.raises(GitCiError, match="busy"):
            await rep.send("a", "s", chat_id="3333333")

    asyncio.run(go())
    assert len(telegram.calls) == 2


def test_the_bot_token_never_reaches_the_logs(telegram, caplog):
    # httpx logs each request URL at INFO, and a Telegram URL contains the token.
    with caplog.at_level("INFO"):
        asyncio.run(_reporter().send("t", "s"))
    assert "SECRET-TOKEN" not in caplog.text
