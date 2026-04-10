"""API tests for sessions router."""
import pytest


@pytest.mark.asyncio
async def test_start_session(client):
    res = await client.post("/api/sessions/start")
    assert res.status_code == 201
    assert "id" in res.json()


@pytest.mark.asyncio
async def test_list_sessions(client):
    await client.post("/api/sessions/start")
    res = await client.get("/api/sessions")
    assert res.status_code == 200
    assert res.json()["total"] >= 1


@pytest.mark.asyncio
async def test_end_session(client):
    start = await client.post("/api/sessions/start")
    sid = start.json()["id"]
    res = await client.post(f"/api/sessions/{sid}/end")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_get_active_session(client):
    await client.post("/api/sessions/start")
    res = await client.get("/api/sessions/active")
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert data["id"] is not None
