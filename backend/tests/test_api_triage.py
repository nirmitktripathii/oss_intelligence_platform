"""Unit tests for the AI Triage & Diagnostics API endpoints."""

import json

import pytest
import httpx

from app.config import settings as app_settings
from app.scrapers.github_client import GitHubClient
from app.triage import llm_engine
from app.triage.llm_engine import LLMTriageEngine

_LLM_KEYS = (
    "AWS_BEARER_TOKEN_BEDROCK", "BEDROCK_AWS_PROFILE",
    "GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL",
)


def _force_ast_only(monkeypatch):
    """Null every provider so the enhancement layer degrades to deterministic AST."""
    for key in _LLM_KEYS:
        monkeypatch.setattr(app_settings, key, None)


def _stub_no_source(monkeypatch):
    """Stub GitHub source fetching so enhancement tests never hit the network."""
    async def _none(self, owner, repo, path, ref=None):
        return None

    monkeypatch.setattr(GitHubClient, "fetch_file_content", _none)


def _force_gemini(monkeypatch, canned_result: dict):
    """Configure a provider and stub the transport so the real enhancement path runs."""
    _force_ast_only(monkeypatch)
    _stub_no_source(monkeypatch)  # keep hermetic; grounding tests override this
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "test-key")

    async def fake_provenance(prompt, system_prompt=None, temperature=0.2):
        return json.dumps(canned_result), "gemini:gemini-3.5-flash-lite"

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
    assert data["llm_analysis"]["provider"] == "gemini:gemini-3.5-flash-lite"
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
    assert data["llm_analysis"]["provider"] == "gemini:gemini-3.5-flash-lite"


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


# ── Amazon Bedrock provider ─────────────────────────────────────────────────── #


def test_resolve_chain_bedrock_leads_with_its_own_model(monkeypatch):
    """Bedrock goes first when configured, and a shared LLM_MODEL never leaks into it."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    monkeypatch.setattr(app_settings, "LLM_PROVIDER", None)
    monkeypatch.setattr(app_settings, "BEDROCK_MODEL_ID", None)
    monkeypatch.setattr(app_settings, "LLM_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(app_settings, "BEDROCK_AWS_PROFILE", "hackathon")

    chain = LLMTriageEngine.resolve_chain()
    assert chain[0] == ("bedrock", "us.amazon.nova-2-lite-v1:0")
    assert chain[1] == ("gemini", "gemini-3.5-flash-lite")

    monkeypatch.setattr(app_settings, "BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
    assert LLMTriageEngine.resolve_chain()[0] == ("bedrock", "us.amazon.nova-pro-v1:0")


def test_bedrock_enabled_by_api_key_alone(monkeypatch):
    """A Bedrock API key (no profile) is enough to enable the provider, as on Render."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    monkeypatch.setattr(app_settings, "LLM_PROVIDER", None)
    monkeypatch.setattr(app_settings, "AWS_BEARER_TOKEN_BEDROCK", "x")
    assert LLMTriageEngine.resolve_chain()[0][0] == "bedrock"


@pytest.mark.asyncio
async def test_call_bedrock_sends_max_tokens_and_returns_text_only(monkeypatch):
    """Converse gets an explicit maxTokens + system prompt; non-text blocks are dropped."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "BEDROCK_AWS_PROFILE", "hackathon")
    monkeypatch.setattr(app_settings, "BEDROCK_MAX_TOKENS", 1234)
    captured = {}

    class FakeClient:
        def converse(self, **kwargs):
            captured.update(kwargs)
            return {
                "stopReason": "end_turn",
                "output": {"message": {"content": [
                    {"reasoningContent": {"reasoningText": {"text": "thinking..."}}},
                    {"text": '{"ok": true}'},
                ]}},
            }

    monkeypatch.setattr(llm_engine, "_bedrock_client", lambda *a, **k: FakeClient())
    text = await LLMTriageEngine._call_bedrock("us.amazon.nova-2-lite-v1:0", "SYS", "PROMPT", 0.2)

    assert text == '{"ok": true}'
    assert captured["modelId"] == "us.amazon.nova-2-lite-v1:0"
    assert captured["system"] == [{"text": "SYS"}]
    assert captured["inferenceConfig"] == {"maxTokens": 1234, "temperature": 0.2}


@pytest.mark.asyncio
async def test_bedrock_failure_falls_back_to_next_provider(monkeypatch):
    """A Bedrock error (e.g. AccessDenied) degrades to the next provider, never raises."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    monkeypatch.setattr(app_settings, "LLM_PROVIDER", None)
    monkeypatch.setattr(app_settings, "LLM_MODEL", None)
    monkeypatch.setattr(app_settings, "BEDROCK_AWS_PROFILE", "hackathon")
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")

    async def boom(*args, **kwargs):
        raise RuntimeError("AccessDeniedException")

    async def gemini_ok(*args, **kwargs):
        return '{"ok": true}'

    monkeypatch.setattr(LLMTriageEngine, "_call_bedrock", boom)
    monkeypatch.setattr(LLMTriageEngine, "_call_gemini", gemini_ok)
    text, provider = await LLMTriageEngine.query_llm_with_provenance("PROMPT")
    assert provider == "gemini:gemini-3.5-flash-lite"


