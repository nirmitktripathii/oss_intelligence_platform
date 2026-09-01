"""Unit tests for the Issues API endpoints."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_issues_pagination(client: httpx.AsyncClient, seed_sample_issues):
    """Verify listing issues with default pagination."""
    response = await client.get("/api/v1/issues?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2


@pytest.mark.asyncio
async def test_filter_issues_by_domain(client: httpx.AsyncClient, seed_sample_issues):
    """Filter issues by specific engineering domain."""
    response = await client.get("/api/v1/issues?domain=AI/ML")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["domain"] == "AI/ML"
    assert data["items"][0]["id"] == "langchain-ai/langchain#2002"


@pytest.mark.asyncio
async def test_filter_issues_by_difficulty(client: httpx.AsyncClient, seed_sample_issues):
    """Filter issues by difficulty tier."""
    response = await client.get("/api/v1/issues?difficulty=Hard")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["difficulty"] == "Hard"
    assert data["items"][0]["id"] == "pola-rs/polars#3003"


@pytest.mark.asyncio
async def test_filter_issues_has_bounty(client: httpx.AsyncClient, seed_sample_issues):
    """Filter issues that have monetary bounties attached."""
    response = await client.get("/api/v1/issues?has_bounty=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["has_bounty"] is True
        assert item["bounty_amount_usd"] > 0


@pytest.mark.asyncio
async def test_filter_issues_min_bounty(client: httpx.AsyncClient, seed_sample_issues):
    """Filter issues by minimum bounty threshold."""
    response = await client.get("/api/v1/issues?min_bounty=300")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["bounty_amount_usd"] == 500.0


@pytest.mark.asyncio
async def test_search_issues_keyword(client: httpx.AsyncClient, seed_sample_issues):
    """Search issues using free-text keywords."""
    response = await client.get("/api/v1/issues?search=BackgroundTasks")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "fastapi/fastapi#1001"


@pytest.mark.asyncio
async def test_sort_issues_by_hourly_roi(client: httpx.AsyncClient, seed_sample_issues):
    """Sort issues by $/hr expected ROI."""
    response = await client.get("/api/v1/issues?sort_by=hourly_roi")
    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    assert len(items) >= 2
    # First item should be the highest ROI ($100/hr for fastapi)
    assert items[0]["id"] == "fastapi/fastapi#1001"
    assert items[0]["hourly_roi"] == 100.0


@pytest.mark.asyncio
async def test_sort_issues_by_time_asc(client: httpx.AsyncClient, seed_sample_issues):
    """Sort issues by fastest-to-solve (ascending estimated effort)."""
    response = await client.get("/api/v1/issues?sort_by=time_asc")
    assert response.status_code == 200
    items = response.json()["items"]
    # langchain (0.75h) < fastapi (2.5h) < k8s (3.0h) < polars (8.0h)
    assert items[0]["id"] == "langchain-ai/langchain#2002"
    assert items[-1]["id"] == "pola-rs/polars#3003"
    hours = [i["estimated_hours"] for i in items]
    assert hours == sorted(hours)


@pytest.mark.asyncio
async def test_filter_issues_max_hours(client: httpx.AsyncClient, seed_sample_issues):
    """Filter to short tasks via the estimated-effort ceiling."""
    response = await client.get("/api/v1/issues?max_hours=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "langchain-ai/langchain#2002"


@pytest.mark.asyncio
async def test_filter_issues_hours_window(client: httpx.AsyncClient, seed_sample_issues):
    """Filter to a 2h-6h effort window (min + max hours together)."""
    response = await client.get("/api/v1/issues?min_hours=2&max_hours=6")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    ids = {i["id"] for i in data["items"]}
    assert ids == {"fastapi/fastapi#1001", "kubernetes/kubernetes#4004"}


@pytest.mark.asyncio
async def test_filter_issues_tech_stack_multi(client: httpx.AsyncClient, seed_sample_issues):
    """A comma-separated tech_stack matches ANY tag, and totals stay accurate."""
    response = await client.get("/api/v1/issues?tech_stack=Python,Rust")
    assert response.status_code == 200
    data = response.json()
    # Python -> fastapi + langchain; Rust -> polars. k8s (Go) excluded.
    assert data["total"] == 3
    ids = {i["id"] for i in data["items"]}
    assert ids == {
        "fastapi/fastapi#1001",
        "langchain-ai/langchain#2002",
        "pola-rs/polars#3003",
    }


@pytest.mark.asyncio
async def test_filter_issues_tech_stack_single(client: httpx.AsyncClient, seed_sample_issues):
    """A single tech_stack tag still filters correctly."""
    response = await client.get("/api/v1/issues?tech_stack=Kubernetes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "kubernetes/kubernetes#4004"


@pytest.mark.asyncio
async def test_get_single_issue_success(client: httpx.AsyncClient, seed_sample_issues):
    """Retrieve an existing issue by composite ID."""
    response = await client.get("/api/v1/issues/fastapi/fastapi%231001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "fastapi/fastapi#1001"
    assert data["repo_owner"] == "fastapi"
    assert data["repo_name"] == "fastapi"
    assert data["issue_number"] == 1001
    assert data["has_bounty"] is True
    assert data["bounty_source"] == "Polar"


@pytest.mark.asyncio
async def test_get_single_issue_not_found(client: httpx.AsyncClient, seed_sample_issues):
    """Verify 404 when requesting a non-existent issue ID."""
    response = await client.get("/api/v1/issues/nonexistent/repo%2399999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
