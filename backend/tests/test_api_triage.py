"""Unit tests for the AI Triage & Diagnostics API endpoints."""

import pytest
import httpx


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