@pytest.mark.asyncio
async def test_failing_provider_is_skipped_during_cooldown(monkeypatch):
    """A provider that raised is not retried on every request while another can answer."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    monkeypatch.setattr(app_settings, "LLM_PROVIDER", None)
    monkeypatch.setattr(app_settings, "LLM_MODEL", None)
    monkeypatch.setattr(app_settings, "BEDROCK_AWS_PROFILE", "hackathon")
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(app_settings, "LLM_PROVIDER_COOLDOWN_SECONDS", 60.0)
    calls = {"bedrock": 0}

    async def boom(*args, **kwargs):
        calls["bedrock"] += 1
        raise RuntimeError("ValidationException")

    async def gemini_ok(*args, **kwargs):
        return '{"ok": true}'

    monkeypatch.setattr(LLMTriageEngine, "_call_bedrock", boom)
    monkeypatch.setattr(LLMTriageEngine, "_call_gemini", gemini_ok)
    for _ in range(3):
        _, provider = await LLMTriageEngine.query_llm_with_provenance("PROMPT")
        assert provider.startswith("gemini:")
    assert calls["bedrock"] == 1  # tried once, then skipped

    LLMTriageEngine._cooldown_until.clear()  # window over: it gets another chance
    await LLMTriageEngine.query_llm_with_provenance("PROMPT")
    assert calls["bedrock"] == 2


@pytest.mark.asyncio
async def test_only_provider_is_never_skipped(monkeypatch):
    """With nothing else to fall back on, a cooled-down provider is still attempted."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "LLM_TRIAGE_ENABLED", True)
    monkeypatch.setattr(app_settings, "LLM_PROVIDER", "bedrock")
    monkeypatch.setattr(app_settings, "BEDROCK_AWS_PROFILE", "hackathon")
    monkeypatch.setattr(app_settings, "LLM_PROVIDER_COOLDOWN_SECONDS", 60.0)
    calls = {"n": 0}

    async def boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("x")

    monkeypatch.setattr(LLMTriageEngine, "_call_bedrock", boom)
    await LLMTriageEngine.query_llm_with_provenance("PROMPT")
    await LLMTriageEngine.query_llm_with_provenance("PROMPT")
    assert calls["n"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"candidates": [{"finishReason": "SAFETY"}]},                    # blocked: no content at all
    {"candidates": [{"content": {"role": "model"}, "finishReason": "MAX_TOKENS"}]},  # no parts
    {"candidates": []},
    {"promptFeedback": {"blockReason": "OTHER"}},
])
async def test_gemini_reply_without_text_is_a_miss_not_a_crash(monkeypatch, body):
    """A 200 from Gemini with no text must yield None so the chain can fall through."""
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "x")

    class FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): ...
        async def post(self, *a, **k):
            return httpx.Response(200, json=body, request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(llm_engine.httpx, "AsyncClient", FakeClient)
    assert await LLMTriageEngine._call_gemini("m", "SYS", "PROMPT", 0.2) is None


def test_coerce_json_tolerates_fences_and_prose():
    """Model output wrapped in ```json fences or prose is still parsed."""
    assert LLMTriageEngine._coerce_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert LLMTriageEngine._coerce_json('Here you go: {"a": 2} done') == {"a": 2}
    assert LLMTriageEngine._coerce_json("not json at all") is None


# ── Real-code grounding (#2) ────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_triage_grounds_in_real_source(client: httpx.AsyncClient, seed_sample_issues, monkeypatch):
    """The fetched repository source is injected into the prompt and recorded as grounded."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(app_settings, "LLM_GROUND_IN_SOURCE", True)

    fake_source = "def format_messages(self, **kwargs):\n    return self.tpl.format(**kwargs)  # MARKER no None guard"

    async def fake_fetch(self, owner, repo, path, ref=None):
        return fake_source

    monkeypatch.setattr(GitHubClient, "fetch_file_content", fake_fetch)

    captured = {}
    canned = {"root_cause_summary": "None reaches .format() unguarded.", "confidence_score": 0.8}

    async def fake_provenance(prompt, system_prompt=None, temperature=0.2):
        captured["prompt"] = prompt
        return json.dumps(canned), "gemini:gemini-3.5-flash-lite"

    monkeypatch.setattr(LLMTriageEngine, "query_llm_with_provenance", staticmethod(fake_provenance))

    response = await client.get("/api/v1/triage/langchain-ai/langchain%232002")
    assert response.status_code == 200
    data = response.json()

    assert data["llm_enhanced"] is True
    # Real source made it into the prompt sent to the model.
    assert "MARKER no None guard" in captured["prompt"]
    # And the grounded file is surfaced in the response.
    assert len(data["llm_analysis"]["grounded_files"]) >= 1


@pytest.mark.asyncio
async def test_triage_grounding_degrades_when_source_unavailable(
    client: httpx.AsyncClient, seed_sample_issues, monkeypatch
):
    """When no source can be fetched, the report is still enhanced but grounded_files is empty."""
    _force_ast_only(monkeypatch)
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(app_settings, "LLM_GROUND_IN_SOURCE", True)
    _stub_no_source(monkeypatch)  # every fetch returns None

    canned = {"root_cause_summary": "Diagnosis from issue text alone.", "confidence_score": 0.5}

    async def fake_provenance(prompt, system_prompt=None, temperature=0.2):
        return json.dumps(canned), "gemini:gemini-3.5-flash-lite"

    monkeypatch.setattr(LLMTriageEngine, "query_llm_with_provenance", staticmethod(fake_provenance))

    response = await client.get("/api/v1/triage/kubernetes/kubernetes%234004")
    assert response.status_code == 200
    data = response.json()

    assert data["llm_enhanced"] is True
    assert data["llm_analysis"]["grounded_files"] == []
