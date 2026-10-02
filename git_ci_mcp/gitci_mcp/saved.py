"""Saved progress: a signed-in user's unfinished work, kept off this machine so it outlives the sandbox.

Sandboxes are deleted when idle, and on a free Render instance the whole disk is wiped whenever the
service sleeps (15 minutes without traffic) or redeploys. So after every change a user's work is saved
here (commits as patches, uncommitted edits as a diff) and sandbox_clone puts it back. One record per
GitHub login and repo.

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
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class SavedStore:
    async def get(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def put(self, owner: str, repo: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def delete(self, owner: str, repo: str) -> None:
        raise NotImplementedError


class FileStore(SavedStore):
    def __init__(self, root: str, keep_days: int):
        self.root = Path(root)
        self.keep_seconds = keep_days * 86400

    def _path(self, owner: str, repo: str) -> Path:
        return self.root / (hashlib.sha256(f"{owner}/{repo}".encode()).hexdigest()[:32] + ".json")

    async def get(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        p = self._path(owner, repo)
        if not p.is_file():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("saved_at", 0) > self.keep_seconds:
            p.unlink(missing_ok=True)
            return None
        return data

    async def put(self, owner: str, repo: str, data: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self._path(owner, repo).with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(self._path(owner, repo))

    async def delete(self, owner: str, repo: str) -> None:
        self._path(owner, repo).unlink(missing_ok=True)


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
        data jsonb NOT NULL,
        saved_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (owner, repo))"""

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

    async def get(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        def go(conn):
            row = conn.execute(
                "SELECT data FROM gitci_saved_work WHERE owner = %s AND repo = %s "
                "AND saved_at > now() - make_interval(days => %s)",
                (owner, repo, self.keep_days),
            ).fetchone()
            return row[0] if row else None
        return await asyncio.to_thread(self._run, go)

    async def put(self, owner: str, repo: str, data: Dict[str, Any]) -> None:
        from psycopg.types.json import Jsonb

        def go(conn):
            conn.execute(
                "INSERT INTO gitci_saved_work (owner, repo, data, saved_at) VALUES (%s, %s, %s, now()) "
                "ON CONFLICT (owner, repo) DO UPDATE SET data = EXCLUDED.data, saved_at = now()",
                (owner, repo, Jsonb(data)),
            )
            conn.execute("DELETE FROM gitci_saved_work WHERE saved_at < now() - make_interval(days => %s)",
                         (self.keep_days,))
        await asyncio.to_thread(self._run, go)

    async def delete(self, owner: str, repo: str) -> None:
        def go(conn):
            conn.execute("DELETE FROM gitci_saved_work WHERE owner = %s AND repo = %s", (owner, repo))
        await asyncio.to_thread(self._run, go)
