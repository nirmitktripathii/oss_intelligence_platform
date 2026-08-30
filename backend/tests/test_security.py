"""Unit tests for OWASP Security Headers, CORS, and Rate Limiting."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_owasp_security_headers_present(client: httpx.AsyncClient):
    """Verify all critical OWASP security headers are returned on API endpoints."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    headers = response.headers
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]

    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Strict-Transport-Security" in headers
    assert "Permissions-Policy" in headers
    assert headers.get("X-XSS-Protection") == "1; mode=block"


@pytest.mark.asyncio
async def test_cors_headers_on_preflight(client: httpx.AsyncClient):
    """Verify CORS preflight headers for allowed origins."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = await client.options("/api/v1/issues", headers=headers)
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
