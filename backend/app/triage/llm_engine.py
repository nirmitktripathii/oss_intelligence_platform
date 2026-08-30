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

[OUTPUT FORMAT]
Respond in valid JSON:
{{
    "root_cause_summary": "Concise 2-3 sentence technical diagnosis of why the bug occurs.",
    "affected_subsystems": ["Subsystem 1", "Subsystem 2"],
    "confidence_score": 0.94,
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
    """Invokes LLM providers with fallback to deterministic AST templates."""

    @classmethod
    async def query_llm(
        cls,
        prompt: str,
        system_prompt: str = TRIAGE_SYSTEM_PROMPT,
        temperature: float = 0.2,
    ) -> Optional[str]:
        """
        Executes an LLM completion using configured provider (OpenAI, Gemini, Anthropic, or Ollama).
        Returns raw response text or None if no API keys are configured.
        """
        # 1. OpenAI / Compatible Endpoint
        openai_key = getattr(settings, "OPENAI_API_KEY", None)
        if openai_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": temperature,
                            "response_format": {"type": "json_object"},
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
            except Exception as exc:
                logger.warning(f"[LLM] OpenAI invocation failed: {exc}")

        # 2. Google Gemini API Endpoint
        gemini_key = getattr(settings, "GEMINI_API_KEY", None)
        if gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                async with httpx.AsyncClient(timeout=30.0) as client:
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
            except Exception as exc:
                logger.warning(f"[LLM] Gemini invocation failed: {exc}")

        # 3. Local Ollama Fallback (if running locally at http://localhost:11434)
        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": f"{system_prompt}\n\n{prompt}",
                        "stream": False,
                        "format": "json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response")
        except Exception:
            pass  # Ollama not running locally

        return None

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
    ) -> Optional[Dict[str, Any]]:
        """Invokes LLM with ROOT_CAUSE_PROMPT_TEMPLATE."""
        prompt = ROOT_CAUSE_PROMPT_TEMPLATE.format(
            repo_owner=repo_owner,
            repo_name=repo_name,
            language=language,
            tech_stack=", ".join(tech_stack),
            issue_number=issue_number,
            title=title,
            body=(body or "")[:2000],
            localized_files_json=json.dumps(localized_files, indent=2),
        )
        raw_json = await cls.query_llm(prompt)
        if raw_json:
            try:
                return json.loads(raw_json)
            except Exception:
                pass
        return None

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
        raw_json = await cls.query_llm(prompt)
        if raw_json:
            try:
                return json.loads(raw_json)
            except Exception:
                pass
        return None

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
        raw_json = await cls.query_llm(prompt)
        if raw_json:
            try:
                return json.loads(raw_json)
            except Exception:
                pass
        return None
