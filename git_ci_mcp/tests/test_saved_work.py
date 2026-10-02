"""Saved progress: a signed-in user's unfinished work outlives their sandbox (idle cleanup, reclaim,
or a wiped disk) and comes back on their next sandbox_clone, unless its pull request is finished."""

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gitci_mcp import github as github_mod
from gitci_mcp.config import Settings
from gitci_mcp.github import GitHub
from gitci_mcp.sandbox import GitCiError, SandboxManager, remove_tree
from gitci_mcp.saved import FileStore, PostgresStore, SavedStore, postgres_url
from gitci_mcp.server import mcp

REPO = "https://github.com/o/r"


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


class Env:
    """A real local origin, a manager over it, and helpers to look at the disk."""

    def __init__(self, tmp_path, store=None, pr_state=None, **cfg_overrides):
        self.origin = tmp_path / "origin"
        self.origin.mkdir()
        _git(self.origin, "init", "-b", "main")
        (self.origin / "a.txt").write_text("hello\n")
        (self.origin / "b.txt").write_text("one\n")
        _git(self.origin, "add", ".")
        _git(self.origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "init")
        self.cfg = Settings()
        self.cfg.sandbox_root = str(tmp_path / "sb")
        self.cfg.save_database_url = ""
        self.cfg.save_dir = str(tmp_path / "saved")
        self.cfg.allowed_owners = ["o"]
        self.cfg.author_name, self.cfg.author_email = "Test", "test@example.com"
        self.cfg.max_sandboxes, self.cfg.sandbox_ttl_seconds, self.cfg.sandbox_reclaim_seconds = 15, 1800, 600
        for key, value in cfg_overrides.items():
            setattr(self.cfg, key, value)
        self.mgr = SandboxManager(self.cfg, store=store, pr_state=pr_state)

    async def clone(self, user="", fresh=False):
        return await self.mgr.create(REPO, source=str(self.origin), user=user, fresh=fresh)

    def repo(self, sid):
        return Path(self.cfg.sandbox_root) / sid / "repo"

    def exists(self, sid):
        return (Path(self.cfg.sandbox_root) / sid / "meta.json").is_file()

    def age(self, sid, seconds):
        meta = Path(self.cfg.sandbox_root) / sid / "meta.json"
        then = meta.stat().st_mtime - seconds
        os.utime(meta, (then, then))

    def wipe_disk(self):
        """What a Render free instance does on sleep or redeploy."""
        remove_tree(Path(self.cfg.sandbox_root))
        assert not Path(self.cfg.sandbox_root).exists()

    async def half_done_fix(self, sid):
        """A branch with one commit, then an uncommitted edit and a brand-new file."""
        await self.mgr.create_branch(sid, "fix-greeting")
        await self.mgr.edit_file(sid, "a.txt", "hello", "hello world")
        await self.mgr.commit(sid, "Fix greeting")
        await self.mgr.edit_file(sid, "b.txt", "one", "two")
        (self.repo(sid) / "new.txt").write_text("brand new\n")
        await self.mgr.edit_file(sid, "b.txt", "two", "three")  # any change saves


class BrokenStore(SavedStore):
    async def get(self, owner, repo):
        return None

    async def put(self, owner, repo, data):
        raise ConnectionError("database is down")

    async def delete(self, owner, repo):
        pass


