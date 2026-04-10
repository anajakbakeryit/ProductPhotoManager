"""API tests for products router."""
import pytest


@pytest.mark.asyncio
async def test_create_product(client):
    res = await client.post("/api/products", json={"barcode": "SKU001", "name": "สินค้า 1"})
    assert res.status_code == 201
    data = res.json()
    assert data["barcode"] == "SKU001"
    assert data["name"] == "สินค้า 1"


@pytest.mark.asyncio
async def test_duplicate_barcode_returns_409(client):
    await client.post("/api/products", json={"barcode": "SKU002"})
    res = await client.post("/api/products", json={"barcode": "SKU002"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_get_product_by_barcode(client):
    await client.post("/api/products", json={"barcode": "SKU003", "name": "Test"})
    res = await client.get("/api/products/SKU003")
    assert res.status_code == 200
    assert res.json()["name"] == "Test"


@pytest.mark.asyncio
async def test_get_nonexistent_product(client):
    res = await client.get("/api/products/NONEXIST")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_products(client):
    await client.post("/api/products", json={"barcode": "A001"})
    await client.post("/api/products", json={"barcode": "A002"})
    res = await client.get("/api/products")
    assert res.status_code == 200
    assert res.json()["total"] >= 2


@pytest.mark.asyncio
async def test_search_products(client):
    await client.post("/api/products", json={"barcode": "SEARCH001", "name": "ค้นหาทดสอบ"})
    res = await client.get("/api/products?search=SEARCH")
    assert res.status_code == 200
    assert res.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_product(client):
    await client.post("/api/products", json={"barcode": "UPD001", "name": "เดิม"})
    res = await client.put("/api/products/UPD001", json={"name": "ใหม่"})
    assert res.status_code == 200
    assert res.json()["name"] == "ใหม่"
