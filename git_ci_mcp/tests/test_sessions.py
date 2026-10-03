"""Two sessions on one branch (a second tab, or an earlier mission still running) and the periodic
autosave. The first must never end with the two sessions taking the branch from each other, or with
one overwriting the other's work; the second must keep work safe between tool calls."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gitci_mcp.sandbox import GitCiError
from gitci_mcp.saved import FileStore
from test_saved_work import Env, REPO, _git


def _env(tmp_path, **cfg):
    return Env(tmp_path, takeover_idle_seconds=30, **cfg)


# ---------------------------------------------------------------- two sessions, one branch
def test_a_new_session_takes_over_and_the_old_one_is_told_to_stop(tmp_path):
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        env.age(old, 100)  # nobody is working in it right now
        new = await env.clone("alice", branch="fix-greeting")
        assert new["resumed"]["restored"] is True and not env.exists(old)
        assert (env.repo(new["sandbox_id"]) / "b.txt").read_text() == "three\n"  # the latest work came along

        # Every way the old tab can still reach for its sandbox says why it is gone and what not to do.
        for call in (env.mgr.status(old), env.mgr.read_file(old, "a.txt"), env.mgr.edit_file(old, "a.txt", "hello", "x"),
                     env.mgr.run_tests(old, "pytest -q"), env.mgr.commit(old, "msg"), env.mgr.diff(old)):
            with pytest.raises(GitCiError) as caught:
                await call
            text = str(caught.value)
            assert "took over" in text and "fix-greeting" in text and "Do not call sandbox_clone" in text
            assert "Unknown sandbox id" not in text and new["sandbox_id"] not in text

    asyncio.run(flow())


def test_a_branch_in_use_is_not_taken_from_the_session_working_on_it(tmp_path):
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)  # used a moment ago
        with pytest.raises(GitCiError) as caught:
            await env.clone("alice", branch="fix-greeting")
        text = str(caught.value)
        assert "open in another session" in text and "Do not retry right away" in text and "seconds" in text
        assert old not in text  # the refused session must not be handed the other one's sandbox
        # The session that was working carries on, untouched.
        assert env.exists(old)
        assert (await env.mgr.edit_file(old, "b.txt", "three", "four"))["edited"] == "b.txt"
        assert (await env.mgr.store.get("alice", "o/r", "fix-greeting"))["uncommitted_patch"].count("four") == 1

    asyncio.run(flow())


def test_the_old_session_cannot_take_the_branch_back_from_the_new_one(tmp_path):
    """The loop seen in the field: each tab's assistant re-cloned the branch to recover, closing the other."""
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        env.age(old, 100)
        new = (await env.clone("alice", branch="fix-greeting"))["sandbox_id"]
        await env.mgr.edit_file(new, "b.txt", "three", "newest")  # the new session is working

        with pytest.raises(GitCiError, match="open in another session"):
            await env.clone("alice", branch="fix-greeting")  # the old tab clones again to "recover"
        assert env.exists(new)
        assert "newest" in (await env.mgr.store.get("alice", "o/r", "fix-greeting"))["uncommitted_patch"]

    asyncio.run(flow())


def test_a_session_taken_over_cannot_overwrite_the_new_sessions_saves(tmp_path):
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        env.age(old, 100)
        new = (await env.clone("alice", branch="fix-greeting"))["sandbox_id"]
        await env.mgr.edit_file(new, "b.txt", "three", "newest")
        before = await env.mgr.store.get("alice", "o/r", "fix-greeting")

        # A change still running in the old tab when it was taken over: nothing of it is saved over the new work.
        out = await env.mgr._autosave(old)
        assert out["saved"] is False and "took over" in out["save_warning"]
        assert await env.mgr.store.get("alice", "o/r", "fix-greeting") == before

    asyncio.run(flow())


def test_a_taken_over_sandbox_cleans_up_without_error_but_an_unknown_one_still_fails(tmp_path):
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        env.age(old, 100)
        await env.clone("alice", branch="fix-greeting")
        out = await env.mgr.destroy(old)  # the old mission's last step: nothing to close, nothing lost
        assert out["destroyed"] is True and "took over" in out["note"]
        with pytest.raises(GitCiError, match="Unknown sandbox id"):
            await env.mgr.destroy("0123456789ab")

    asyncio.run(flow())


def test_an_expired_sandbox_is_not_reported_as_taken_over(tmp_path):
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        env.age(sid, 5000)
        await env.clone("alice")  # sweeping saves and removes it, with no note
        assert not env.exists(sid)
        with pytest.raises(GitCiError) as caught:
            await env.mgr.status(sid)
        assert "Unknown sandbox id" in str(caught.value) and "took over" not in str(caught.value)

    asyncio.run(flow())


def test_deleting_saved_work_tells_its_open_session_why_it_closed(tmp_path):
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(sid)
        await env.mgr.delete_saved("alice", REPO, "fix-greeting")
        with pytest.raises(GitCiError, match="deleted at the user's request"):
            await env.mgr.status(sid)

    asyncio.run(flow())


def test_the_notes_about_closed_sandboxes_are_dropped_after_a_day(tmp_path):
    env = _env(tmp_path)

    async def flow():
        old = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(old)
        env.age(old, 100)
        await env.clone("alice", branch="fix-greeting")
        note = Path(env.cfg.sandbox_root) / ".closed" / f"{old}.json"
        assert note.is_file()
        then = note.stat().st_mtime - 2 * 86400
        os.utime(note, (then, then))
        await env.clone("bob")
        assert not note.exists()

    asyncio.run(flow())


