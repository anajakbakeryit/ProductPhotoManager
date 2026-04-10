"""API tests for health + auth."""
import pytest


@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "dev_mode" in data


@pytest.mark.asyncio
async def test_auth_me(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"