def test_work_survives_a_wiped_disk_and_comes_back_on_the_next_clone(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("Alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        env.wipe_disk()  # no destroy, no warning: the save after each change is what counts

        again = await env.clone("alice")
        resumed = again["resumed"]
        assert resumed["restored"] is True
        assert again["branch"] == resumed["branch"] == "fix-greeting"
        assert resumed["commits"] == 1
        assert set(resumed["files_changed"]) == {"a.txt", "b.txt", "new.txt"}
        repo = env.repo(again["sandbox_id"])
        assert (repo / "a.txt").read_text() == "hello world\n"
        assert (repo / "b.txt").read_text() == "three\n"
        assert (repo / "new.txt").read_text() == "brand new\n"
        assert _git(repo, "log", "-1", "--format=%s").strip() == "Fix greeting"
        status = await env.mgr.status(again["sandbox_id"])
        assert status["commits_ahead_of_base"] == 1
        assert set(status["uncommitted_files"]) == {"b.txt", "new.txt"}

    asyncio.run(flow())


def test_destroy_saves_first(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        await env.mgr.destroy(sid)
        assert not env.exists(sid)
        again = await env.clone("alice")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "a.txt").read_text() == "hi\n"

    asyncio.run(flow())


def test_fresh_starts_clean_but_keeps_the_saved_work(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        clean = await env.clone("alice", fresh=True)
        assert "resumed" not in clean and clean["branch"] == "main"
        assert (env.repo(clean["sandbox_id"]) / "a.txt").read_text() == "hello\n"
        # fresh does not throw the saved work away, and the clean sandbox has nothing to overwrite it
        await env.mgr.destroy(clean["sandbox_id"])
        assert (await env.clone("alice"))["resumed"]["restored"] is True

    asyncio.run(flow())


def test_each_user_has_one_sandbox_per_repo(tmp_path):
    env = Env(tmp_path)

    async def flow():
        first = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(first, "a.txt", "hello", "hi")
        second = (await env.clone("alice"))["sandbox_id"]
        bob = (await env.clone("bob"))["sandbox_id"]
        assert not env.exists(first)  # replaced, and its work carried over
        assert env.exists(second) and env.exists(bob)
        assert (env.repo(second) / "a.txt").read_text() == "hi\n"
        assert (env.repo(bob) / "a.txt").read_text() == "hello\n"  # nobody sees another user's work

    asyncio.run(flow())


def test_anonymous_sandboxes_are_not_saved(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone())["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        await env.mgr.destroy(sid)
        assert "resumed" not in await env.clone()
        assert not Path(env.cfg.save_dir).exists() or not any(Path(env.cfg.save_dir).iterdir())

    asyncio.run(flow())


def test_a_full_pool_saves_the_idle_sandbox_before_reclaiming_it(tmp_path):
    env = Env(tmp_path, max_sandboxes=2)

    async def flow():
        alice = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(alice, "a.txt", "hello", "hi")
        await env.clone("bob")
        env.age(alice, 900)
        carol = (await env.clone("carol"))["sandbox_id"]  # pool full: alice's idle sandbox makes room
        assert not env.exists(alice) and env.exists(carol)

        # Alice comes back later, once another sandbox has gone idle.
        env.age(carol, 700)
        again = await env.clone("alice")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "a.txt").read_text() == "hi\n"

    asyncio.run(flow())


def test_a_sandbox_whose_work_cannot_be_saved_is_never_deleted(tmp_path):
    env = Env(tmp_path, store=BrokenStore(), max_sandboxes=1)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")  # the change works; only the save failed
        with pytest.raises(GitCiError, match="could not be saved"):
            await env.mgr.destroy(sid)
        env.age(sid, 900)
        with pytest.raises(GitCiError, match="in use"):
            await env.clone("bob")  # not reclaimed either
        env.age(sid, 2000)
        with pytest.raises(GitCiError, match="in use"):
            await env.clone("bob")  # nor deleted as abandoned
        assert env.exists(sid) and (env.repo(sid) / "a.txt").read_text() == "hi\n"

    asyncio.run(flow())


def test_work_too_large_to_save_keeps_its_sandbox(tmp_path):
    env = Env(tmp_path, max_save_bytes=50)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        (env.repo(sid) / "big.txt").write_text("x" * 500)
        with pytest.raises(GitCiError, match="could not be saved"):
            await env.mgr.destroy(sid)
        assert env.exists(sid)

    asyncio.run(flow())


def test_bytecode_and_test_caches_are_not_part_of_the_saved_work(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        cache = env.repo(sid) / "pkg" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "m.cpython-312.pyc").write_bytes(b"\x00\x01")
        (env.repo(sid) / ".pytest_cache").mkdir()
        (env.repo(sid) / ".pytest_cache" / "v").write_text("x")
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        env.wipe_disk()
        again = await env.clone("alice")
        assert again["resumed"]["files_changed"] == ["a.txt"]
        assert not (env.repo(again["sandbox_id"]) / "pkg").exists()

    asyncio.run(flow())


@pytest.mark.parametrize("state", ["merged", "closed"])
def test_work_whose_pull_request_is_finished_is_not_put_back(tmp_path, state):
    async def pr_state(url):
        return state

    env = Env(tmp_path, pr_state=pr_state)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        await env.mgr.record_pr(sid, "https://github.com/o/r/pull/7")
        env.wipe_disk()
        again = await env.clone("alice")
        assert again["resumed"]["restored"] is False
        assert again["resumed"]["pull_request_state"] == state
        assert again["branch"] == "main"
        assert await env.mgr.store.get("alice", "o/r") is None  # done with: dropped

    asyncio.run(flow())


def test_work_with_an_open_pull_request_resumes_on_the_pushed_branch(tmp_path):
    async def pr_state(url):
        return "open"

    env = Env(tmp_path, pr_state=pr_state)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-greeting")
        await env.mgr.edit_file(sid, "a.txt", "hello", "hello world")
        await env.mgr.commit(sid, "Fix greeting")
        await env.mgr.push_branch(sid, "token")  # a local origin ignores the token
        await env.mgr.record_pr(sid, "https://github.com/o/r/pull/7")
        pushed = _git(env.repo(sid), "rev-parse", "HEAD").strip()
        await env.mgr.edit_file(sid, "b.txt", "one", "two")
        await env.mgr.commit(sid, "Follow-up")  # after the push: only this is in the saved patch
        env.wipe_disk()

        again = await env.clone("alice")
        resumed = again["resumed"]
        assert resumed["restored"] is True and resumed["pull_request"] == "https://github.com/o/r/pull/7"
        repo = env.repo(again["sandbox_id"])
        assert _git(repo, "rev-parse", "HEAD~1").strip() == pushed  # the same commit GitHub has
        assert (repo / "b.txt").read_text() == "two\n"
        # So pushing again is a fast-forward, not a rejected rewrite of the pull request's branch.
        await env.mgr.push_branch(again["sandbox_id"], "token")
        assert _git(env.origin, "log", "-1", "--format=%s", "fix-greeting").strip() == "Follow-up"

    asyncio.run(flow())


def test_saved_work_that_no_longer_applies_is_kept_and_the_sandbox_starts_clean(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        await env.mgr.destroy(sid)
        # Someone rewrote a.txt on the base branch since.
        (env.origin / "a.txt").write_text("completely different\n")
        _git(env.origin, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-am", "rewrite")
        data = await env.mgr.store.get("alice", "o/r")
        data["base_sha"] = "f" * 40  # and the old base is gone (force-push)
        await env.mgr.store.put("alice", "o/r", data)

        again = await env.clone("alice")
        assert again["resumed"]["restored"] is False and "kept" in again["resumed"]["note"]
        repo = env.repo(again["sandbox_id"])
        assert again["branch"] == "main" and _git(repo, "status", "--porcelain").strip() == ""
        assert (repo / "a.txt").read_text() == "completely different\n"
        assert await env.mgr.store.get("alice", "o/r") is not None

    asyncio.run(flow())


@pytest.mark.parametrize("owner", ["not a login", "../x", "a" * 40])
def test_the_owner_must_be_a_github_login(tmp_path, owner):
    env = Env(tmp_path)
    with pytest.raises(GitCiError, match="GitHub login"):
        asyncio.run(env.clone(owner))


def test_test_runs_wait_for_a_slot_then_ask_to_retry(tmp_path):
    env = Env(tmp_path, max_concurrent_tests=1, test_queue_seconds=0.2, test_commands=["git --version"])

    async def flow():
        sid = (await env.clone())["sandbox_id"]
        assert (await env.mgr.run_tests(sid, "git --version"))["passed"] is True
        await env.mgr._tests.acquire()  # another mission's run is in progress
        with pytest.raises(GitCiError, match="running their tests"):
            await env.mgr.run_tests(sid, "git --version")
        env.mgr._tests.release()
        assert (await env.mgr.run_tests(sid, "git --version"))["passed"] is True

    asyncio.run(flow())


def test_sandbox_clone_takes_fresh_and_a_system_set_owner():
    tool = next(t for t in asyncio.run(mcp.list_tools()) if t.name == "sandbox_clone")
    schema = getattr(tool, "inputSchema", None) or tool.input_schema
    assert {"fresh", "owner"} <= set(schema["properties"])
    assert "set by the system" in tool.description


# ---------------------------------------------------------------- stores
def test_file_store_expires_old_work(tmp_path):
    store = FileStore(str(tmp_path), keep_days=14)

    async def flow():
        await store.put("alice", "o/r", {"saved_at": time.time()})
        assert await store.get("alice", "o/r")
        assert await store.get("bob", "o/r") is None
        await store.put("alice", "o/r", {"saved_at": time.time() - 15 * 86400})
        assert await store.get("alice", "o/r") is None
        await store.delete("alice", "o/r")

    asyncio.run(flow())


@pytest.mark.parametrize("given, expected", [
    ("postgresql+asyncpg://u:p@h/db?ssl=require", "postgresql://u:p@h/db?sslmode=require"),
    ("postgres://u:p@h:5432/db", "postgresql://u:p@h:5432/db"),
    ("postgresql://u:p@h/db?sslmode=require&prepared_statement_cache_size=0",
     "postgresql://u:p@h/db?sslmode=require"),
])
def test_postgres_url_accepts_the_forms_people_paste(given, expected):
    assert postgres_url(given) == expected


@pytest.fixture(scope="module")
def postgres():
    pgserver = pytest.importorskip("pgserver")
    pytest.importorskip("psycopg")
    root = tempfile.mkdtemp(prefix="gitci-pg-")
    server = pgserver.get_server(root, cleanup_mode="stop")
    yield server.get_uri()
    server.cleanup()
    shutil.rmtree(root, ignore_errors=True)


def test_postgres_store_round_trip_and_expiry(postgres):
    import psycopg

    store = PostgresStore(postgres, keep_days=14)

    async def flow():
        await store.delete("alice", "o/r")
        assert await store.get("alice", "o/r") is None
        await store.put("alice", "o/r", {"branch": "fix-a", "commits_patch": "x\r\n\x7f"})
        await store.put("alice", "o/r", {"branch": "fix-b"})  # upsert
        assert (await store.get("alice", "o/r"))["branch"] == "fix-b"
        assert await store.get("bob", "o/r") is None
        with psycopg.connect(store.url, autocommit=True) as conn:
            conn.execute("UPDATE gitci_saved_work SET saved_at = now() - interval '15 days'")
        assert await store.get("alice", "o/r") is None
        await store.delete("alice", "o/r")

    asyncio.run(flow())


def test_resume_through_postgres(tmp_path, postgres):
    env = Env(tmp_path, store=PostgresStore(postgres, keep_days=14))

    async def flow():
        await env.mgr.store.delete("alice", "o/r")
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        env.wipe_disk()
        again = await env.clone("alice")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "b.txt").read_text() == "three\n"
        await env.mgr.store.delete("alice", "o/r")

    asyncio.run(flow())


# ---------------------------------------------------------------- GitHub pull request state
@pytest.fixture
def github(monkeypatch):
    routes = {}

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={})
        status, body = routes[key]
        return httpx.Response(status, json=body)

    real = httpx.AsyncClient
    monkeypatch.setattr(github_mod.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    cfg = Settings()
    cfg.github_token = "t"
    return GitHub(cfg), routes


@pytest.mark.parametrize("body, expected", [
    ({"state": "closed", "merged_at": "2026-10-03T00:00:00Z"}, "merged"),
    ({"state": "closed", "merged_at": None}, "closed"),
    ({"state": "open", "merged_at": None}, "open"),
])
def test_pr_state(github, body, expected):
    gh, routes = github
    routes[("GET", "/repos/o/r/pulls/7")] = (200, body)
    assert asyncio.run(gh.pr_state("https://github.com/o/r/pull/7")) == expected


@pytest.mark.parametrize("url", ["https://github.com/o/r/pull/8", "https://evil.example/o/r/pull/7", ""])
def test_pr_state_is_unknown_when_github_cannot_say(github, url):
    gh, _ = github
    assert asyncio.run(gh.pr_state(url)) == "unknown"


def test_draft_pr_on_a_resumed_branch_returns_its_open_pull_request(github):
    gh, routes = github
    routes[("POST", "/repos/o/r/pulls")] = (422, {"message": "A pull request already exists"})
    routes[("GET", "/repos/o/r/pulls")] = (200, [{"number": 7, "html_url": "https://github.com/o/r/pull/7",
                                                   "draft": True}])
    pr = asyncio.run(gh.draft_pr("o", "r", "fix-greeting", "main", "t", "b"))
    assert pr == {"created": False, "updated": True, "draft": True, "number": 7,
                  "url": "https://github.com/o/r/pull/7"}
