"""
Semantic enhancement layer for AI triage.

Wraps the deterministic AST triage with a *real* LLM enrichment when a free-tier
provider is configured, and derives a real, sortable triage confidence. Every path
degrades honestly: if the LLM is disabled, unconfigured, rate-limited, or returns
nothing usable, ``semantic_enhance`` returns ``None`` and the caller keeps the
deterministic AST result. Nothing here fabricates an AI answer.
"""

import logging
from typing import Any, Dict, List, Optional

from app.cache import get_cached_json, set_cached_json
from app.config import settings
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


async def semantic_enhance(
    *,
    cache_key: str,
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    title: str,
    body: Optional[str],
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

    try:
        result = await LLMTriageEngine.synthesize_semantic_root_cause(
            repo_owner=repo_owner,
            repo_name=repo_name,
            issue_number=issue_number,
            title=title,
            body=body,
            language=language,
            tech_stack=tech_stack,
            localized_files=localized_files,
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
    }
    # A result with no usable diagnosis is treated as a miss (stay AST-only).
    if not enrichment["semantic_root_cause"]:
        return None

    await set_cached_json(
        cache_key, enrichment, ttl_seconds=int(getattr(settings, "LLM_CACHE_TTL_SECONDS", 604800))
    )
    return enrichment