def test_sessions_of_different_users_never_meet(tmp_path):
    env = _env(tmp_path)

    async def flow():
        a = (await env.clone("alice"))["sandbox_id"]
        await env.half_done_fix(a)
        b = (await env.clone("bob"))["sandbox_id"]
        await env.half_done_fix(b)  # the same branch name, a different user: not a conflict
        assert env.exists(a) and env.exists(b)
        with pytest.raises(GitCiError, match="no saved work"):
            await env.clone("carol", branch="fix-greeting")

    asyncio.run(flow())


# ---------------------------------------------------------------- periodic autosave
def test_autosave_saves_work_made_between_tool_calls(tmp_path):
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-x")
        (env.repo(sid) / "notes.txt").write_text("written by something other than a tool call\n")
        (env.repo(sid) / "a.txt").write_text("edited directly\n")
        assert "notes.txt" not in (await env.mgr.store.get("alice", "o/r", "fix-x"))["uncommitted_patch"]

        assert await env.mgr.autosave_all() == 1
        patch = (await env.mgr.store.get("alice", "o/r", "fix-x"))["uncommitted_patch"]
        assert "notes.txt" in patch and "edited directly" in patch

        # And it comes back from that record.
        env.wipe_disk()
        again = await env.clone("alice", branch="fix-x")
        assert (env.repo(again["sandbox_id"]) / "notes.txt").read_text().startswith("written by")

    asyncio.run(flow())


def test_autosave_skips_a_sandbox_that_has_not_changed(tmp_path):
    env = _env(tmp_path)
    puts = []

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-x")
        original = env.mgr.store.put

        async def counting_put(*args):
            puts.append(args[2])
            return await original(*args)

        env.mgr.store.put = counting_put
        (env.repo(sid) / "a.txt").write_text("changed\n")
        assert await env.mgr.autosave_all() == 1
        assert await env.mgr.autosave_all() == 0 and await env.mgr.autosave_all() == 0
        assert puts == ["fix-x"]  # one write, not one per round
        (env.repo(sid) / "a.txt").write_text("changed again\n")  # the same file, new content
        assert await env.mgr.autosave_all() == 1 and puts == ["fix-x", "fix-x"]

    asyncio.run(flow())


def test_autosave_does_not_count_as_use_of_the_sandbox(tmp_path):
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]  # a clean clone: the first save claims 'main' in meta.json
        (env.repo(sid) / "a.txt").write_text("edited\n")
        meta = Path(env.cfg.sandbox_root) / sid / "meta.json"
        before = meta.stat().st_mtime_ns
        assert await env.mgr.autosave_all() == 1
        assert ("o/r", "main") in await env.saved()
        assert meta.stat().st_mtime_ns == before  # still idle, so it is still reclaimable

    asyncio.run(flow())


def test_autosave_ignores_anonymous_sandboxes(tmp_path):
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone(""))["sandbox_id"]
        (env.repo(sid) / "a.txt").write_text("edited\n")
        assert await env.mgr.autosave_all() == 0
        assert await env.saved("") == set()

    asyncio.run(flow())


def test_autosave_leaves_the_repos_own_index_alone(tmp_path):
    """New files are found through a scratch index, so a commit running at the same time cannot be
    blocked by the save, and nothing is left staged."""
    env = _env(tmp_path)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-x")
        (env.repo(sid) / "new.txt").write_text("new\n")
        await env.mgr.autosave_all()
        assert _git(env.repo(sid), "status", "--porcelain").strip() == "?? new.txt"
        assert not (Path(env.cfg.sandbox_root) / sid / "save.index").exists()

        for n in range(5):  # saves and commits at the same moment never fail each other
            (env.repo(sid) / "a.txt").write_text(f"round {n}\n")
            committed, saved = await asyncio.gather(env.mgr.commit(sid, f"round {n}"), env.mgr.autosave_all())
            assert committed["commit"]
        await env.mgr.autosave_all()
        assert (await env.mgr.store.get("alice", "o/r", "fix-x"))["commits"] == 5

    asyncio.run(flow())


class FlakyStore(FileStore):
    down = False

    async def put(self, owner, repo, branch, data):
        if self.down:
            raise ConnectionError("database is down")
        return await super().put(owner, repo, branch, data)


def test_autosave_survives_a_broken_store_and_catches_up_when_it_recovers(tmp_path):
    store = FlakyStore(str(tmp_path / "saved"), 90)
    env = Env(tmp_path, store=store, takeover_idle_seconds=30)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-x")
        (env.repo(sid) / "a.txt").write_text("edited\n")
        store.down = True
        assert await env.mgr.autosave_all() == 0  # no exception, and the sandbox is untouched
        assert env.exists(sid) and (env.repo(sid) / "a.txt").read_text() == "edited\n"
        store.down = False
        assert await env.mgr.autosave_all() == 1  # unchanged since, but it was never saved, so it is tried again
        assert "edited" in (await store.get("alice", "o/r", "fix-x"))["uncommitted_patch"]

    asyncio.run(flow())


def test_the_autosave_loop_runs_by_itself(tmp_path):
    env = Env(tmp_path, autosave_seconds=0.05, takeover_idle_seconds=30)

    async def flow():
        sid = (await env.clone("alice"))["sandbox_id"]
        await env.mgr.create_branch(sid, "fix-x")
        (env.repo(sid) / "later.txt").write_text("saved without anyone asking\n")
        for _ in range(60):
            await asyncio.sleep(0.1)
            if "later.txt" in (await env.mgr.store.get("alice", "o/r", "fix-x"))["uncommitted_patch"]:
                break
        else:
            pytest.fail("the periodic save never ran")
        assert env.mgr._autosaver is not None and not env.mgr._autosaver.done()

    asyncio.run(flow())


def test_autosave_can_be_turned_off(tmp_path):
    env = Env(tmp_path, autosave_seconds=0)

    async def flow():
        await env.clone("alice")
        assert env.mgr._autosaver is None

    asyncio.run(flow())
