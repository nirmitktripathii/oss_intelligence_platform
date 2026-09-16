"""
Semantic enhancement layer for AI triage.

Wraps the deterministic AST triage with a *real* LLM enrichment when a free-tier
provider is configured, and derives a real, sortable triage confidence. Every path
degrades honestly: if the LLM is disabled, unconfigured, rate-limited, or returns
nothing usable, ``semantic_enhance`` returns ``None`` and the caller keeps the
deterministic AST result. Nothing here fabricates an AI answer.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.cache import get_cached_json, set_cached_json
from app.config import settings
from app.scrapers.github_client import GitHubClient
from app.triage.llm_engine import LLMTriageEngine

logger = logging.getLogger("gitscout.triage.enhancer")

# Bump when the shape of the enrichment dict changes so stale (root-cause-only) cache
# entries are ignored and re-synthesized with the richer repro/patch/contributing fields.
ENRICHMENT_SCHEMA_VERSION = "v2"

# Where real CONTRIBUTING guides commonly live, in priority order.
_CONTRIBUTING_CANDIDATES = [
    "CONTRIBUTING.md",
    ".github/CONTRIBUTING.md",
    "docs/CONTRIBUTING.md",
    "CONTRIBUTING.rst",
    "CONTRIBUTING",
]

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


def _normalize_ranked_files(
    ranked: Any, localized_files: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Normalize the LLM's ``ranked_files`` into [{file_path, priority, reason}], keeping only
    paths that actually appear in the AST-localized candidates (never a hallucinated path).
    Returns [] when the model gave nothing usable — the frontend then shows the AST order.
    """
    if not isinstance(ranked, list):
        return []
    known = {(lf.get("file_path") or "").strip() for lf in localized_files if isinstance(lf, dict)}
    out: List[Dict[str, Any]] = []
    for item in ranked:
        if not isinstance(item, dict):
            continue
        path = str(item.get("file_path") or "").strip()
        if not path or (known and path not in known):
            continue
        try:
            priority = int(item.get("priority") or 2)
        except (TypeError, ValueError):
            priority = 2
        out.append({
            "file_path": path,
            "priority": max(1, min(3, priority)),
            "reason": str(item.get("reason") or "").strip(),
        })
    return out


