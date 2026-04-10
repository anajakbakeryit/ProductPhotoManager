"""API tests for settings router."""
import pytest


@pytest.mark.asyncio
async def test_get_default_settings(client):
    res = await client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "config" in data
    assert data["config"].get("watermark_opacity") is not None


@pytest.mark.asyncio
async def test_update_settings(client):
    res = await client.put("/api/settings", json={
        "config": {"watermark_opacity": 80, "enable_cutout": False}
    })
    assert res.status_code == 200

    # Verify saved
    res2 = await client.get("/api/settings")
    assert res2.json()["config"]["watermark_opacity"] == 80


@pytest.mark.asyncio
async def test_invalid_settings_rejected(client):
    res = await client.put("/api/settings", json={
        "config": {"watermark_opacity": 999}  # out of range
    })
    assert res.status_code == 400
