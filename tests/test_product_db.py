"""
test_product_db.py — Unit tests for core/product_db.py
"""
import csv
import os
import pytest

from core.product_db import ProductDB


@pytest.fixture
def db(tmp_path):
    """Fresh ProductDB in a temp directory."""
    return ProductDB(str(tmp_path / "products.csv"))


class TestProductDB:
    def test_creates_file_if_missing(self, tmp_path):
        path = tmp_path / "products.csv"
        assert not path.exists()
        ProductDB(str(path))
        assert path.exists()

    def test_lookup_nonexistent_returns_none(self, db):
        assert db.lookup("UNKNOWN999") is None

    def test_add_and_lookup(self, db):
        db.add("SKU001", name="สินค้าทดสอบ", category="ทดสอบ")
        result = db.lookup("SKU001")
        assert result is not None
        assert result["name"] == "สินค้าทดสอบ"
        assert result["category"] == "ทดสอบ"

    def test_add_persists_to_csv(self, tmp_path):
        path = tmp_path / "products.csv"
        db = ProductDB(str(path))
        db.add("SKU002", name="สินค้า 2")
        # Reload fresh instance
        db2 = ProductDB(str(path))
        assert db2.lookup("SKU002")["name"] == "สินค้า 2"

    def test_update_existing(self, db):
        db.add("SKU003", name="เดิม")
        db.add("SKU003", name="ใหม่")
        assert db.lookup("SKU003")["name"] == "ใหม่"

    def test_empty_csv_loads_cleanly(self, tmp_path):
        path = tmp_path / "products.csv"
        path.write_text("barcode,name,category,note\n", encoding="utf-8-sig")
        db = ProductDB(str(path))
        assert len(db.products) == 0

    def test_malformed_csv_row_skipped(self, tmp_path):
        path = tmp_path / "products.csv"
        path.write_text(
            "barcode,name,category,note\n"
            ",empty_barcode,cat,note\n"  # empty barcode → skip
            "SKU004,valid,cat,note\n",
            encoding="utf-8-sig",
        )
        db = ProductDB(str(path))
        assert db.lookup("SKU004") is not None
        assert "" not in db.products  # empty barcode skipped

    def test_multiple_adds(self, db):
        for i in range(10):
            db.add(f"SKU{i:03d}", name=f"Product {i}")
        assert len(db.products) == 10
        assert db.lookup("SKU005")["name"] == "Product 5"
