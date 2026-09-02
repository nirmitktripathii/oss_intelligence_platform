"""Q1 long-description handling: prepare_llm_body + orchestrator summary resolution.

Covers the summarize-on-overflow contract:
  * bodies <= LLM_BODY_MAX_CHARS are fed verbatim (no summary, no LLM call);
  * a longer body is condensed exactly ONCE (hash-guarded compute-once);
  * an unchanged re-scrape reuses the stored summary without another call;
  * when no provider/summary is available the read path degrades to a hard
    truncation and NEVER fabricates a summary.
"""

import hashlib

import pytest

from app.config import settings
from app.models.issue import Issue
from app.scrapers.orchestrator import ScraperOrchestrator
from app.triage.llm_engine import LLMTriageEngine


CAP = int(getattr(settings, "LLM_BODY_MAX_CHARS", 8000))


def _issue(body: str) -> Issue:
    return Issue(
        id="foo/bar#1",
        repo_owner="foo",
        repo_name="bar",
        issue_number=1,
        title="Something is broken",
        body=body,
        html_url="https://github.com/foo/bar/issues/1",
        author="dev",
        domain="Web",
        tech_stack=["python"],
        difficulty="Medium",
        estimated_hours=2.0,
        has_bounty=False,
        labels=[],
    )


# ── prepare_llm_body ─────────────────────────────────────────────────────── #


def test_prepare_llm_body_prefers_summary():
    body = "x" * (CAP + 500)
    assert LLMTriageEngine.prepare_llm_body(body, body_summary="condensed") == "condensed"


def test_prepare_llm_body_passes_short_body_verbatim():
    body = "short body"
    assert LLMTriageEngine.prepare_llm_body(body, body_summary=None) == body


def test_prepare_llm_body_truncates_long_body_without_summary():
    body = "y" * (CAP + 1000)
    out = LLMTriageEngine.prepare_llm_body(body, body_summary=None)
    assert len(out) == CAP
    assert out == body[:CAP]


# ── _resolve_body_summary ────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_short_body_needs_no_summary(monkeypatch):
    called = False

    async def _boom(*a, **k):
        nonlocal called
        called = True
        return "should not run"

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _boom)

    orch = ScraperOrchestrator(client=None)
    issue = _issue("a short description")
    await orch._resolve_body_summary(issue, existing=None)

    assert issue.body_summary is None
    assert issue.body_summary_hash is None
    assert called is False  # no LLM call for bodies that already fit


@pytest.mark.asyncio
async def test_long_body_summarized_once(monkeypatch):
    calls = {"n": 0}

    async def _summ(body, issue_number=0, title=""):
        calls["n"] += 1
        return "condensed summary"

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _summ)

    body = "z" * (CAP + 4000)
    orch = ScraperOrchestrator(client=None)
    issue = _issue(body)
    await orch._resolve_body_summary(issue, existing=None)

    assert issue.body_summary == "condensed summary"
    assert issue.body_summary_hash == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_unchanged_body_reuses_stored_summary(monkeypatch):
    calls = {"n": 0}

    async def _summ(body, issue_number=0, title=""):
        calls["n"] += 1
        return "fresh summary"

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _summ)

    body = "q" * (CAP + 2000)
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    existing = _issue(body)
    existing.body_summary = "previously stored"
    existing.body_summary_hash = body_hash

    orch = ScraperOrchestrator(client=None)
    issue = _issue(body)
    await orch._resolve_body_summary(issue, existing=existing)

    assert issue.body_summary == "previously stored"
    assert issue.body_summary_hash == body_hash
    assert calls["n"] == 0  # compute-once: unchanged body => no new call


@pytest.mark.asyncio
async def test_changed_body_recomputes(monkeypatch):
    calls = {"n": 0}

    async def _summ(body, issue_number=0, title=""):
        calls["n"] += 1
        return "new summary"

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _summ)

    old_body = "a" * (CAP + 100)
    existing = _issue(old_body)
    existing.body_summary = "old summary"
    existing.body_summary_hash = hashlib.sha256(old_body.encode("utf-8")).hexdigest()

    new_body = "b" * (CAP + 100)  # different content -> different hash
    orch = ScraperOrchestrator(client=None)
    issue = _issue(new_body)
    await orch._resolve_body_summary(issue, existing=existing)

    assert issue.body_summary == "new summary"
    assert issue.body_summary_hash == hashlib.sha256(new_body.encode("utf-8")).hexdigest()
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_no_provider_degrades_without_fabricating(monkeypatch):
    async def _none(body, issue_number=0, title=""):
        return None  # e.g. no key configured / call failed

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _none)

    body = "c" * (CAP + 100)
    orch = ScraperOrchestrator(client=None)
    issue = _issue(body)
    await orch._resolve_body_summary(issue, existing=None)

    # Honest degradation: no summary stored (read path truncates), hash left NULL so a
    # later scrape retries. Nothing fabricated.
    assert issue.body_summary is None
    assert issue.body_summary_hash is None


@pytest.mark.asyncio
async def test_summarizer_exception_is_swallowed(monkeypatch):
    async def _raise(body, issue_number=0, title=""):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(LLMTriageEngine, "summarize_issue_body", _raise)

    body = "d" * (CAP + 100)
    orch = ScraperOrchestrator(client=None)
    issue = _issue(body)
    # Must not raise: summarization can never break indexing.
    await orch._resolve_body_summary(issue, existing=None)

    assert issue.body_summary is None
    assert issue.body_summary_hash is None
