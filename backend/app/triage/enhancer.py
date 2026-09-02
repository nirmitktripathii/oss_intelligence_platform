"""
Semantic enhancement layer for AI triage.

Wraps the deterministic AST triage with a *real* LLM enrichment when a free-tier
provider is configured, and derives a real, sortable triage confidence. Every path
degrades honestly: if the LLM is disabled, unconfigured, rate-limited, or returns
nothing usable, ``semantic_enhance`` returns ``None`` and the caller keeps the
deterministic AST result. Nothing here fabricates an AI answer.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.cache import get_cached_json, set_cached_json
from app.config import settings
from app.scrapers.github_client import GitHubClient
from app.triage.llm_engine import LLMTriageEngine

logger = logging.getLogger("gitscout.triage.enhancer")

# Rough language hints derived from an issue's tech_stack tags.
_LANG_HINTS = {
    "python": "Python", "py": "Python",
    "typescript": "TypeScript", "ts": "TypeScript",
    "javascript": "JavaScript", "js": "JavaScript", "node": "JavaScript",
    "go": "Go", "golang": "Go",
    "rust": "Rust", "rs": "Rust",
    "java": "Java", "kotlin": "Kotlin",
    "c++": "C++", "cpp": "C++",
    "ruby": "Ruby", "php": "PHP", "swift": "Swift",
}


def _clamp01(value: Any) -> Optional[float]:
    """Coerce a model-supplied score into [0.0, 1.0], or None if not numeric."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return round(max(0.0, min(1.0, f)), 4)


def derive_language(tech_stack: Optional[List[str]], domain: Optional[str] = None) -> str:
    """Best-effort primary language for prompt context; defaults to Python."""
    for tag in tech_stack or []:
        low = str(tag).lower()
        for needle, lang in _LANG_HINTS.items():
            if needle in low:
                return lang
    return "Python"


def ast_confidence(localized_files: List[Any]) -> float:
    """Deterministic confidence floor: the highest AST localization confidence."""
    best = 0.0
    for f in localized_files or []:
        c = f.get("confidence") if isinstance(f, dict) else getattr(f, "confidence", None)
        if isinstance(c, (int, float)):
            best = max(best, float(c))
    return round(best, 4)


def compute_triage_confidence(
    enrichment: Optional[Dict[str, Any]], localized_files: List[Any]
) -> float:
    """
    Real triage confidence used for the "Highest AI Confidence" sort:
    the LLM's calibrated score when the report was AI-enhanced, otherwise the
    deterministic AST localization floor. Never a hardcoded placeholder.
    """
    if enrichment and enrichment.get("confidence_score") is not None:
        return _clamp01(enrichment["confidence_score"]) or 0.0
    return ast_confidence(localized_files)


# ── Real-code grounding (#2): fetch the localized files' actual source ──────── #


def _candidate_paths(path: str) -> List[str]:
    """Repo-relative candidates to try for a stack-trace path (handles src/ layouts)."""
    path = path.lstrip("/")
    candidates = [path]
    if not path.startswith("src/"):
        candidates.append(f"src/{path}")
    return candidates


def _extract_window(source: str, line_range: Optional[str], max_chars: int) -> str:
    """Line-numbered slice around the localized range (or the file head), bounded by max_chars."""
    lines = source.splitlines()
    start, end = 0, min(len(lines), 150)
    if line_range and "-" in str(line_range):
        try:
            a, b = str(line_range).split("-", 1)
            start = max(0, int(a) - 1)
            end = min(len(lines), int(b))
        except (ValueError, TypeError):
            start, end = 0, min(len(lines), 150)
    numbered = [f"{start + i + 1}: {ln}" for i, ln in enumerate(lines[start:end])]
    return "\n".join(numbered)[:max_chars]


