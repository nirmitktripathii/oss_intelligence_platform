"""Reject non-actionable "issues" (bot-generated digests, newsletters, blog posts).

GitScout is a portal for *solvable OSS bugs and feature requests*. The global bounty
search (``GitHubClient.search_bounty_issues``) does a broad full-text match on the word
"bounty", so it also surfaces automated news digests that merely *mention* bounties in
prose — e.g. a "Hacker News AI 日报" generated daily by ``github-actions[bot]`` in a
``*-radar`` repo. Those are not defects a contributor can fix, and they pollute the
board (often mis-tagged with a false bounty parsed out of the prose).

``NoiseFilter.is_actionable_issue`` is the single gate the orchestrator runs before an
item is stored. It errs toward keeping real issues: only clear automation output or
unambiguous digest/newsletter content is dropped, and each rejection returns a short
reason for logging so the decision is auditable.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Authors that only ever open automated, non-actionable issues (dashboards, scheduled
# digests, dependency reports). Matched exactly, case-insensitively; any login ending in
# "[bot]" is also treated as automation. Real bugs are filed by humans.
_BOT_AUTHORS = {
    "github-actions[bot]",
    "github-actions",
    "dependabot[bot]",
    "dependabot",
    "renovate[bot]",
    "renovate",
    "mergify[bot]",
    "codecov[bot]",
    "sonarcloud[bot]",
    "sweep-ai[bot]",
    "allcontributors[bot]",
    "imgbot[bot]",
    "stale[bot]",
}

# Strong markers: any ONE of these is enough to classify the item as a generated
# digest / newsletter / news roundup rather than a bug report.
_STRONG_DIGEST_MARKERS = (
    "自动生成",        # "auto-generated" (zh)
    "数据来源",        # "data source:" (zh) — digest provenance footer
    "日报",            # "daily report/digest" (zh)
    "周报",            # "weekly report" (zh)
    "月报",            # "monthly report" (zh)
    "动态日报",        # "activity daily" (zh)
    "auto-generated",
    "automatically generated",
    "this digest",
    "daily digest",
    "weekly digest",
    "news digest",
)

# Weaker markers: need at least two DISTINCT hits so a bug that merely says
# "weekly crash" or "news feed" is not dropped.
_WEAK_DIGEST_MARKERS = (
    "digest",
    "newsletter",
    "roundup",
    "round-up",
    "top stories",
    "week in review",
    "this week in",
    "hacker news",
    "news.ycombinator.com",
    "trending",
    "速览",            # "quick overview" (zh)
    "动态",            # "updates/trends" (zh)
    "新闻",            # "news" (zh)
)

# Repo name patterns that are aggregators / curated lists / blogs, not bug trackers.
_NONCODE_REPO_SUFFIXES = (
    "-radar",
    "-news",
    "-daily",
    "-digest",
    "-newsletter",
    "-weekly",
    "-trends",
    "-blog",
)
_NONCODE_REPO_PREFIXES = (
    "awesome-",
)


class NoiseFilter:
    """Decides whether a raw GitHub item is an actionable bug/feature vs. content noise."""

    @staticmethod
    def _is_bot_author(author: Optional[str]) -> bool:
        if not author:
            return False
        a = author.strip().lower()
        return a.endswith("[bot]") or a in _BOT_AUTHORS

    @staticmethod
    def _is_noncode_repo(repo_name: Optional[str]) -> bool:
        if not repo_name:
            return False
        name = repo_name.strip().lower()
        if name.startswith(_NONCODE_REPO_PREFIXES):
            return True
        return name.endswith(_NONCODE_REPO_SUFFIXES)

    @classmethod
    def _looks_like_digest(cls, title: str, body: str) -> bool:
        haystack = f"{title}\n{body}".lower()

        # 📰 in the title is a near-universal digest/newsletter signal.
        if "📰" in (title or ""):
            return True

        if any(marker in haystack for marker in _STRONG_DIGEST_MARKERS):
            return True

        # Hacker News aggregation: title/body pulls a feed of HN items.
        if "hacker news" in haystack and "news.ycombinator.com" in haystack:
            return True

        # A body that is mostly a link list of external stories (many markdown links to
        # external hosts) is a roundup, not a single actionable defect.
        weak_hits = {m for m in _WEAK_DIGEST_MARKERS if m in haystack}
        if len(weak_hits) >= 2:
            return True

        return False

    @classmethod
    def is_actionable_issue(
        cls,
        title: str,
        body: Optional[str],
        author: Optional[str] = None,
        labels: Optional[List[Dict[str, Any]]] = None,
        repo_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Return ``(True, None)`` for a real bug/feature, ``(False, reason)`` for noise.

        ``reason`` is a short, stable slug suitable for logging and metrics.
        """
        title = (title or "").strip()
        body = body or ""

        # An item with no title AND no body is not a usable issue.
        if not title and not body.strip():
            return False, "empty"

        if cls._is_bot_author(author):
            return False, "bot-authored"

        if cls._is_noncode_repo(repo_name):
            return False, "non-code-repo"

        if cls._looks_like_digest(title, body):
            return False, "digest-or-newsletter"

        return True, None
