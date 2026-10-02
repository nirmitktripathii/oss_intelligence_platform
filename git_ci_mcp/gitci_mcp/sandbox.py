"""Sandboxed git operations. Every function here validates its inputs and confines itself to one
directory under the sandbox root; the MCP layer in server.py is a thin wrapper over this."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .config import Settings, settings as default_settings
from .saved import FileStore, PostgresStore, SavedStore, size_of

logger = logging.getLogger(__name__)


class GitCiError(Exception):
    """A problem the caller can act on. The message is safe to show to the user."""


class SaveRefused(GitCiError):
    """Work that will not be saved until the user does something (frees space, picks another branch)."""


_REPO_URL = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")
_SANDBOX_ID = re.compile(r"^[0-9a-f]{12}$")
_LOGIN = re.compile(r"^[A-Za-z0-9-]{1,39}$")
# Never part of saved work: bytecode and test caches that running the tests leaves behind.
_NOT_WORK = (":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/*.pyc", ":(exclude,glob)**/.pytest_cache/**")
_DIFF_PATH = re.compile(r"^(?:---|\+\+\+) (?:[ab]/)?(.+?)(?:\t.*)?$")
_DIFF_GIT = re.compile(r"^diff --git a/(.+) b/(.+)$")

# Environment the test command is allowed to see. Secrets (tokens, cloud keys) are not here.
_SAFE_ENV = ("PATH", "PATHEXT", "SYSTEMROOT", "COMSPEC", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE",
             "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL")


def parse_repo_url(url: str) -> Tuple[str, str]:
    m = _REPO_URL.match((url or "").strip())
    if not m:
        raise GitCiError("Only https://github.com/<owner>/<repo> URLs are supported.")
    return m.group(1), m.group(2)


def check_ref(ref: str, what: str = "branch") -> str:
    if not _REF.match(ref or "") or ".." in ref or ref.endswith((".", "/", ".lock")) or "//" in ref:
        raise GitCiError(f"'{ref}' is not a valid {what} name.")
    return ref


def _bad_patch_path(path: str) -> bool:
    if not path or path == "/dev/null":
        return False
    p = path.replace("\\", "/")
    parts = [x for x in p.split("/") if x]
    return (
        p.startswith("/") or bool(re.match(r"^[A-Za-z]:", p)) or "\x00" in p
        or any(x == ".." or x.lower() == ".git" for x in parts)
    )


def validate_patch(diff: str, max_bytes: int) -> List[str]:
    """Reject anything that could write outside the work tree or into .git; return touched paths."""
    if not diff or not diff.strip():
        raise GitCiError("The patch is empty.")
    if len(diff.encode("utf-8")) > max_bytes:
        raise GitCiError(f"The patch is larger than {max_bytes} bytes.")
    if "GIT binary patch" in diff:
        raise GitCiError("Binary patches are not supported.")
    paths: List[str] = []
    for line in diff.splitlines():
        for pattern in (_DIFF_GIT, _DIFF_PATH):
            m = pattern.match(line)
            if m:
                for group in m.groups():
                    if _bad_patch_path(group):
                        raise GitCiError(f"The patch touches a path that is not allowed: {group!r}.")
                    if group != "/dev/null":
                        paths.append(group)
    if not paths:
        raise GitCiError("That does not look like a unified diff (no file headers).")
    return sorted(set(paths))


def remove_tree(path: Path) -> None:
    """Delete a directory, including git's read-only object files (which plain rmtree cannot remove
    on Windows). Anything that still cannot be removed is left; the caller does not depend on it."""
    def retry(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def _when(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(ts))


def make_store(cfg: Settings) -> SavedStore:
    if cfg.save_database_url:
        return PostgresStore(cfg.save_database_url, cfg.save_keep_days)
    root = Path(cfg.sandbox_root)
    return FileStore(cfg.save_dir or str(root.with_name(root.name + "-saved")), cfg.save_keep_days)


class SandboxManager:
    def __init__(self, cfg: Settings = default_settings, store: Optional[SavedStore] = None,
                 pr_state: Optional[Callable[[str], Awaitable[str]]] = None):
        self.cfg = cfg
        self.root = Path(cfg.sandbox_root)
        # A signed-in user's unfinished work lives here between sandboxes (see saved.py).
        self.store = store if store is not None else make_store(cfg)
        # Looks up a pull request ("open", "merged", "closed" or "unknown"), so work that was already
        # merged or closed is not put back.
        self.pr_state = pr_state
        self._tests = asyncio.Semaphore(max(1, cfg.max_concurrent_tests))

    # ---------------------------------------------------------------- plumbing
    def _dir(self, sandbox_id: str) -> Path:
        if not _SANDBOX_ID.match(sandbox_id or ""):
            raise GitCiError(
                "That is not a sandbox id. Use the sandbox_id that sandbox_clone returned (12 letters and digits); "
                "do not guess one."
            )
        d = self.root / sandbox_id
        meta = d / "meta.json"
        if not meta.is_file():
            raise GitCiError(
                "Unknown sandbox id. It may have expired or been reclaimed after sitting idle. "
                "Run sandbox_clone again to get a new one: its result lists your saved work, and passing "
                "that branch to sandbox_clone puts the work back."
            )
        try:
            os.utime(meta)  # every use counts as activity, so only abandoned sandboxes look idle
        except OSError:
            pass
        return d

    def _meta(self, sandbox_id: str) -> Dict[str, Any]:
        return json.loads((self._dir(sandbox_id) / "meta.json").read_text(encoding="utf-8"))

    def _repo(self, sandbox_id: str) -> Path:
        return self._dir(sandbox_id) / "repo"

    def _git_env(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        env = {k: os.environ[k] for k in _SAFE_ENV if k in os.environ}
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = "echo"
        env.update(extra or {})
        return env

    async def _git(self, cwd: Optional[Path], *args: str, stdin: Optional[str] = None,
                   extra_env: Optional[Dict[str, str]] = None, timeout: int = 120,
                   secret: str = "") -> str:
        hooks = self.root / ".nohooks"
        hooks.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "-c", f"core.hooksPath={hooks}", "-c", "protocol.ext.allow=never", *args]

        def run() -> subprocess.CompletedProcess:
            # Bytes in and out: text mode would turn every "\n" of a patch into "\r\n" on Windows.
            return subprocess.run(
                cmd, cwd=str(cwd) if cwd else None, input=stdin.encode("utf-8") if stdin is not None else None,
                capture_output=True, timeout=timeout, env=self._git_env(extra_env),
            )

        try:
            done = await asyncio.to_thread(run)
        except subprocess.TimeoutExpired:
            raise GitCiError(f"git {args[0]} timed out after {timeout}s.")
        except FileNotFoundError:
            raise GitCiError("git is not installed on the server.")
        out = done.stdout.decode("utf-8", errors="replace")
        if done.returncode != 0:
            msg = (done.stderr.decode("utf-8", errors="replace") or out).strip()
            if secret:
                msg = msg.replace(secret, "***")
            raise GitCiError(f"git {args[0]} failed: {msg[-600:]}")
        return out

    def _cap(self, text: str) -> str:
        cap = self.cfg.output_cap_bytes
        return text if len(text) <= cap else "...(truncated)...\n" + text[-cap:]

    def _live(self) -> List[Tuple[float, Path, Dict[str, Any]]]:
        """(idle seconds, directory, meta) of every sandbox, longest idle first."""
        if not self.root.is_dir():
            return []
        now, out = time.time(), []
        for d in self.root.iterdir():
            meta = d / "meta.json"
            if meta.is_file():
                try:
                    out.append((now - meta.stat().st_mtime, d, json.loads(meta.read_text(encoding="utf-8"))))
                except (OSError, ValueError):
                    continue
        return sorted(out, key=lambda item: item[0], reverse=True)

    async def _sweep(self) -> None:
        """Make room for one more sandbox: delete the abandoned ones, and if the pool is still full,
        the one idle longest (when it has been idle long enough). Otherwise ask the caller to wait.

        Nothing is deleted before its owner's work is saved. A sandbox whose work cannot be saved is
        kept, but only until it has been idle for the grace period. Last use is the mtime of meta.json."""
        self.root.mkdir(parents=True, exist_ok=True)
        live = []
        for idle, d, _meta in self._live():
            if idle > self.cfg.sandbox_ttl_seconds:
                if await self._delete_saving(d):
                    continue
                if idle > self.cfg.save_grace_seconds:
                    logger.warning("[GITCI] deleting sandbox %s unsaved after the grace period", d.name)
                    await asyncio.to_thread(remove_tree, d)
                    continue
            live.append((idle, d))
        if len(live) < self.cfg.max_sandboxes:
            return
        for idle, d in live:
            if idle < self.cfg.sandbox_reclaim_seconds:
                break
            if await self._delete_saving(d):
                return
        minutes = max(1, round((self.cfg.sandbox_reclaim_seconds - live[0][0]) / 60))
        raise GitCiError(
            f"All {self.cfg.max_sandboxes} sandboxes are in use by other missions right now. Try again in "
            f"about {minutes} minute(s); one is freed once it has been idle that long. You cannot see or "
            "free other people's sandboxes, so do not try to destroy any."
        )

    # ---------------------------------------------------------------- saved progress
    # One saved record per user, repo and branch. A sandbox writes only the record of the branch it is
    # on, and only a record it created or restored ("owns"), so work on one issue never overwrites
    # work on another, even from a clean clone of the same repo in another conversation.
    async def _delete_saving(self, d: Path) -> bool:
        """Save the owner's work, then delete the sandbox. False (and nothing deleted) if saving failed."""
        try:
            await self._save(d)
        except Exception as exc:
            logger.warning("[GITCI] keeping sandbox %s: could not save its work (%s)", d.name, type(exc).__name__)
            return False
        await asyncio.to_thread(remove_tree, d)
        return True

    async def _save(self, d: Path) -> bool:
        """Save a signed-in owner's work in sandbox directory ``d``. Returns False when there is
        nothing to save (no owner, or no change from the base). Raises if saving fails."""
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        owner = meta.get("user")
        if not owner:
            return False
        repo = d / "repo"
        base_sha = meta["base_sha"]
        branch = (await self._git(repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
        # Commits already pushed are on GitHub; save only what came after, so a resumed branch keeps
        # the same commits and pushing it again is a fast-forward.
        pushed_sha = meta.get("pushed", {}).get(branch, "")
        patch_base = pushed_sha or base_sha
        commits = int((await self._git(repo, "rev-list", "--count", f"{base_sha}..HEAD")).strip() or 0)
        unpushed = int((await self._git(repo, "rev-list", "--count", f"{patch_base}..HEAD")).strip() or 0)
        commits_patch = ""
        if unpushed:
            commits_patch = await self._git(repo, "format-patch", "--stdout", "--binary", f"{patch_base}..HEAD")
        await self._git(repo, "add", "-N", "--", ".", *_NOT_WORK)
        uncommitted = await self._git(repo, "diff", "HEAD", "--binary", "--", ".", *_NOT_WORK)
        if branch == meta["base"] and not commits and not uncommitted.strip():
            return False
        if len(commits_patch) + len(uncommitted) > self.cfg.max_save_bytes:
            raise SaveRefused(f"The work on '{branch}' is larger than {self.cfg.max_save_bytes} bytes, so it "
                              "cannot be saved and would be lost if the server restarts.")
        changed = (await self._git(repo, "diff", "--name-only", base_sha, "--", ".", *_NOT_WORK)).split()
        last = (await self._git(repo, "log", "-1", "--format=%s")).strip() if commits else ""
        key = meta["key"]
        data = {
            "base": meta["base"], "base_sha": base_sha, "commits": commits, "last_commit": last,
            "parent": meta.get("parents", {}).get(branch, ""), "pushed_sha": pushed_sha,
            "commits_patch": commits_patch, "uncommitted_patch": uncommitted, "files": sorted(set(changed)),
            "pr_url": meta.get("prs", {}).get(branch, ""), "saved_at": time.time(),
        }
        owns = meta.get("owns", [])
        if branch not in owns and await self.store.get(owner, key, branch) is not None:
            if branch == meta["base"]:
                raise SaveRefused(
                    f"These changes are not saved: you already have saved work on '{branch}' from earlier. "
                    f"Create a branch (create_branch) to have them saved, or resume the earlier work with "
                    f"sandbox_clone(branch='{branch}')."
                )
            raise SaveRefused(
                f"You already have saved work on branch '{branch}' from another conversation, so this sandbox "
                f"does not overwrite it. Resume it with sandbox_clone(branch='{branch}'), or use another name."
            )
        await self._check_space(owner, key, branch, data)
        await self.store.put(owner, key, branch, data)
        if branch not in owns:
            meta["owns"] = owns + [branch]
            (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return True

    async def _check_space(self, owner: str, key: str, branch: str, data: Dict[str, Any]) -> None:
        """Refuse a save that would take the owner past their branch count or space, after first
        dropping their records whose pull request is finished."""
        others = [r for r in await self.store.list(owner) if (r["repo"], r["branch"]) != (key, branch)]
        need = size_of({**data, "repo": key, "branch": branch})

        def full() -> bool:
            return (len(others) >= self.cfg.max_saved_branches
                    or sum(r["bytes"] for r in others) + need > self.cfg.max_saved_bytes_per_user)

        if full():
            others = await self._drop_finished(owner, others)
        if full():
            used = sum(r["bytes"] for r in others) / 1e6
            raise SaveRefused(
                f"Your saved work is full ({len(others)} of {self.cfg.max_saved_branches} branches, "
                f"{used:.1f} of {self.cfg.max_saved_bytes_per_user / 1e6:.0f} MB), so this is not saved and would "
                "be lost if the server restarts. Ask the user which saved work to delete (list_saved_work, then "
                "delete_saved_work)."
            )

    async def _finished(self, record: Dict[str, Any]) -> str:
        """"merged" or "closed" when the record's pull request is done with, else ""."""
        if not record.get("pr_url") or not self.pr_state:
            return ""
        try:
            state = await self.pr_state(record["pr_url"])
        except Exception:
            return ""
        return state if state in ("merged", "closed") else ""

    async def _drop_finished(self, owner: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Delete the records whose pull request was merged or closed; return the rest."""
        kept = []
        for record in records:
            if await self._finished(record):
                await self.store.delete(owner, record["repo"], record["branch"])
            else:
                kept.append(record)
        return kept

    async def _autosave(self, sandbox_id: str) -> Dict[str, Any]:
        """Save after a change. Never raises: the change itself worked. A failure is returned as a
        warning for the tool result, and the sandbox is not deleted until a save succeeds."""
        try:
            await self._save(self.root / sandbox_id)
            return {}
        except SaveRefused as exc:
            return {"saved": False, "save_warning": str(exc)}
        except Exception as exc:
            logger.warning("[GITCI] could not save sandbox %s (%s)", sandbox_id, type(exc).__name__)
            return {"saved": False, "save_warning": "This change is not saved yet (saving is unavailable right "
                    "now); it is tried again after every change. Until then it would be lost if the server restarts."}

    @staticmethod
    def _holds(meta: Dict[str, Any], user: str, key: str, branch: str) -> bool:
        """Whether a sandbox is on ``branch`` and is the one that saves it."""
        return ((meta.get("user"), meta.get("key"), meta.get("branch")) == (user, key, branch)
                and branch in meta.get("owns", []))

    async def _retire(self, user: str, key: str, branch: str) -> None:
        """One sandbox per user per branch: save and delete the one already on this branch, so the
        new clone carries on from it instead of two copies of one branch drifting apart."""
        for _idle, d, m in self._live():
            if self._holds(m, user, key, branch) and not await self._delete_saving(d):
                raise GitCiError(f"Your open sandbox on '{branch}' could not be saved, so it was kept. "
                                 "Try again in a minute.")

    async def _make_room_for(self, user: str) -> None:
        """Keep a user within their share of the pool: past it, save and close their own sandbox
        that has been idle longest."""
        mine = [d for _idle, d, m in self._live() if m.get("user") == user]
        if len(mine) < self.cfg.max_sandboxes_per_user:
            return
        for d in mine:
            if await self._delete_saving(d):
                return
        raise GitCiError(f"You already have {len(mine)} sandboxes open and none of their work could be saved, "
                         "so none was closed. Try again in a few minutes.")

    async def _restore(self, sandbox_id: str, owner: str, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Put one saved branch back into a fresh clone, unless its pull request is finished."""
        branch = data["branch"]
        pr_url = data.get("pr_url") or ""
        state = await self._finished(data)
        if state:
            # Done with: the branch is on GitHub anyway. Start clean.
            await self.store.delete(owner, key, branch)
            return {"restored": False, "branch": branch, "pull_request": pr_url, "pull_request_state": state,
                    "note": f"The work on '{branch}' is in a pull request that was {state}, so its saved copy "
                            "was deleted and this sandbox starts clean."}
        d = self.root / sandbox_id
        repo = d / "repo"
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        base_sha, base_moved = data["base_sha"], False
        pushed_sha = data.get("pushed_sha") or ""
        ident: List[str] = []
        if self.cfg.author_name and self.cfg.author_email:
            ident = ["-c", f"user.name={self.cfg.author_name}", "-c", f"user.email={self.cfg.author_email}"]
        try:
            if pushed_sha:
                # Continue from the branch as GitHub has it.
                await self._git(repo, "fetch", "--depth", "50", "origin", f"refs/heads/{branch}", timeout=60)
                await self._git(repo, "switch", "-c", branch, pushed_sha)
            else:
                try:
                    await self._git(repo, "cat-file", "-e", f"{base_sha}^{{commit}}")
                except GitCiError:
                    try:
                        await self._git(repo, "fetch", "--depth", "50", "origin", base_sha, timeout=60)
                    except GitCiError:
                        base_sha, base_moved = meta["base_sha"], True
                if branch != meta["base"]:
                    await self._git(repo, "switch", "-c", branch, base_sha)
                else:
                    await self._git(repo, "reset", "--hard", base_sha)
            if data.get("commits_patch"):
                await self._git(repo, *ident, "am", "--3way", "--keep-cr", stdin=data["commits_patch"])
            if data.get("uncommitted_patch", "").strip():
                await self._git(repo, "apply", "--binary", "-", stdin=data["uncommitted_patch"])
        except GitCiError as exc:
            # Leave a clean clone and keep the saved work for another try.
            for args in (("am", "--abort"), ("reset", "--hard"), ("clean", "-fd"), ("switch", "-f", meta["base"]),
                         ("reset", "--hard", meta["base_sha"])):
                try:
                    await self._git(repo, *args)
                except GitCiError:
                    pass
            logger.warning("[GITCI] could not restore saved work in %s: %s", sandbox_id, str(exc)[:200])
            return {"restored": False, "branch": branch,
                    "note": f"The saved work on '{branch}' could not be put back on the current code, so this "
                            "sandbox starts clean. The saved work is kept; tell the user."}
        parent = data.get("parent") or ""
        meta.update(base_sha=base_sha, branch=branch, owns=[branch],
                    parents={branch: parent} if parent else {},
                    pushed={branch: pushed_sha} if pushed_sha else {},
                    prs={branch: pr_url} if pr_url else {})
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        status = (await self._git(repo, "status", "--porcelain")).splitlines()
        return {
            "restored": True, "branch": branch, "stacked_on": parent or None, "commits": data.get("commits", 0),
            "uncommitted_files": [line[3:] for line in status], "files_changed": data.get("files", []),
            "saved_at": _when(data.get("saved_at", 0)), "pull_request": pr_url or None, "base_moved": base_moved,
        }

    @staticmethod
    def _summary(record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "repo": record["repo"], "branch": record["branch"], "stacked_on": record.get("parent") or None,
            "commits": record.get("commits", 0), "last_commit": record.get("last_commit") or None,
            "files_changed": record.get("files", [])[:10], "saved_at": _when(record.get("saved_at", 0)),
            "pull_request": record.get("pr_url") or None, "bytes": record.get("bytes", 0),
        }

    async def list_saved(self, user: str, repo_url: Optional[str] = None) -> Dict[str, Any]:
        """The user's saved work (all repos, or one), dropping any whose pull request is finished."""
        user = self._user(user)
        if not user:
            raise GitCiError("Saved work belongs to a signed-in user; sign in to see it.")
        records = await self._drop_finished(user, await self.store.list(user))
        mine = records
        if repo_url:
            owner, name = parse_repo_url(repo_url)
            mine = [r for r in records if r["repo"] == f"{owner}/{name}".lower()]
        return {
            "saved_work": [self._summary(r) for r in mine],
            "branches_used": len(records), "branches_limit": self.cfg.max_saved_branches,
            "mb_used": round(sum(r["bytes"] for r in records) / 1e6, 2),
            "mb_limit": round(self.cfg.max_saved_bytes_per_user / 1e6, 2),
            "kept_days_after_last_change": self.cfg.save_keep_days,
        }

    async def delete_saved(self, user: str, repo_url: str, branch: str) -> Dict[str, Any]:
        """Delete one saved branch, and close the user's open sandbox on it without saving, so it
        does not save the work right back."""
        user = self._user(user)
        if not user:
            raise GitCiError("Saved work belongs to a signed-in user; sign in to delete it.")
        owner, name = parse_repo_url(repo_url)
        key = f"{owner}/{name}".lower()
        check_ref(branch)
        if await self.store.get(user, key, branch) is None:
            raise GitCiError(f"There is no saved work on '{branch}' of {key}. list_saved_work shows what there is.")
        for _idle, d, m in self._live():
            if self._holds(m, user, key, branch):
                await asyncio.to_thread(remove_tree, d)
        await self.store.delete(user, key, branch)
        return {"deleted": True, "repo": key, "branch": branch}

    async def record_pr(self, sandbox_id: str, pr_url: str) -> None:
        """Remember the pull request of the current branch, so a later clone can tell if it was merged."""
        d = self._dir(sandbox_id)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta.setdefault("prs", {})[meta.get("branch") or meta["base"]] = pr_url
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        await self._autosave(sandbox_id)

    async def pr_base(self, sandbox_id: str) -> Dict[str, str]:
        """The branch a pull request from the current branch should target: the branch it was created
        on (a stacked pull request) once that is on GitHub, otherwise the repo's base branch."""
        repo, meta = self._repo(sandbox_id), self._meta(sandbox_id)
        parent = meta.get("parents", {}).get(meta.get("branch", ""), "")
        if not parent:
            return {"base": meta["base"]}
        try:
            on_github = (await self._git(repo, "ls-remote", "--heads", "origin", f"refs/heads/{parent}", timeout=30)).strip()
        except GitCiError:
            on_github = ""
        if on_github:
            return {"base": parent}
        return {"base": meta["base"], "note": f"This branch is stacked on '{parent}', which is not on GitHub, so the "
                f"pull request targets {meta['base']} and also shows the commits of '{parent}'."}

    @staticmethod
    def _user(user: str) -> str:
        user = (user or "").strip().lower()
        if user and not _LOGIN.match(user):
            raise GitCiError("The owner must be a GitHub login.")
        return user

    def _check_owner(self, owner: str) -> None:
        if owner.lower() not in {o.lower() for o in self.cfg.allowed_owners}:
            raise GitCiError(
                f"'{owner}' is not an allowed owner. This server only works on repos owned by: "
                f"{', '.join(self.cfg.allowed_owners)}."
            )

    def check_repo(self, owner: str, name: str) -> None:
        self._check_owner(owner)
        allowed = {r.lower() for r in self.cfg.allowed_repos}
        if allowed and f"{owner}/{name}".lower() not in allowed:
            raise GitCiError(
                f"'{owner}/{name}' is not an allowed repo. This server only works on: "
                f"{', '.join(self.cfg.allowed_repos)}."
            )

    # ---------------------------------------------------------------- operations
    async def create(self, repo_url: str, ref: Optional[str] = None, *, source: Optional[str] = None,
                     user: str = "", branch: Optional[str] = None) -> Dict[str, Any]:
        """Clone into a fresh sandbox. ``user`` is the signed-in GitHub login, set by the agent backend
        (never by the model). With ``branch``, that saved branch of the user's is put back; without it
        the sandbox starts clean and the result lists the user's saved work on this repo.
        ``source`` (tests only) replaces the clone URL."""
        owner, name = parse_repo_url(repo_url)
        self.check_repo(owner, name)
        if ref:
            check_ref(ref, "ref")
        user = self._user(user)
        key = f"{owner}/{name}".lower()
        saved: Optional[Dict[str, Any]] = None
        if branch:
            check_ref(branch)
            if not user:
                raise GitCiError("Saved work belongs to a signed-in user; sign in to resume it.")
            # An open sandbox on this branch is saved and closed first, so what comes back is its latest.
            await self._retire(user, key, branch)
            saved = await self.store.get(user, key, branch)
            if saved is None:
                names = [r["branch"] for r in await self.store.list(user) if r["repo"] == key]
                raise GitCiError(f"You have no saved work on branch '{branch}' of {key}. "
                                 + (f"Saved branches: {', '.join(names)}." if names else "Nothing is saved for this repo."))
        if user:
            await self._make_room_for(user)
        await self._sweep()
        sid = uuid.uuid4().hex[:12]
        d = self.root / sid
        d.mkdir(parents=True)
        try:
            # autocrlf off: keep the repo's own line endings so a patch written from read_file applies.
            args = ["clone", "-c", "core.autocrlf=false", "--depth", "50", "--no-tags", "--single-branch"]
            if ref:
                args += ["--branch", ref]
            await self._git(None, *args, "--", source or f"https://github.com/{owner}/{name}.git", str(d / "repo"))
            base = (await self._git(d / "repo", "rev-parse", "--abbrev-ref", "HEAD")).strip()
            head = (await self._git(d / "repo", "rev-parse", "HEAD")).strip()
        except Exception:
            remove_tree(d)
            raise
        meta = {"owner": owner, "repo": name, "user": user, "key": key, "base": base, "base_sha": head,
                "branch": base, "owns": [], "parents": {}, "pushed": {}, "prs": {}, "created": time.time()}
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        result: Dict[str, Any] = {"sandbox_id": sid, "repo": f"{owner}/{name}", "branch": base, "head": head[:12]}
        if saved is not None:
            resumed = await self._restore(sid, user, key, saved)
            result["resumed"] = resumed
            if resumed.get("restored"):
                result["branch"] = resumed["branch"]
                result["head"] = (await self._git(d / "repo", "rev-parse", "HEAD")).strip()[:12]
        elif user:
            try:
                records = [r for r in await self.store.list(user) if r["repo"] == key]
            except Exception:
                records = []
            if records:
                result["saved_work"] = [self._summary(r) for r in records]
        return result

    async def status(self, sandbox_id: str) -> Dict[str, Any]:
        repo, meta = self._repo(sandbox_id), self._meta(sandbox_id)
        branch = (await self._git(repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
        porcelain = (await self._git(repo, "status", "--porcelain")).splitlines()
        ahead = (await self._git(repo, "rev-list", "--count", f"{meta['base']}..HEAD")).strip() if branch != meta["base"] else "0"
        return {
            "repo": f"{meta['owner']}/{meta['repo']}", "base": meta["base"], "branch": branch,
            "uncommitted_files": [line[3:] for line in porcelain], "commits_ahead_of_base": int(ahead or 0),
        }

    async def create_branch(self, sandbox_id: str, name: str) -> Dict[str, Any]:
        """Create a branch from wherever the sandbox is. Created on top of another feature branch, it
        is stacked on it: its pull request targets that branch once it is on GitHub."""
        check_ref(name)
        d = self._dir(sandbox_id)
        repo, meta = d / "repo", self._meta(sandbox_id)
        await self._git(repo, "check-ref-format", "--branch", name)
        # Find a name clash now, not after the whole fix: a push never overwrites a branch that
        # already exists on GitHub (an earlier run's), so it would be rejected at the very end.
        try:
            taken = (await self._git(repo, "ls-remote", "--heads", "origin", f"refs/heads/{name}", timeout=30)).strip()
        except GitCiError:
            taken = ""  # cannot reach origin to ask; the push will say if there is a real problem
        if taken:
            raise GitCiError(
                f"The branch '{name}' already exists on GitHub (probably from an earlier run). "
                f"Create the branch again with a different name, for example '{name}-2'."
            )
        if meta.get("user"):
            try:
                saved = await self.store.get(meta["user"], meta["key"], name)
            except Exception:
                saved = None  # cannot ask; the save after this step will say if the name is taken
            if saved is not None:
                raise GitCiError(
                    f"You already have saved work on a branch named '{name}'. To continue it, use "
                    f"sandbox_clone with branch='{name}'; for new work, pick another name."
                )
        current = (await self._git(repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
        await self._git(repo, "switch", "-c", name)
        stacked_on = current if current != meta["base"] else ""
        meta["branch"] = name
        if stacked_on:
            meta.setdefault("parents", {})[name] = stacked_on
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        result: Dict[str, Any] = {"branch": name}
        if stacked_on:
            result["stacked_on"] = stacked_on
        return {**result, **await self._autosave(sandbox_id)}

    async def apply_patch(self, sandbox_id: str, diff: str) -> Dict[str, Any]:
        files = validate_patch(diff, self.cfg.max_patch_bytes)
        repo = self._repo(sandbox_id)
        text = diff if diff.endswith("\n") else diff + "\n"
        # --recount: models often get a hunk's line counts wrong; git recomputes them from the body.
        flags = ["--recount", "--whitespace=nowarn"]
        try:
            await self._git(repo, "apply", "--check", *flags, "-", stdin=text)
        except GitCiError as exc:
            raise GitCiError(
                f"{exc} Hint: copy the context lines exactly from read_file, or use edit_file with the exact old and new text."
            )
        await self._git(repo, "apply", *flags, "-", stdin=text)
        return {"applied": True, "files": files, **await self._autosave(sandbox_id)}

    def _inside(self, sandbox_id: str, rel: str) -> Path:
        """Resolve a repo-relative path, refusing anything outside the work tree or inside .git."""
        repo = self._repo(sandbox_id).resolve()
        if _bad_patch_path(rel or "x") or not rel:
            raise GitCiError("That path is not allowed.")
        target = (repo / rel).resolve()
        if repo != target and repo not in target.parents:
            raise GitCiError("That path is not allowed.")
        return target

    async def edit_file(self, sandbox_id: str, path: str, old: str, new: str) -> Dict[str, Any]:
        """Replace one exact occurrence of `old` with `new`. More reliable for a model than a diff."""
        target = self._inside(sandbox_id, path)
        if not target.is_file():
            raise GitCiError(f"'{path}' is not a file in this sandbox.")
        if not old:
            raise GitCiError("'old' must be the exact text to replace.")
        if len(old) + len(new) > self.cfg.max_patch_bytes:
            raise GitCiError("The edit is too large.")
        raw = target.read_bytes()
        if b"\x00" in raw[:8000]:
            raise GitCiError("That looks like a binary file.")
        text = raw.decode("utf-8")
        crlf = "\r\n" in text
        body, old_n, new_n = (t.replace("\r\n", "\n") for t in (text, old, new))
        count = body.count(old_n)
        if count != 1:
            raise GitCiError(
                f"'old' matched {count} times; it must match exactly once. Include more surrounding lines from read_file."
            )
        body = body.replace(old_n, new_n, 1)
        target.write_bytes((body.replace("\n", "\r\n") if crlf else body).encode("utf-8"))
        return {"edited": path, "removed_lines": old_n.count("\n") + 1, "added_lines": new_n.count("\n") + 1,
                **await self._autosave(sandbox_id)}

    async def list_files(self, sandbox_id: str) -> Dict[str, Any]:
        """Tracked files only (git ls-files), so build output and .git never appear."""
        out = await self._git(self._repo(sandbox_id), "ls-files")
        files = out.splitlines()
        return {"count": len(files), "files": files[:300], "truncated": len(files) > 300}

    async def read_file(self, sandbox_id: str, path: str) -> Dict[str, Any]:
        target = self._inside(sandbox_id, path)
        if not target.is_file():
            raise GitCiError(f"'{path}' is not a file in this sandbox.")
        cap = 20000
        data = target.read_bytes()[: cap + 1]
        if b"\x00" in data:
            raise GitCiError("That looks like a binary file.")
        text = data.decode("utf-8", errors="replace")
        return {"path": path, "content": text[:cap], "truncated": len(data) > cap}

    async def diff(self, sandbox_id: str) -> Dict[str, Any]:
        repo = self._repo(sandbox_id)
        await self._git(repo, "add", "-N", ".")  # show new files too (intent-to-add, not staged content)
        out = await self._git(repo, "diff", "HEAD")
        stat = await self._git(repo, "diff", "HEAD", "--stat")
        return {"stat": stat.strip(), "diff": self._cap(out)}

    async def run_tests(self, sandbox_id: str, command: str) -> Dict[str, Any]:
        normalized = " ".join((command or "").split())
        allowed = [" ".join(c.split()) for c in self.cfg.test_commands]
        if normalized not in allowed:
            raise GitCiError(f"'{command}' is not an allowed test command. Allowed: {', '.join(allowed)}.")
        repo = self._repo(sandbox_id)
        argv = normalized.split(" ")
        env = {k: os.environ[k] for k in _SAFE_ENV if k in os.environ}
        env["CI"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        started = time.time()

        def run() -> Dict[str, Any]:
            try:
                done = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=self.cfg.test_timeout_seconds, env=env)
                return {"exit_code": done.returncode, "output": (done.stdout or "") + (done.stderr or ""), "timed_out": False}
            except subprocess.TimeoutExpired as exc:
                partial = (exc.stdout or b"")
                partial = partial.decode("utf-8", "replace") if isinstance(partial, bytes) else partial
                return {"exit_code": None, "output": partial, "timed_out": True}
            except FileNotFoundError:
                return {"exit_code": 127, "output": f"{argv[0]}: command not found on this server", "timed_out": False}

        # Test runs are the heavy part, so only a few run at once. Wait briefly for a slot; the agent
        # gives up on a tool call after 90 seconds, so a long queue would only turn into a timeout.
        try:
            await asyncio.wait_for(self._tests.acquire(), timeout=self.cfg.test_queue_seconds)
        except asyncio.TimeoutError:
            raise GitCiError("Other missions are running their tests right now. Run the tests again in a minute.")
        try:
            result = await asyncio.to_thread(run)
        finally:
            self._tests.release()
        return {
            "command": normalized, "passed": result["exit_code"] == 0, "exit_code": result["exit_code"],
            "timed_out": result["timed_out"], "seconds": round(time.time() - started, 1),
            "output_tail": self._cap(result["output"]),
        }

    async def commit(self, sandbox_id: str, message: str) -> Dict[str, Any]:
        message = (message or "").strip()
        if not message or len(message) > 1000:
            raise GitCiError("The commit message must be 1-1000 characters.")
        repo = self._repo(sandbox_id)
        await self._git(repo, "add", "-A")
        if not (await self._git(repo, "status", "--porcelain")).strip():
            raise GitCiError("There is nothing to commit.")
        ident: List[str] = []
        if self.cfg.author_name and self.cfg.author_email:
            ident = ["-c", f"user.name={self.cfg.author_name}", "-c", f"user.email={self.cfg.author_email}"]
        await self._git(repo, *ident, "commit", "-m", message)
        head = (await self._git(repo, "rev-parse", "HEAD")).strip()
        return {"commit": head[:12], **await self._autosave(sandbox_id)}

    async def push_branch(self, sandbox_id: str, token: str) -> Dict[str, Any]:
        """Push the current branch to origin using the token as an HTTP header (never in a URL
        or in git config on disk). Refuses to push the base branch."""
        if not token:
            raise GitCiError("GITHUB_TOKEN is not set on the server, so nothing can be pushed.")
        repo, meta = self._repo(sandbox_id), self._meta(sandbox_id)
        branch = (await self._git(repo, "rev-parse", "--abbrev-ref", "HEAD")).strip()
        if branch == meta["base"] or branch in ("main", "master", "HEAD"):
            raise GitCiError(f"Refusing to push '{branch}'. Create a feature branch first.")
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraheader",
               "GIT_CONFIG_VALUE_0": f"Authorization: Basic {basic}"}
        await self._git(repo, "push", "origin", f"HEAD:refs/heads/{branch}", extra_env=env, secret=token)
        meta.setdefault("pushed", {})[branch] = (await self._git(repo, "rev-parse", "HEAD")).strip()
        (self._dir(sandbox_id) / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return {"branch": branch, "pushed": True, **await self._autosave(sandbox_id)}

    def meta(self, sandbox_id: str) -> Dict[str, Any]:
        return self._meta(sandbox_id)

    async def destroy(self, sandbox_id: str, discard: bool = False) -> Dict[str, Any]:
        """Delete a sandbox. A signed-in user's unfinished work is saved first and comes back when they
        pass its branch to sandbox_clone; if it cannot be saved, the sandbox is kept. ``discard`` deletes
        it without saving (only when the user says to throw the work away)."""
        d = self._dir(sandbox_id)
        if discard:
            await asyncio.to_thread(remove_tree, d)
            return {"destroyed": True, "saved": False}
        try:
            saved = await self._save(d)
        except SaveRefused as exc:
            raise GitCiError(f"{exc} The sandbox was not deleted.")
        except Exception as exc:
            logger.warning("[GITCI] could not save sandbox %s (%s)", sandbox_id, type(exc).__name__)
            raise GitCiError("The work in this sandbox could not be saved, so it was not deleted. Try again later.")
        await asyncio.to_thread(remove_tree, d)
        return {"destroyed": True, "saved": saved}
