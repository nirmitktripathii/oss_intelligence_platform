"""Unit tests for the Bounties & ROI API endpoints."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_bounties_default(client: httpx.AsyncClient, seed_sample_issues):
    """Retrieve all funded bounties with summary analytics."""
    response = await client.get("/api/v1/bounties")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["total_bounty_usd"] == 750.0  # 250 (fastapi) + 500 (polars)
    assert data["average_hourly_roi"] > 0
    # Items should be ordered by hourly ROI (100.0 $/hr for fastapi, then 62.5 $/hr for polars)
    assert data["items"][0]["issue_id"] == "fastapi/fastapi#1001"
    assert data["items"][0]["hourly_roi"] == 100.0


@pytest.mark.asyncio
async def test_filter_bounties_min_amount(client: httpx.AsyncClient, seed_sample_issues):
    """Filter bounties by minimum USD threshold."""
    response = await client.get("/api/v1/bounties?min_amount=300")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["issue_id"] == "pola-rs/polars#3003"
    assert data["items"][0]["bounty_amount_usd"] == 500.0


@pytest.mark.asyncio
async def test_filter_bounties_by_domain(client: httpx.AsyncClient, seed_sample_issues):
    """Filter bounties by engineering domain."""
    response = await client.get("/api/v1/bounties?domain=Web")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["domain"] == "Web"
    assert data["items"][0]["bounty_source"] == "Polar"
