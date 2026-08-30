"""Unit tests for the health check and root endpoints."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_root_endpoint(client: httpx.AsyncClient):
    """Verify root index returns operational status."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert data["api_v1"] == "/api/v1"


@pytest.mark.asyncio
async def test_health_check_empty_db(client: httpx.AsyncClient):
    """Verify health check endpoint when DB is fresh."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db_connected"] is True
    assert data["issues_count"] == 0
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check_with_seeded_data(client: httpx.AsyncClient, seed_sample_issues):
    """Verify health check returns accurate issue count."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["db_connected"] is True
    assert data["issues_count"] == 4
