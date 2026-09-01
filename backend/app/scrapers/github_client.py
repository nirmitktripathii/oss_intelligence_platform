"""Async GitHub REST & Search API Client with ETag caching and rate limit handling."""

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """High-throughput asynchronous GitHub API client."""

    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = (base_url or settings.GITHUB_API_BASE).rstrip("/")
        # In-memory ETag cache: url -> (etag, json_data)
        self._etag_cache: Dict[str, Tuple[str, Any]] = {}

    def _build_headers(self, etag: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitScout-Platform/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if etag:
            headers["If-None-Match"] = etag
        return headers

    async def fetch_repo_issues(
        self,
        owner: str,
        repo: str,
        per_page: int = 20,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Fetch 100% live open unassigned issues from a specific repository.
        Strict verification: state == 'open', pull_request is None, assignee is None.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {
            "state": "open",
            "assignee": "none",
            "per_page": min(per_page, 100),
            "page": page,
            "sort": "updated",
            "direction": "desc",
        }

        cache_key = f"{url}?{owner}/{repo}/p{page}"
        cached_etag, cached_data = self._etag_cache.get(cache_key, (None, None))

        headers = self._build_headers(etag=cached_etag)

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=headers)

                # Check for 304 Not Modified
                if response.status_code == 304 and cached_data is not None:
                    logger.debug(f"ETag cache hit for {owner}/{repo}")
                    return cached_data

                # Rate Limit handling
                if response.status_code == 403:
                    remaining = response.headers.get("x-ratelimit-remaining", "0")
                    logger.warning(f"GitHub API rate limit reached or 403 Forbidden: remaining={remaining}")
                    return cached_data if cached_data is not None else []

                if response.status_code == 404:
                    logger.warning(f"GitHub repository not found: {owner}/{repo}")
                    return []

                response.raise_for_status()

                # Update ETag cache
                etag = response.headers.get("ETag")
                raw_items = response.json()

                if not isinstance(raw_items, list):
                    return []

                # Strict Verification Filter
                valid_issues = []
                for item in raw_items:
                    # Must NOT be a pull request
                    if item.get("pull_request") is not None:
                        continue
                    # Must be open
                    if item.get("state") != "open":
                        continue
                    # Must be unassigned
                    if item.get("assignee") is not None or len(item.get("assignees", [])) > 0:
                        continue

                    valid_issues.append(item)

                if etag:
                    self._etag_cache[cache_key] = (etag, valid_issues)

                return valid_issues

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error fetching issues for {owner}/{repo}: {exc}")
            return cached_data if cached_data is not None else []
        except Exception as exc:
            logger.error(f"Unexpected error fetching issues for {owner}/{repo}: {exc}")
            return []

    async def search_bounty_issues(
        self,
        query: Optional[str] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Query GitHub Global Search API for open unassigned bounty issues.
        Strict verification: is:issue, is:open, no:assignee.
        """
        url = f"{self.base_url}/search/issues"
        default_q = 'is:issue is:open (label:bounty OR "algora.io" OR "Funding on Polar" OR "bounty")'
        search_q = query or default_q

        params = {
            "q": search_q,
            "sort": "updated",
            "order": "desc",
            "per_page": min(per_page, 100),
            "page": page,
        }

        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 403:
                    logger.warning("GitHub Search API rate limit hit.")
                    return []

                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])

                valid_issues = []
                for item in items:
                    if item.get("pull_request") is not None:
                        continue
                    if item.get("state") != "open":
                        continue
                    if item.get("assignee") is not None:
                        continue
                    valid_issues.append(item)

                return valid_issues

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error searching bounty issues: {exc}")
            return []
        except Exception as exc:
            logger.error(f"Unexpected error searching bounty issues: {exc}")
            return []

    async def fetch_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> List[Dict[str, Any]]:
        """Fetch comments for an issue to locate bot bounty disclosures."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else []
                return []
        except Exception:
            return []

    async def fetch_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Optional[str]:
        """
        Fetch a single file's decoded UTF-8 text via the GitHub Contents API
        (default branch unless ``ref`` given). Returns None on 404 / rate limit /
        directory / binary / oversized-without-download — callers degrade gracefully.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref} if ref else {}
        headers = self._build_headers()
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                # A directory returns a list; we only ground on individual files.
                if not isinstance(data, dict):
                    return None
                if data.get("encoding") == "base64" and data.get("content"):
                    try:
                        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                    except Exception:
                        return None
                # Files >1MB omit inline content; fall back to the raw download URL.
                download_url = data.get("download_url")
                if download_url:
                    raw = await client.get(download_url)
                    if raw.status_code == 200:
                        return raw.text
        except Exception as exc:
            logger.debug(f"Contents fetch failed for {owner}/{repo}/{path}: {exc}")
        return None

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Check current GitHub API quota status."""
        url = f"{self.base_url}/rate_limit"
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                return {"status": "unavailable", "code": response.status_code}
        except Exception as exc:
            return {"error": str(exc)}