async def gather_source_context(
    repo_owner: str, repo_name: str, localized_files: List[Dict[str, Any]]
) -> Tuple[str, List[str]]:
    """
    Fetch the top localized files' real source (Contents API, Upstash-cached) and
    build a line-numbered context block. Returns (context_text, grounded_paths).
    Best-effort: unresolved files are skipped so the LLM still runs, just less grounded.
    """
    if not getattr(settings, "LLM_GROUND_IN_SOURCE", True):
        return "", []

    max_files = int(getattr(settings, "LLM_GROUND_MAX_FILES", 2))
    total_budget = int(getattr(settings, "LLM_SOURCE_MAX_CHARS", 6000))
    ttl = int(getattr(settings, "GITHUB_FILE_CACHE_TTL_SECONDS", 86400))

    client = GitHubClient()
    blocks: List[str] = []
    grounded: List[str] = []
    remaining = total_budget

    for lf in localized_files[:max_files]:
        path = (lf.get("file_path") or "").strip()
        if not path or path.startswith("http") or remaining <= 500:
            continue

        cache_key = f"gitscout:ghfile:{repo_owner}/{repo_name}:{path}"
        cached = await get_cached_json(cache_key)
        source = cached.get("content") if isinstance(cached, dict) else None

        if source is None:
            for candidate in _candidate_paths(path):
                try:
                    source = await client.fetch_file_content(repo_owner, repo_name, candidate)
                except Exception as exc:  # never let grounding break enhancement
                    logger.debug("grounding fetch error for %s: %s", candidate, exc)
                    source = None
                if source:
                    break
            if source:
                await set_cached_json(cache_key, {"content": source}, ttl_seconds=ttl)

        if not source:
            continue

        window = _extract_window(source, lf.get("line_range"), max_chars=remaining)
        if not window.strip():
            continue
        blocks.append(f"# File: {path}\n{window}")
        grounded.append(path)
        remaining -= len(window)

    return ("\n\n".join(blocks), grounded)


async def semantic_enhance(
    *,
    cache_key: str,
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    title: str,
    body: Optional[str],
    body_summary: Optional[str] = None,
    language: str,
    tech_stack: List[str],
    localized_files: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Return a normalized LLM enrichment dict, or ``None`` to keep AST-only.

    ``localized_files`` must be JSON-serializable dicts (call ``.model_dump()`` first).
    Results are cached in Redis under ``cache_key`` so the free-tier quota is spent
    once per issue, not once per view.
    """
    if not getattr(settings, "LLM_TRIAGE_ENABLED", True):
        return None
    # No provider configured -> deterministic only. Avoids any network call.
    if not LLMTriageEngine.resolve_chain():
        return None

    cached = await get_cached_json(cache_key)
    if isinstance(cached, dict) and cached.get("semantic_root_cause"):
        return cached

    # Real-code grounding: fetch the localized files' actual source for the prompt.
    source_context, grounded_files = await gather_source_context(
        repo_owner, repo_name, localized_files
    )

    try:
        result = await LLMTriageEngine.synthesize_semantic_root_cause(
            repo_owner=repo_owner,
            repo_name=repo_name,
            issue_number=issue_number,
            title=title,
            body=body,
            body_summary=body_summary,
            language=language,
            tech_stack=tech_stack,
            localized_files=localized_files,
            source_context=source_context,
        )
    except Exception as exc:  # never let enhancement break the endpoint
        logger.warning("[triage] semantic enhancement failed, serving AST-only: %s", exc)
        return None

    if not result:
        return None

    enrichment = {
        "semantic_root_cause": result.get("root_cause_summary"),
        "affected_subsystems": result.get("affected_subsystems") or [],
        "investigation_entrypoint": result.get("investigation_entrypoint"),
        "rationale": result.get("rationale"),
        "confidence_score": _clamp01(result.get("confidence_score")),
        "provider": result.get("_provider"),
        # Files whose real source grounded this analysis (empty => issue-text only).
        "grounded_files": grounded_files,
    }
    # A result with no usable diagnosis is treated as a miss (stay AST-only). The model
    # returned parseable JSON but omitted root_cause_summary — log its keys so this second
    # silent-miss path (distinct from an unparseable body) is diagnosable in prod.
    if not enrichment["semantic_root_cause"]:
        logger.warning(
            "[triage] LLM (%s) returned JSON without root_cause_summary; keys=%s",
            result.get("_provider"), sorted(k for k in result if k != "_provider"),
        )
        return None

    await set_cached_json(
        cache_key, enrichment, ttl_seconds=int(getattr(settings, "LLM_CACHE_TTL_SECONDS", 604800))
    )
    return enrichment
