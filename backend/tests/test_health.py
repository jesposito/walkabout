"""
Tests for health check endpoints.
"""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy(client):
    """Test that the /health endpoint returns a healthy status."""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_returns_json(client):
    """Test that the /health endpoint returns JSON content type."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
