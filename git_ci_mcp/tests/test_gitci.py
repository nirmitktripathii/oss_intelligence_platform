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
