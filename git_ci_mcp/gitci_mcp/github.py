"""Thin GitHub REST client: read-only CI status and draft pull requests."""

from __future__ import annotations

import re
from typing import Any, Dict

import httpx

from .config import Settings, settings as default_settings
from .sandbox import GitCiError, check_ref


_PR_URL = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})/pull/([0-9]{1,9})$")


class GitHub:
    def __init__(self, cfg: Settings = default_settings):
        self.cfg = cfg

    def _headers(self, auth: bool) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
             "User-Agent": "gitci-mcp"}
        if auth and self.cfg.github_token:
            h["Authorization"] = f"Bearer {self.cfg.github_token}"
        return h

    async def ci_status(self, owner: str, repo: str, ref: str) -> Dict[str, Any]:
        check_ref(ref, "ref")
        base = f"{self.cfg.github_api}/repos/{owner}/{repo}/commits/{ref}"
        async with httpx.AsyncClient(timeout=20, headers=self._headers(True)) as c:
            runs = await c.get(f"{base}/check-runs", params={"per_page": 30})
            if runs.status_code == 404:
                raise GitCiError(f"No commit '{ref}' found in {owner}/{repo}. Has the branch been pushed?")
            if runs.status_code in (401, 403):
                raise GitCiError("GitHub refused the request (rate limit or missing permission).")
            runs.raise_for_status()
            combined = await c.get(f"{base}/status")
        checks = [{"name": r["name"], "status": r["status"], "conclusion": r.get("conclusion")}
                  for r in runs.json().get("check_runs", [])]
        legacy = combined.json().get("state") if combined.status_code == 200 else None
        if not checks:
            overall = legacy or "none"
        elif any(ch["status"] != "completed" for ch in checks):
            overall = "pending"
        elif all(ch["conclusion"] in ("success", "neutral", "skipped") for ch in checks):
            overall = "success"
        else:
            overall = "failure"
        return {"repo": f"{owner}/{repo}", "ref": ref, "overall": overall, "checks": checks}

    async def pr_state(self, url: str) -> str:
        """"open", "merged", "closed", or "unknown" when GitHub cannot be asked."""
        m = _PR_URL.match(url or "")
        if not m:
            return "unknown"
        owner, repo, number = m.groups()
        try:
            async with httpx.AsyncClient(timeout=15, headers=self._headers(True)) as c:
                r = await c.get(f"{self.cfg.github_api}/repos/{owner}/{repo}/pulls/{number}")
        except httpx.HTTPError:
            return "unknown"
        if r.status_code != 200:
            return "unknown"
        pr = r.json()
        if pr.get("merged_at"):
            return "merged"
        return "closed" if pr.get("state") == "closed" else "open"

    async def draft_pr(self, owner: str, repo: str, head: str, base: str, title: str, body: str) -> Dict[str, Any]:
        if not self.cfg.github_token:
            raise GitCiError("GITHUB_TOKEN is not set on the server, so a pull request cannot be opened.")
        async with httpx.AsyncClient(timeout=30, headers=self._headers(True)) as c:
            r = await c.post(f"{self.cfg.github_api}/repos/{owner}/{repo}/pulls",
                             json={"title": title, "head": head, "base": base, "body": body, "draft": True})
            if r.status_code == 422:
                # Resumed work whose branch already has an open pull request: the push updated it.
                found = await c.get(f"{self.cfg.github_api}/repos/{owner}/{repo}/pulls",
                                    params={"head": f"{owner}:{head}", "state": "open"})
                if found.status_code == 200 and found.json():
                    pr = found.json()[0]
                    return {"created": False, "updated": True, "draft": pr.get("draft", True),
                            "number": pr["number"], "url": pr["html_url"]}
        if r.status_code == 422:
            raise GitCiError(f"GitHub rejected the pull request: {r.json().get('message', 'validation failed')}.")
        if r.status_code in (401, 403, 404):
            raise GitCiError("GitHub refused the request; check that GITHUB_TOKEN can write to this repo.")
        r.raise_for_status()
        pr = r.json()
        return {"created": True, "draft": True, "number": pr["number"], "url": pr["html_url"]}
