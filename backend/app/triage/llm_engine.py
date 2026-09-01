"""
LLM Semantic Triage & Prompt Engine for GitScout.
Provides structured prompt engineering, system instructions, and multi-provider LLM invocations
(OpenAI, Google Gemini, Anthropic, or local Ollama) for root cause analysis, code diff synthesis,
and standalone bug reproduction generation.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. SYSTEM PROMPTS & INSTRUCTION SETS
# ==============================================================================

TRIAGE_SYSTEM_PROMPT = """You are GitScout AI, a Principal Staff Software Engineer and Open-Source Triage Expert.
Your job is to analyze reported GitHub issues, examine abstract syntax tree (AST) candidate files,
and generate high-precision diagnostic breakdowns, minimal bug reproduction scripts, and unified git diffs.

RULES:
1. Strictly respect the target repository's programming language, design patterns, and conventions.
2. Ground all file references and line numbers in the provided AST localized files—DO NOT hallucinate non-existent files.
3. Keep reproduction scripts minimal, self-contained, and executable with standard test runners (pytest, jest, cargo test).
4. Output valid JSON adhering strictly to the requested schema.
"""

# ==============================================================================
# 2. STRUCTURED PROMPT TEMPLATES
# ==============================================================================

ROOT_CAUSE_PROMPT_TEMPLATE = """### TASK: ROOT CAUSE DIAGNOSIS & SUBSYSTEM ANALYSIS
Analyze the following open-source issue and determine the exact underlying cause of the failure.

[REPOSITORY CONTEXT]
Repository: {repo_owner}/{repo_name}
Primary Language: {language}
Tech Stack: {tech_stack}

[ISSUE DETAILS]
Issue #{issue_number}: {title}
Description:
\"\"\"
{body}
\"\"\"

[AST LOCALIZED CANDIDATE FILES]
{localized_files_json}

[GROUNDED SOURCE CODE]
Actual source fetched from the repository around the localized lines (line-numbered).
Base your diagnosis, file references, and any line numbers strictly on THIS code. If this
section is empty, say the analysis is based on the issue text alone and lower your confidence.
{source_context}

[OUTPUT FORMAT]
Respond in valid JSON. Set "confidence_score" to your genuine calibrated certainty in the
root-cause identification on a 0.0-1.0 scale — low when the issue text is vague or no stack
trace / file reference was provided, high only when the evidence is strong. Never default to a
fixed number.
{{
    "root_cause_summary": "Concise 2-3 sentence technical diagnosis of why the bug occurs.",
    "affected_subsystems": ["Subsystem 1", "Subsystem 2"],
    "confidence_score": 0.0,
    "investigation_entrypoint": "path/to/primary/file.py",
    "rationale": "Why this specific file/function is the root cause."
}}
"""

CODE_PATCH_DIFF_PROMPT_TEMPLATE = """### TASK: SYNTHESIZE UNIFIED CODE PATCH DIFF
Generate a production-ready git diff patch to fix the reported issue in accordance with the repository's CONTRIBUTING guidelines.

[REPOSITORY]
Repository: {repo_owner}/{repo_name}
Target File: {primary_file}
Issue: #{issue_number} - {title}

[PROBLEM DESCRIPTION]
{body}

[OUTPUT FORMAT]
Respond in valid JSON:
{{
    "diff_snippet": "--- a/{primary_file}\n+++ b/{primary_file}\n@@ ... @@\n+ ...",
    "explanation": "Explanation of the logic change and boundary guard added.",
    "regression_risk": "Low/Medium/High with justification"
}}
"""

REPRO_SYNTHESIS_PROMPT_TEMPLATE = """### TASK: GENERATE MINIMAL STANDALONE BUG REPRODUCTION
Synthesize an isolated, executable test script that reliably reproduces the reported failure.

[REPOSITORY]
Repository: {repo_owner}/{repo_name}
Language: {language}
Issue #{issue_number}: {title}

[ERROR LOGS / DESCRIPTION]
{body}

