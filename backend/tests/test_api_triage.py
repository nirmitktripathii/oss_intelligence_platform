"""Unit tests for the AI Triage & Diagnostics API endpoints."""

import json

import pytest
import httpx

from app.config import settings as app_settings
from app.triage.llm_engine import LLMTriageEngine

_LLM_KEYS = ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL")


def _force_ast_only(monkeypatch):
    """Null every provider so the enhancement layer degrades to deterministic AST."""
    for key in _LLM_KEYS:
        monkeypatch.setattr(app_settings, key, None)


def _force_gemini(monkeypatch, canned_result: dict):
    """Configure a provider and stub the transport so the real enhancement path runs."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "test-key")

    async def fake_provenance(prompt, system_prompt=None, temperature=0.2):
        return json.dumps(canned_result), "gemini:gemini-2.0-flash"

    monkeypatch.setattr(
        LLMTriageEngine, "query_llm_with_provenance", staticmethod(fake_provenance)
    )


@pytest.mark.asyncio
async def test_get_existing_triage_report(client: httpx.AsyncClient, seed_sample_issues):
    """Retrieve pre-existing triage report for an issue."""
    response = await client.get("/api/v1/triage/fastapi/fastapi%231001")
    assert response.status_code == 200
    data = response.json()
    assert data["issue_id"] == "fastapi/fastapi#1001"
    assert "solve_dependencies" in data["localized_files"][0]["rationale"]
    assert len(data["fix_plan_steps"]) >= 1
    assert data["reproduction_lang"] == "python"


@pytest.mark.asyncio
async def test_get_triage_dynamic_generation(client: httpx.AsyncClient, seed_sample_issues):
    """Automatically generate triage for an issue that lacks a precomputed report."""
    response = await client.get("/api/v1/triage/langchain-ai/langchain%232002")
    assert response.status_code == 200
    data = response.json()
    assert data["issue_id"] == "langchain-ai/langchain#2002"
    assert len(data["localized_files"]) > 0
    assert len(data["fix_plan_steps"]) == 4
    assert "ChatPromptTemplate" in data["root_cause_analysis"] or "langchain" in data["summary"].lower()


@pytest.mark.asyncio
async def test_get_triage_not_found(client: httpx.AsyncClient, seed_sample_issues):
    """Verify 404 for non-existent issue triage request."""
    response = await client.get("/api/v1/triage/unknown/repo%239999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_on_demand_triage(client: httpx.AsyncClient):
    """Test generating on-demand AST triage from custom error reports."""
    payload = {
        "repo_owner": "fastapi",
        "repo_name": "fastapi",
        "issue_number": 8888,
        "title": "AttributeError in APIRoute endpoint resolution",
        "body": "Traceback (most recent call last):\n  File \"fastapi/routing.py\", line 180, in get_app\n    return self.app\nAttributeError: 'NoneType' object has no attribute 'app'",
        "primary_language": "Python",
    }
    response = await client.post("/api/v1/triage/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["issue_id"] == "fastapi/fastapi#8888"
    assert len(data["localized_files"]) >= 1
    assert data["localized_files"][0]["file_path"] == "fastapi/routing.py"
    assert data["localized_files"][0]["confidence"] > 0.8
    assert len(data["fix_plan_steps"]) == 4
    assert data["reproduction_code"] != ""


# ── AI semantic enhancement layer ──────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_triage_degrades_to_ast_only_without_provider(
    client: httpx.AsyncClient, seed_sample_issues, monkeypatch
):
    """No LLM provider configured => honest AST-only report, real AST-floor confidence."""
    _force_ast_only(monkeypatch)
    response = await client.get("/api/v1/triage/kubernetes/kubernetes%234004")
    assert response.status_code == 200
    data = response.json()

    assert data["llm_enhanced"] is False
    assert data["llm_analysis"] is None
    # Confidence is the real top AST localization score, never a fabricated placeholder.
    expected = max(f["confidence"] for f in data["localized_files"])
    assert data["triage_confidence"] == pytest.approx(expected)


@pytest.mark.asyncio
async def test_triage_ai_enhanced_when_provider_configured(
    client: httpx.AsyncClient, seed_sample_issues, monkeypatch
):
    """With a provider configured, the report is enriched and confidence is the LLM's score."""
    canned = {
        "root_cause_summary": "None is passed unguarded into ChatPromptTemplate substitution.",
        "affected_subsystems": ["Prompt templating"],
        "confidence_score": 0.83,
        "investigation_entrypoint": "langchain/prompts/chat.py",
        "rationale": "The format path lacks a None guard before .format().",
    }
    _force_gemini(monkeypatch, canned)

    response = await client.get("/api/v1/triage/langchain-ai/langchain%232002")
    assert response.status_code == 200
    data = response.json()

    assert data["llm_enhanced"] is True
    assert data["llm_analysis"]["semantic_root_cause"] == canned["root_cause_summary"]
    assert data["llm_analysis"]["provider"] == "gemini:gemini-2.0-flash"
    assert data["llm_analysis"]["affected_subsystems"] == ["Prompt templating"]
    # Real triage confidence is the model's calibrated score, not the AST floor.
    assert data["triage_confidence"] == pytest.approx(0.83)
    # The deterministic floor is still present alongside the AI enrichment.
    assert data["root_cause_analysis"]


@pytest.mark.asyncio
async def test_on_demand_triage_ai_enhanced(client: httpx.AsyncClient, monkeypatch):
    """The on-demand endpoint also enriches when a provider is configured."""
    canned = {
        "root_cause_summary": "Endpoint resolution dereferences a None APIRoute.",
        "affected_subsystems": ["Routing"],
        "confidence_score": 0.71,
        "investigation_entrypoint": "fastapi/routing.py",
        "rationale": "self.app is None when the route failed to mount.",
    }
    _force_gemini(monkeypatch, canned)

    payload = {
        "repo_owner": "fastapi",
        "repo_name": "fastapi",
        "issue_number": 8888,
        "title": "AttributeError in APIRoute endpoint resolution",
        "body": "Traceback:\n  File \"fastapi/routing.py\", line 180, in get_app\nAttributeError: 'NoneType' object has no attribute 'app'",
        "primary_language": "Python",
    }
    response = await client.post("/api/v1/triage/generate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["llm_enhanced"] is True
    assert data["triage_confidence"] == pytest.approx(0.71)
    assert data["llm_analysis"]["provider"] == "gemini:gemini-2.0-flash"


def test_resolve_chain_gating(monkeypatch):
    """No keys => empty chain (AST-only); a key => that provider is selected."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    assert LLMTriageEngine.resolve_chain() == []

    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")
    chain = LLMTriageEngine.resolve_chain()
    assert chain and chain[0][0] == "gemini"


def test_resolve_chain_master_switch_off(monkeypatch):
    """LLM_TRIAGE_ENABLED=False forces AST-only even when a key is present."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", False)
    assert LLMTriageEngine.resolve_chain() == []


def test_coerce_json_tolerates_fences_and_prose():
    """Model output wrapped in ```json fences or prose is still parsed."""
    assert LLMTriageEngine._coerce_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert LLMTriageEngine._coerce_json('Here you go: {"a": 2} done') == {"a": 2}
    assert LLMTriageEngine._coerce_json("not json at all") is None