async def fetch_contributing(
    repo_owner: str, repo_name: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch the repo's real CONTRIBUTING guide (first candidate that resolves), Upstash-cached.
    Returns (text, source_path) or (None, None). Best-effort — never raises.
    """
    cache_key = f"gitscout:contributing:{repo_owner}/{repo_name}"
    cached = await get_cached_json(cache_key)
    if isinstance(cached, dict) and "text" in cached:
        return cached.get("text"), cached.get("source_path")

    client = GitHubClient()
    ttl = int(getattr(settings, "CONTRIBUTING_CACHE_TTL_SECONDS", 604800))
    for candidate in _CONTRIBUTING_CANDIDATES:
        try:
            text = await client.fetch_file_content(repo_owner, repo_name, candidate)
        except Exception as exc:  # never let a fetch break enhancement
            logger.debug("contributing fetch error for %s: %s", candidate, exc)
            text = None
        if text and text.strip():
            await set_cached_json(cache_key, {"text": text, "source_path": candidate}, ttl_seconds=ttl)
            return text, candidate
    # Cache the negative result briefly so we don't re-probe every view.
    await set_cached_json(cache_key, {"text": None, "source_path": None}, ttl_seconds=min(ttl, 86400))
    return None, None


async def _synth_reproduction(
    *, repo_owner: str, repo_name: str, issue_number: int, title: str,
    body: Optional[str], body_summary: Optional[str], language: str, source_context: str,
) -> Optional[Dict[str, Any]]:
    """Grounded LLM reproduction script, normalized, or None to keep the deterministic scaffold."""
    if not getattr(settings, "LLM_SYNTH_REPRO", True):
        return None
    try:
        result = await LLMTriageEngine.synthesize_reproduction_script(
            repo_owner=repo_owner, repo_name=repo_name, issue_number=issue_number,
            title=title, body=body or "", language=language,
            source_context=source_context, body_summary=body_summary,
        )
    except Exception as exc:
        logger.warning("[triage] repro synthesis failed, keeping scaffold: %r", exc)
        return None
    if not result or not str(result.get("code") or "").strip():
        return None
    return {
        "language": result.get("language") or language,
        "filename": result.get("filename"),
        "code": result.get("code"),
        "cli_command": result.get("cli_command"),
        "expected_failure": result.get("expected_failure"),
        "provider": result.get("_provider"),
    }


async def _synth_patch(
    *, repo_owner: str, repo_name: str, issue_number: int, title: str,
    body: Optional[str], body_summary: Optional[str], primary_file: str, source_context: str,
) -> Optional[Dict[str, Any]]:
    """Grounded LLM unified-diff patch, normalized, or None to omit the patch card."""
    if not getattr(settings, "LLM_SYNTH_PATCH", True) or not primary_file:
        return None
    try:
        result = await LLMTriageEngine.synthesize_code_patch(
            repo_owner=repo_owner, repo_name=repo_name, issue_number=issue_number,
            title=title, body=body or "", primary_file=primary_file,
            source_context=source_context, body_summary=body_summary,
        )
    except Exception as exc:
        logger.warning("[triage] patch synthesis failed, omitting patch: %r", exc)
        return None
    if not result or not str(result.get("diff_snippet") or "").strip():
        return None
    return {
        "primary_file": primary_file,
        "diff_snippet": result.get("diff_snippet"),
        "explanation": result.get("explanation"),
        "regression_risk": result.get("regression_risk"),
        "provider": result.get("_provider"),
    }


async def _build_contributing(
    *, repo_owner: str, repo_name: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch the repo's REAL CONTRIBUTING guide and summarize it into concrete rule bullets.
    Returns {guidelines, source_path, source_url} or None (caller keeps the template).
    """
    if not getattr(settings, "LLM_CONTRIBUTING", True):
        return None
    text, source_path = await fetch_contributing(repo_owner, repo_name)
    if not text or not source_path:
        return None
    try:
        bullets = await LLMTriageEngine.summarize_contributing(
            repo_owner, repo_name, text, source_path
        )
    except Exception as exc:
        logger.warning("[triage] contributing summary failed: %r", exc)
        bullets = None
    if not bullets:
        return None
    return {
        "guidelines": bullets,
        "source_path": source_path,
        "source_url": f"https://github.com/{repo_owner}/{repo_name}/blob/HEAD/{source_path}",
        # The chain that served this run — same provider that produced the other cards.
        "provider": LLMTriageEngine.active_provider_label(),
    }


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

    # Version the cache key so stale root-cause-only entries (schema v1) are ignored and
    # re-synthesized with the richer repro/patch/contributing/reranked fields. The version is
    # injected INSIDE the "gitscout:" namespace (-> "gitscout:v2:...") so the app's own
    # invalidate_cache_pattern("gitscout:*") still clears enrichment entries.
    if cache_key.startswith("gitscout:"):
        versioned_key = f"gitscout:{ENRICHMENT_SCHEMA_VERSION}:{cache_key[len('gitscout:'):]}"
    else:
        versioned_key = f"gitscout:{ENRICHMENT_SCHEMA_VERSION}:{cache_key}"
    cached = await get_cached_json(versioned_key)
    if isinstance(cached, dict) and cached.get("semantic_root_cause"):
        return cached

    # Real-code grounding: fetch the localized files' actual source once, reused by the
    # root-cause, reproduction, and patch prompts so the free-tier quota buys one fetch.
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
        "schema_version": ENRICHMENT_SCHEMA_VERSION,
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

    # LLM re-ranking of the AST candidates (no extra call — it rode along with the root
    # cause). Kept only for paths that exist in the AST candidates; [] => frontend uses
    # the deterministic AST order.
    reranked = _normalize_ranked_files(result.get("ranked_files"), localized_files)
    enrichment["localized_reranked"] = reranked

    # Pick the primary edit target for the patch. Prefer the highest-ranked file we actually
    # fetched source for (so the diff is grounded), then any grounded file, then the model's
    # top pick, then the top AST candidate.
    grounded_set = set(grounded_files)
    primary_file = ""
    for rf in reranked:
        if rf["file_path"] in grounded_set:
            primary_file = rf["file_path"]
            break
    if not primary_file and grounded_files:
        primary_file = grounded_files[0]
    if not primary_file and reranked:
        primary_file = reranked[0]["file_path"]
    if not primary_file:
        for lf in localized_files:
            p = (lf.get("file_path") or "").strip() if isinstance(lf, dict) else ""
            if p:
                primary_file = p
                break

    # Grounded reproduction, grounded patch diff, and the repo's REAL CONTRIBUTING guide, all
    # in parallel — one wall-clock round trip instead of three. return_exceptions keeps a
    # single failed synth from cancelling the others; each helper already degrades to None.
    repro_res, patch_res, contributing_res = await asyncio.gather(
        _synth_reproduction(
            repo_owner=repo_owner, repo_name=repo_name, issue_number=issue_number,
            title=title, body=body, body_summary=body_summary, language=language,
            source_context=source_context,
        ),
        _synth_patch(
            repo_owner=repo_owner, repo_name=repo_name, issue_number=issue_number,
            title=title, body=body, body_summary=body_summary, primary_file=primary_file,
            source_context=source_context,
        ),
        _build_contributing(repo_owner=repo_owner, repo_name=repo_name),
        return_exceptions=True,
    )

    def _ok(res: Any) -> Optional[Dict[str, Any]]:
        """A dict result is usable; an Exception (from return_exceptions) or None is a miss."""
        if isinstance(res, Exception):
            logger.warning("[triage] parallel synth raised: %r", res)
            return None
        return res if isinstance(res, dict) else None

    enrichment["reproduction"] = _ok(repro_res)
    enrichment["patch"] = _ok(patch_res)
    enrichment["contributing"] = _ok(contributing_res)

    await set_cached_json(
        versioned_key, enrichment, ttl_seconds=int(getattr(settings, "LLM_CACHE_TTL_SECONDS", 604800))
    )
    return enrichment