[OUTPUT FORMAT]
Respond in valid JSON:
{{
    "language": "{language}",
    "filename": "reproduce_{repo_name}_issue.py",
    "code": "# Standalone test script with assertions\n...",
    "cli_command": "pytest reproduce_{repo_name}_issue.py -v",
    "expected_failure": "Specific exception or assertion failure expected before applying fix"
}}
"""


# ==============================================================================
# 3. LLM INVOCATION & ORCHESTRATION PIPELINE
# ==============================================================================

class LLMTriageEngine:
    """
    Invokes a free-tier-friendly LLM provider as an *enhancement layer* over the
    deterministic AST triage. Provider and model are configuration-driven; when no
    provider is configured every method returns ``None`` so callers keep the
    deterministic result rather than fabricating one.
    """

    # Default model per provider (all reachable on a free tier). Override with LLM_MODEL.
    # Gemini/Gemma default to the free-tier flash-lite; other free Gemma options via the
    # same Gemini API: gemini-3.1-flash-lite, gemma-4-26b-a4b-it, gemma-4-31b-it. Groq's
    # free tier does not carry Llama 3.3, so default to an available general model.
    PROVIDER_DEFAULTS: Dict[str, str] = {
        "gemini": "gemini-3.5-flash-lite",
        "groq": "openai/gpt-oss-120b",
        "openai": "gpt-4o-mini",
        "ollama": "llama3.2",
    }

    # ------------------------------------------------------------------ #
    # Provider resolution
    # ------------------------------------------------------------------ #
    @classmethod
    def _provider_available(cls, provider: str) -> bool:
        if provider == "gemini":
            return bool(getattr(settings, "GEMINI_API_KEY", None))
        if provider == "groq":
            return bool(getattr(settings, "GROQ_API_KEY", None))
        if provider == "openai":
            return bool(getattr(settings, "OPENAI_API_KEY", None))
        if provider == "ollama":
            return bool(getattr(settings, "OLLAMA_BASE_URL", None))
        return False

    @classmethod
    def resolve_chain(cls) -> List[tuple]:
        """
        Ordered list of ``(provider, model)`` to attempt. Respects a forced
        ``LLM_PROVIDER`` if set and available, otherwise auto-selects every
        configured provider (Ollama last, and only when its URL is set — so the
        old unconditional localhost probe never runs on a deployed backend).
        """
        if not getattr(settings, "LLM_TRIAGE_ENABLED", True):
            return []
        model_override = getattr(settings, "LLM_MODEL", None)
        forced = (getattr(settings, "LLM_PROVIDER", None) or "").strip().lower()
        order = [forced] if forced in cls.PROVIDER_DEFAULTS else ["gemini", "groq", "openai", "ollama"]
        chain: List[tuple] = []
        for provider in order:
            if cls._provider_available(provider):
                chain.append((provider, model_override or cls.PROVIDER_DEFAULTS[provider]))
        return chain

    @classmethod
    def active_provider_label(cls) -> Optional[str]:
        """Human-readable label of the provider that would serve a request, or None."""
        chain = cls.resolve_chain()
        return f"{chain[0][0]}:{chain[0][1]}" if chain else None

    # ------------------------------------------------------------------ #
    # Robust JSON coercion (models sometimes wrap output in prose/fences)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _coerce_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        candidate = text.strip()
        # Strip ```json ... ``` / ``` ... ``` fences if present
        if candidate.startswith("```"):
            candidate = candidate.split("```", 2)[1] if candidate.count("```") >= 2 else candidate
            if candidate.lstrip().lower().startswith("json"):
                candidate = candidate.lstrip()[4:]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        # Fallback: extract the first balanced {...} object
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except Exception:
                return None
        return None

    # ------------------------------------------------------------------ #
    # Provider transports
    # ------------------------------------------------------------------ #
    @classmethod
    async def _call_openai_compatible(
        cls, provider: str, model: str, system_prompt: str, prompt: str, temperature: float
    ) -> Optional[str]:
        if provider == "groq":
            base_url, key = "https://api.groq.com/openai/v1", getattr(settings, "GROQ_API_KEY", None)
        else:
            base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
            key = getattr(settings, "OPENAI_API_KEY", None)
        if not key:
            return None
        timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 20.0))
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            logger.warning("[LLM] %s returned HTTP %s", provider, resp.status_code)
        return None

    @classmethod
    async def _call_gemini(
        cls, model: str, system_prompt: str, prompt: str, temperature: float
    ) -> Optional[str]:
        key = getattr(settings, "GEMINI_API_KEY", None)
        if not key:
            return None
        timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 20.0))
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
                    "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            logger.warning("[LLM] gemini returned HTTP %s", resp.status_code)
        return None

    @classmethod
    async def _call_ollama(
        cls, model: str, system_prompt: str, prompt: str, temperature: float
    ) -> Optional[str]:
        base = getattr(settings, "OLLAMA_BASE_URL", None)
        if not base:
            return None
        timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 20.0))
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
            )
            if resp.status_code == 200:
                return resp.json().get("response")
        return None

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #
    @classmethod
    async def query_llm_with_provenance(
        cls,
        prompt: str,
        system_prompt: str = TRIAGE_SYSTEM_PROMPT,
        temperature: float = 0.2,
    ) -> Optional[tuple]:
        """
        Try each configured provider in order. Returns ``(raw_text, "provider:model")``
        on the first success, or ``None`` when nothing is configured / every call fails.
        """
        for provider, model in cls.resolve_chain():
            try:
                if provider in ("openai", "groq"):
                    text = await cls._call_openai_compatible(provider, model, system_prompt, prompt, temperature)
                elif provider == "gemini":
                    text = await cls._call_gemini(model, system_prompt, prompt, temperature)
                elif provider == "ollama":
                    text = await cls._call_ollama(model, system_prompt, prompt, temperature)
                else:
                    text = None
                if text:
                    return text, f"{provider}:{model}"
            except Exception as exc:  # never let a provider failure escape — degrade to AST
                logger.warning("[LLM] %s invocation failed: %s", provider, exc)
        return None

    @classmethod
    async def query_llm(
        cls,
        prompt: str,
        system_prompt: str = TRIAGE_SYSTEM_PROMPT,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """Backwards-compatible text-only wrapper around :meth:`query_llm_with_provenance`."""
        result = await cls.query_llm_with_provenance(prompt, system_prompt, temperature)
        return result[0] if result else None

    @classmethod
    async def synthesize_semantic_root_cause(
        cls,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: str,
        body: str,
        language: str,
        tech_stack: List[str],
        localized_files: List[Dict[str, Any]],
        source_context: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke the LLM with ROOT_CAUSE_PROMPT_TEMPLATE and return the parsed result
        stamped with the ``_provider`` that produced it, or ``None`` to keep AST-only.
        ``source_context`` is the real repository code fetched for grounding (may be empty).
        """
        prompt = ROOT_CAUSE_PROMPT_TEMPLATE.format(
            repo_owner=repo_owner,
            repo_name=repo_name,
            language=language,
            tech_stack=", ".join(tech_stack),
            issue_number=issue_number,
            title=title,
            body=(body or "")[:2000],
            localized_files_json=json.dumps(localized_files, indent=2),
            source_context=source_context.strip() or "(no source could be fetched for the localized files)",
        )
        result = await cls.query_llm_with_provenance(prompt)
        if not result:
            return None
        raw_json, provider_label = result
        parsed = cls._coerce_json(raw_json)
        if parsed is None:
            return None
        parsed["_provider"] = provider_label
        return parsed

    @classmethod
    async def synthesize_code_patch(
        cls,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: str,
        body: str,
        primary_file: str,
    ) -> Optional[Dict[str, Any]]:
        """Invokes LLM with CODE_PATCH_DIFF_PROMPT_TEMPLATE."""
        prompt = CODE_PATCH_DIFF_PROMPT_TEMPLATE.format(
            repo_owner=repo_owner,
            repo_name=repo_name,
            primary_file=primary_file,
            issue_number=issue_number,
            title=title,
            body=(body or "")[:2000],
        )
        result = await cls.query_llm_with_provenance(prompt)
        if not result:
            return None
        parsed = cls._coerce_json(result[0])
        if parsed is not None:
            parsed["_provider"] = result[1]
        return parsed

    @classmethod
    async def synthesize_reproduction_script(
        cls,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: str,
        body: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        """Invokes LLM with REPRO_SYNTHESIS_PROMPT_TEMPLATE."""
        prompt = REPRO_SYNTHESIS_PROMPT_TEMPLATE.format(
            repo_owner=repo_owner,
            repo_name=repo_name,
            language=language,
            issue_number=issue_number,
            title=title,
            body=(body or "")[:2000],
        )
        result = await cls.query_llm_with_provenance(prompt)
        if not result:
            return None
        parsed = cls._coerce_json(result[0])
        if parsed is not None:
            parsed["_provider"] = result[1]
        return parsed
