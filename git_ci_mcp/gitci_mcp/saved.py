"""Saved progress: a signed-in user's unfinished work, kept off this machine so it outlives the sandbox.

Sandboxes are deleted when idle, and on a free Render instance the whole disk is wiped whenever the
service sleeps (15 minutes without traffic) or redeploys. So after every change a user's work is saved
here (commits as patches, uncommitted edits as a diff) and sandbox_clone puts it back. One record per
GitHub login, repo and branch, so work on one issue never overwrites work on another.

Postgres when GITCI_SAVE_DATABASE_URL is set, which survives restarts. Otherwise a local directory,
which is fine on a laptop but is wiped along with the sandboxes on Render.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def size_of(data: Dict[str, Any]) -> int:
    """What a record counts against its owner's space."""
    return len(json.dumps(data).encode("utf-8"))


class SavedStore:
    """Records expire ``keep_days`` after their last save."""

    async def get(self, owner: str, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def put(self, owner: str, repo: str, branch: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def delete(self, owner: str, repo: str, branch: str) -> None:
        raise NotImplementedError

    async def list(self, owner: str) -> List[Dict[str, Any]]:
        """Every live record of this owner, each with "repo", "branch", "bytes" and its data."""
        raise NotImplementedError


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


class FileStore(SavedStore):
    def __init__(self, root: str, keep_days: int):
        self.root = Path(root)
        self.keep_seconds = keep_days * 86400

    def _path(self, owner: str, repo: str, branch: str) -> Path:
        return self.root / _h(owner) / (_h(f"{repo}\n{branch}") + ".json")

    def _read(self, p: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if time.time() - data.get("saved_at", 0) > self.keep_seconds:
            p.unlink(missing_ok=True)
            return None
        return data

    async def get(self, owner: str, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        p = self._path(owner, repo, branch)
        return self._read(p) if p.is_file() else None

    async def put(self, owner: str, repo: str, branch: str, data: Dict[str, Any]) -> None:
        p = self._path(owner, repo, branch)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({**data, "repo": repo, "branch": branch}), encoding="utf-8")
        tmp.replace(p)

    async def delete(self, owner: str, repo: str, branch: str) -> None:
        self._path(owner, repo, branch).unlink(missing_ok=True)

    async def list(self, owner: str) -> List[Dict[str, Any]]:
        d = self.root / _h(owner)
        out = []
        for p in sorted(d.glob("*.json")) if d.is_dir() else []:
            data = self._read(p)
            if data:
                out.append({**data, "bytes": size_of(data)})
        return out


def postgres_url(url: str) -> str:
    """Accept the forms people paste (SQLAlchemy's postgresql+asyncpg://, postgres://, asyncpg's ssl=)
    and return a plain libpq URL."""
    url = re.sub(r"^postgres(?:ql)?(?:\+\w+)?://", "postgresql://", url.strip())
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "ssl":
            key = "sslmode"
        if key == "prepared_statement_cache_size":
            continue  # asyncpg only
        query.append((key, value))
    return urlunsplit(parts._replace(query=urlencode(query)))


class PostgresStore(SavedStore):
    _TABLE = """CREATE TABLE IF NOT EXISTS gitci_saved_work (
        owner text NOT NULL,
        repo text NOT NULL,
        branch text NOT NULL,
        data jsonb NOT NULL,
        bytes integer NOT NULL,
        saved_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (owner, repo, branch))"""

    def __init__(self, url: str, keep_days: int):
        self.url = postgres_url(url)
        self.keep_days = keep_days
        self._ready = False

    def _run(self, fn):
        import psycopg  # only needed when this store is configured

        with psycopg.connect(self.url, connect_timeout=10, autocommit=True) as conn:
            if not self._ready:
                conn.execute(self._TABLE)
                self._ready = True
            return fn(conn)

    _LIVE = "saved_at > now() - make_interval(days => %s)"

    async def get(self, owner: str, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        def go(conn):
            row = conn.execute(
                f"SELECT data FROM gitci_saved_work WHERE owner = %s AND repo = %s AND branch = %s AND {self._LIVE}",
                (owner, repo, branch, self.keep_days),
            ).fetchone()
            return row[0] if row else None
        return await asyncio.to_thread(self._run, go)

    async def put(self, owner: str, repo: str, branch: str, data: Dict[str, Any]) -> None:
        from psycopg.types.json import Jsonb

        data = {**data, "repo": repo, "branch": branch}

        def go(conn):
            conn.execute(
                "INSERT INTO gitci_saved_work (owner, repo, branch, data, bytes, saved_at) "
                "VALUES (%s, %s, %s, %s, %s, now()) ON CONFLICT (owner, repo, branch) "
                "DO UPDATE SET data = EXCLUDED.data, bytes = EXCLUDED.bytes, saved_at = now()",
                (owner, repo, branch, Jsonb(data), size_of(data)),
            )
            conn.execute("DELETE FROM gitci_saved_work WHERE saved_at < now() - make_interval(days => %s)",
                         (self.keep_days,))
        await asyncio.to_thread(self._run, go)

    async def delete(self, owner: str, repo: str, branch: str) -> None:
        def go(conn):
            conn.execute("DELETE FROM gitci_saved_work WHERE owner = %s AND repo = %s AND branch = %s",
                         (owner, repo, branch))
        await asyncio.to_thread(self._run, go)

    async def list(self, owner: str) -> List[Dict[str, Any]]:
        def go(conn):
            rows = conn.execute(
                f"SELECT data, bytes FROM gitci_saved_work WHERE owner = %s AND {self._LIVE} ORDER BY repo, branch",
                (owner, self.keep_days),
            ).fetchall()
            return [{**data, "bytes": size} for data, size in rows]
        return await asyncio.to_thread(self._run, go)
