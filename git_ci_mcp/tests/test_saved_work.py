"""Saved progress: a signed-in user's unfinished work outlives their sandbox (idle cleanup, reclaim,
or a wiped disk). One record per user, repo and branch: work on one issue never overwrites work on
another, sandbox_clone lists what is saved, and sandbox_clone with a branch puts that work back."""

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
        self.cfg.max_sandboxes_per_user, self.cfg.save_grace_seconds = 5, 86400
        self.cfg.max_saved_branches, self.cfg.max_saved_bytes_per_user = 15, 100_000_000
        for key, value in cfg_overrides.items():
            setattr(self.cfg, key, value)
        self.mgr = SandboxManager(self.cfg, store=store, pr_state=pr_state)

    async def clone(self, user="", branch=None):
        return await self.mgr.create(REPO, source=str(self.origin), user=user, branch=branch)

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

    async def half_done_fix(self, sid, branch="fix-greeting"):
        """A branch with one commit, then an uncommitted edit and a brand-new file."""
        await self.mgr.create_branch(sid, branch)
        await self.mgr.edit_file(sid, "a.txt", "hello", "hello world")
        await self.mgr.commit(sid, "Fix greeting")
        await self.mgr.edit_file(sid, "b.txt", "one", "two")
        (self.repo(sid) / "new.txt").write_text("brand new\n")
        return await self.mgr.edit_file(sid, "b.txt", "two", "three")  # any change saves

    async def saved(self, user="alice"):
        return {(r["repo"], r["branch"]) for r in await self.mgr.store.list(user)}


class BrokenStore(SavedStore):
    async def get(self, owner, repo, branch):
        return None

    async def put(self, owner, repo, branch, data):
        raise ConnectionError("database is down")

    async def delete(self, owner, repo, branch):
        pass

    async def list(self, owner):
        return []


# ---------------------------------------------------------------- saving and resuming
def test_work_survives_a_wiped_disk_and_comes_back_by_branch(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("Alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        env.wipe_disk()  # no destroy, no warning: the save after each change is what counts

        clean = await env.clone("alice")
        assert clean["branch"] == "main" and "resumed" not in clean  # a clone without a branch starts clean
        listed = clean["saved_work"]
        assert [s["branch"] for s in listed] == ["fix-greeting"]
        assert listed[0]["commits"] == 1 and listed[0]["last_commit"] == "Fix greeting"

        again = await env.clone("alice", branch="fix-greeting")
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


def test_a_second_issue_in_another_conversation_never_touches_the_first(tmp_path):
    """The bug this design fixes: with one record per repo, starting issue B overwrote issue A."""
    env = Env(tmp_path)

    async def flow():
        a = (await env.clone("alice"))["sandbox_id"]  # conversation 1: issue A
        await env.mgr.create_branch(a, "fix-a")
        await env.mgr.edit_file(a, "a.txt", "hello", "A was here")
        await env.mgr.commit(a, "Fix A")

        b = (await env.clone("alice"))["sandbox_id"]  # conversation 2, same repo: issue B
        assert env.exists(a) and env.exists(b)  # both conversations keep their sandbox
        await env.mgr.create_branch(b, "fix-b")
        await env.mgr.edit_file(b, "b.txt", "one", "B was here")
        await env.mgr.edit_file(a, "b.txt", "one", "A again")  # and A carries on meanwhile
        assert await env.saved() == {("o/r", "fix-a"), ("o/r", "fix-b")}

        env.wipe_disk()
        ra = env.repo((await env.clone("alice", branch="fix-a"))["sandbox_id"])
        rb = env.repo((await env.clone("alice", branch="fix-b"))["sandbox_id"])
        assert (ra / "a.txt").read_text() == "A was here\n" and (ra / "b.txt").read_text() == "A again\n"
        assert (rb / "a.txt").read_text() == "hello\n" and (rb / "b.txt").read_text() == "B was here\n"

    asyncio.run(flow())


def test_two_sandboxes_on_one_branch_never_overwrite_each_other(tmp_path):
    env = Env(tmp_path)

    async def flow():
        first = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(first, "a.txt", "hello", "first")  # on main: saved as 'main'
        second = (await env.clone("alice"))["sandbox_id"]
        out = await env.mgr.edit_file(second, "b.txt", "one", "second")
        assert out["saved"] is False and "create_branch" in out["save_warning"]
        saved = await env.mgr.store.get("alice", "o/r", "main")
        assert "first" in saved["uncommitted_patch"] and "second" not in saved["uncommitted_patch"]

        # A new branch is a new record, so the second sandbox's work is saved from there on.
        out = await env.mgr.create_branch(second, "fix-b")
        assert "save_warning" not in out
        assert await env.saved() == {("o/r", "main"), ("o/r", "fix-b")}

    asyncio.run(flow())


def test_a_branch_name_with_saved_work_is_not_reused_for_new_work(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid, "fix-x")
        other = (await env.clone("alice"))["sandbox_id"]
        with pytest.raises(GitCiError, match="branch='fix-x'"):
            await env.mgr.create_branch(other, "fix-x")
        # Bob has his own records, so the same name is fine for him.
        bob = (await env.clone("bob"))["sandbox_id"]
        assert (await env.mgr.create_branch(bob, "fix-x"))["branch"] == "fix-x"

    asyncio.run(flow())


def test_resuming_a_branch_that_is_open_elsewhere_continues_from_its_latest_work(tmp_path):
    env = Env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        new = await env.clone("alice", branch="fix-greeting")
        assert not env.exists(old)  # one sandbox per branch: the open one was saved, then closed
        assert (env.repo(new["sandbox_id"]) / "b.txt").read_text() == "three\n"

    asyncio.run(flow())


def test_resuming_a_branch_with_nothing_saved_says_what_is(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        with pytest.raises(GitCiError, match="Saved branches: fix-greeting"):
            await env.clone("alice", branch="fix-other")
        with pytest.raises(GitCiError, match="sign in"):
            await env.clone("", branch="fix-greeting")

    asyncio.run(flow())


def test_destroy_saves_first_and_discard_does_not(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        assert await env.mgr.destroy(sid) == {"destroyed": True, "saved": True}
        assert not env.exists(sid)
        again = await env.clone("alice", branch="main")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "a.txt").read_text() == "hi\n"

        throwaway = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(throwaway, "fix-junk")
        await env.mgr.store.delete("alice", "o/r", "fix-junk")
        await env.mgr.destroy(throwaway, discard=True)
        assert not env.exists(throwaway) and ("o/r", "fix-junk") not in await env.saved()

    asyncio.run(flow())


def test_anonymous_sandboxes_are_not_saved(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone())["sandbox_id"]
        await env.mgr.edit_file(sid, "a.txt", "hello", "hi")
        await env.mgr.destroy(sid)
        assert "saved_work" not in await env.clone()
        assert not Path(env.cfg.save_dir).exists() or not any(Path(env.cfg.save_dir).iterdir())

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
        again = await env.clone("alice", branch="main")
        assert again["resumed"]["files_changed"] == ["a.txt"]
        assert not (env.repo(again["sandbox_id"]) / "pkg").exists()

    asyncio.run(flow())


# ---------------------------------------------------------------- stacked branches
def test_a_stacked_branch_targets_its_parent_and_comes_back_whole(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-a")
        await env.mgr.edit_file(sid, "a.txt", "hello", "step one")
        await env.mgr.commit(sid, "Step one")
        assert await env.mgr.pr_base(sid) == {"base": "main"}
        await env.mgr.push_branch(sid, "token")  # fix-a is on GitHub, with its own pull request

        made = await env.mgr.create_branch(sid, "fix-b")
        assert made["stacked_on"] == "fix-a"
        await env.mgr.edit_file(sid, "b.txt", "one", "step two")
        await env.mgr.commit(sid, "Step two")
        assert await env.mgr.pr_base(sid) == {"base": "fix-a"}  # only step two shows in its pull request

        # A third branch on an unpushed parent targets main for now, and says why.
        await env.mgr.create_branch(sid, "fix-c")
        target = await env.mgr.pr_base(sid)
        assert target["base"] == "main" and "fix-b" in target["note"]

        env.wipe_disk()
        again = await env.clone("alice", branch="fix-b")
        assert again["resumed"]["stacked_on"] == "fix-a" and again["resumed"]["commits"] == 2
        repo = env.repo(again["sandbox_id"])
        assert _git(repo, "log", "--format=%s", "-2").split("\n")[:2] == ["Step two", "Step one"]
        assert await env.mgr.pr_base(again["sandbox_id"]) == {"base": "fix-a"}
        listed = (await env.mgr.list_saved("alice"))["saved_work"]
        assert {s["branch"]: s["stacked_on"] for s in listed} == {"fix-a": None, "fix-b": "fix-a", "fix-c": "fix-b"}

    asyncio.run(flow())


def test_the_draft_pr_tool_uses_the_stacked_base():
    tool = next(t for t in asyncio.run(mcp.list_tools()) if t.name == "draft_pr")
    assert "stacked" in tool.description


# ---------------------------------------------------------------- limits
def test_a_user_at_their_branch_limit_must_delete_some_to_save_more(tmp_path):
    env = Env(tmp_path, max_saved_branches=2)

    async def flow():
        for name in ("fix-1", "fix-2"):
            sid = (await env.clone("alice"))["sandbox_id"]
            await env.mgr.create_branch(sid, name)
        third = (await env.clone("alice"))["sandbox_id"]
        out = await env.mgr.create_branch(third, "fix-3")
        assert out["branch"] == "fix-3"  # the branch is made; only saving it is refused
        assert out["saved"] is False and "2 of 2 branches" in out["save_warning"]
        assert "delete_saved_work" in out["save_warning"]
        with pytest.raises(GitCiError, match="not deleted"):
            await env.mgr.destroy(third)  # unsaved work is never thrown away silently
        assert env.exists(third)

        listed = await env.mgr.list_saved("alice", REPO)
        assert (listed["branches_used"], listed["branches_limit"]) == (2, 2)
        await env.mgr.delete_saved("alice", REPO, "fix-1")
        out = await env.mgr.edit_file(third, "a.txt", "hello", "hi")
        assert "save_warning" not in out
        assert await env.saved() == {("o/r", "fix-2"), ("o/r", "fix-3")}
        assert (await env.clone("bob"))["sandbox_id"]  # other users are not affected

    asyncio.run(flow())


def test_a_user_at_their_space_limit_must_delete_some_to_save_more(tmp_path):
    env = Env(tmp_path, max_saved_bytes_per_user=7000)

    async def flow():
        first = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(first, "fix-first")
        (env.repo(first) / "first.txt").write_text("y" * 3000)
        assert "save_warning" not in await env.mgr.edit_file(first, "a.txt", "hello", "hi")

        big = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(big, "fix-big")
        (env.repo(big) / "big.txt").write_text("x" * 5000)
        out = await env.mgr.edit_file(big, "a.txt", "hello", "hey")  # about 3 KB + 5 KB > 7 KB
        assert out["saved"] is False and "MB" in out["save_warning"]
        # The last version of fix-big that fitted is still there; the change is not lost while the sandbox is open.
        assert "big.txt" not in (await env.mgr.store.get("alice", "o/r", "fix-big"))["files"]

        await env.mgr.delete_saved("alice", REPO, "fix-first")
        assert "save_warning" not in await env.mgr.edit_file(big, "b.txt", "one", "two")
        assert "big.txt" in (await env.mgr.store.get("alice", "o/r", "fix-big"))["files"]

    asyncio.run(flow())


def test_finished_pull_requests_free_their_space_by_themselves(tmp_path):
    states = {}

    async def pr_state(url):
        return states.get(url, "open")

    env = Env(tmp_path, pr_state=pr_state, max_saved_branches=1)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-1")
        await env.mgr.record_pr(sid, "https://github.com/o/r/pull/1")
        nxt = (await env.clone("alice"))["sandbox_id"]
        assert (await env.mgr.create_branch(nxt, "fix-2"))["saved"] is False  # full, and #1 is still open
        states["https://github.com/o/r/pull/1"] = "merged"
        assert "save_warning" not in await env.mgr.edit_file(nxt, "a.txt", "hello", "hi")
        assert await env.saved() == {("o/r", "fix-2")}

    asyncio.run(flow())


def test_list_saved_work_drops_finished_work_and_shows_usage(tmp_path):
    async def pr_state(url):
        return "closed" if url.endswith("/1") else "open"

    env = Env(tmp_path, pr_state=pr_state)

    async def flow():
        for name, pr in (("fix-1", "https://github.com/o/r/pull/1"), ("fix-2", "https://github.com/o/r/pull/2")):
            sid = (await env.clone("alice"))["sandbox_id"]
            await env.mgr.create_branch(sid, name)
            await env.mgr.record_pr(sid, pr)
        listed = await env.mgr.list_saved("alice")
        assert [s["branch"] for s in listed["saved_work"]] == ["fix-2"]
        assert listed["saved_work"][0]["pull_request"] == "https://github.com/o/r/pull/2"
        assert (listed["branches_used"], listed["branches_limit"], listed["mb_limit"]) == (1, 15, 100.0)
        assert listed["kept_days_after_last_change"] == 90
        assert (await env.mgr.list_saved("bob"))["saved_work"] == []
        with pytest.raises(GitCiError, match="sign in"):
            await env.mgr.list_saved("")

    asyncio.run(flow())


def test_deleting_saved_work_closes_its_open_sandbox(tmp_path):
    env = Env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        other = (await env.clone("alice"))["sandbox_id"]
        assert await env.mgr.delete_saved("alice", REPO, "fix-greeting") == {
            "deleted": True, "repo": "o/r", "branch": "fix-greeting"}
        assert not env.exists(sid) and env.exists(other)  # or it would save the work right back
        assert await env.saved() == set()
        with pytest.raises(GitCiError, match="no saved work"):
            await env.mgr.delete_saved("alice", REPO, "fix-greeting")
        with pytest.raises(GitCiError, match="no saved work"):
            await env.mgr.delete_saved("bob", REPO, "fix-greeting")  # nobody deletes another user's work

    asyncio.run(flow())


def test_each_user_has_at_most_their_share_of_sandboxes(tmp_path):
    env = Env(tmp_path, max_sandboxes_per_user=2)

    async def flow():
        first = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(first, "fix-1")
        second = (await env.clone("alice"))["sandbox_id"]
        bob = (await env.clone("bob"))["sandbox_id"]
        env.age(first, 60)
        third = (await env.clone("alice"))["sandbox_id"]
        assert not env.exists(first)  # her longest idle one was saved and closed
        assert env.exists(second) and env.exists(third) and env.exists(bob)
        assert ("o/r", "fix-1") in await env.saved()

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
        again = await env.clone("alice", branch="main")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "a.txt").read_text() == "hi\n"

    asyncio.run(flow())


def test_a_change_that_cannot_be_saved_says_so_and_its_sandbox_is_kept(tmp_path):
    env = Env(tmp_path, store=BrokenStore(), max_sandboxes=1, save_grace_seconds=3000)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        out = await env.mgr.edit_file(sid, "a.txt", "hello", "hi")  # the change works; only the save failed
        assert out["saved"] is False and "lost if the server restarts" in out["save_warning"]
        with pytest.raises(GitCiError, match="could not be saved"):
            await env.mgr.destroy(sid)
        env.age(sid, 900)
        with pytest.raises(GitCiError, match="in use"):
            await env.clone("bob")  # not reclaimed either
        env.age(sid, 1200)
        with pytest.raises(GitCiError, match="in use"):
            await env.clone("bob")  # nor deleted as abandoned, within the grace period
        assert env.exists(sid) and (env.repo(sid) / "a.txt").read_text() == "hi\n"

        env.age(sid, 1000)  # idle past the grace period: deleted, so the pool cannot stay stuck
        assert (await env.clone("bob"))["sandbox_id"]
        assert not env.exists(sid)

    asyncio.run(flow())


def test_work_too_large_to_save_keeps_its_sandbox(tmp_path):
    env = Env(tmp_path, max_save_bytes=50)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        (env.repo(sid) / "big.txt").write_text("x" * 500)
        with pytest.raises(GitCiError, match="larger than 50 bytes"):
            await env.mgr.destroy(sid)
        assert env.exists(sid)

    asyncio.run(flow())


# ---------------------------------------------------------------- pull requests
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
        again = await env.clone("alice", branch="fix-greeting")
        assert again["resumed"]["restored"] is False
        assert again["resumed"]["pull_request_state"] == state
        assert again["branch"] == "main"
        assert await env.mgr.store.get("alice", "o/r", "fix-greeting") is None  # done with: dropped

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

        again = await env.clone("alice", branch="fix-greeting")
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
        data = await env.mgr.store.get("alice", "o/r", "main")
        data["base_sha"] = "f" * 40  # and the old base is gone (force-push)
        await env.mgr.store.put("alice", "o/r", "main", data)

        again = await env.clone("alice", branch="main")
        assert again["resumed"]["restored"] is False and "kept" in again["resumed"]["note"]
        repo = env.repo(again["sandbox_id"])
        assert again["branch"] == "main" and _git(repo, "status", "--porcelain").strip() == ""
        assert (repo / "a.txt").read_text() == "completely different\n"
        assert await env.mgr.store.get("alice", "o/r", "main") is not None

    asyncio.run(flow())


# ---------------------------------------------------------------- inputs and tools
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


def test_saved_work_tools_take_a_system_set_owner():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name, params in (("sandbox_clone", {"branch", "owner"}), ("list_saved_work", {"owner"}),
                         ("delete_saved_work", {"repo_url", "branch", "owner"})):
        schema = getattr(tools[name], "inputSchema", None) or tools[name].input_schema
        assert params <= set(schema["properties"]), name
        assert "set by the system" in tools[name].description
    clone = getattr(tools["sandbox_clone"], "inputSchema", None) or tools["sandbox_clone"].input_schema
    assert "fresh" not in clone["properties"]
    destroy = getattr(tools["destroy_sandbox"], "inputSchema", None) or tools["destroy_sandbox"].input_schema
    assert "discard" in destroy["properties"]


# ---------------------------------------------------------------- stores
def test_file_store_keeps_one_record_per_branch_and_expires_old_ones(tmp_path):
    store = FileStore(str(tmp_path), keep_days=90)

    async def flow():
        await store.put("alice", "o/r", "fix-a", {"saved_at": time.time()})
        await store.put("alice", "o/r", "fix-b", {"saved_at": time.time()})
        assert (await store.get("alice", "o/r", "fix-a"))["branch"] == "fix-a"
        assert await store.get("bob", "o/r", "fix-a") is None
        assert sorted(r["branch"] for r in await store.list("alice")) == ["fix-a", "fix-b"]
        assert all(r["bytes"] > 0 for r in await store.list("alice"))
        await store.put("alice", "o/r", "fix-a", {"saved_at": time.time() - 91 * 86400})
        assert await store.get("alice", "o/r", "fix-a") is None
        assert [r["branch"] for r in await store.list("alice")] == ["fix-b"]
        await store.delete("alice", "o/r", "fix-b")
        assert await store.list("alice") == []

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

    store = PostgresStore(postgres, keep_days=90)

    async def flow():
        with psycopg.connect(store.url, autocommit=True) as conn:
            conn.execute("DROP TABLE IF EXISTS gitci_saved_work")
        store._ready = False
        assert await store.get("alice", "o/r", "fix-a") is None
        await store.put("alice", "o/r", "fix-a", {"commits_patch": "x\r\n\x7f"})
        await store.put("alice", "o/r", "fix-b", {"last_commit": "one"})
        await store.put("alice", "o/r", "fix-b", {"last_commit": "two"})  # upsert
        assert (await store.get("alice", "o/r", "fix-a"))["commits_patch"] == "x\r\n\x7f"
        assert (await store.get("alice", "o/r", "fix-b"))["last_commit"] == "two"
        assert await store.get("bob", "o/r", "fix-a") is None
        listed = await store.list("alice")
        assert [r["branch"] for r in listed] == ["fix-a", "fix-b"] and all(r["bytes"] > 0 for r in listed)
        with psycopg.connect(store.url, autocommit=True) as conn:
            conn.execute("UPDATE gitci_saved_work SET saved_at = now() - interval '91 days' WHERE branch = 'fix-a'")
        assert await store.get("alice", "o/r", "fix-a") is None
        assert [r["branch"] for r in await store.list("alice")] == ["fix-b"]
        await store.delete("alice", "o/r", "fix-b")
        assert await store.list("alice") == []

    asyncio.run(flow())


def test_resume_through_postgres(tmp_path, postgres):
    env = Env(tmp_path, store=PostgresStore(postgres, keep_days=90))

    async def flow():
        for r in await env.mgr.store.list("alice"):
            await env.mgr.store.delete("alice", r["repo"], r["branch"])
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        await env.half_done_fix((await env.clone("alice"))["sandbox_id"], "fix-other")
        env.wipe_disk()
        again = await env.clone("alice", branch="fix-greeting")
        assert again["resumed"]["restored"] is True
        assert (env.repo(again["sandbox_id"]) / "b.txt").read_text() == "three\n"
        assert {s["branch"] for s in (await env.mgr.list_saved("alice"))["saved_work"]} == {"fix-greeting", "fix-other"}
        for name in ("fix-greeting", "fix-other"):
            await env.mgr.store.delete("alice", "o/r", name)

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
