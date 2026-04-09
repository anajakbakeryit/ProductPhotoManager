"""
core/product_db.py — CSV-based product database (barcode → name/category/note)
"""
import csv
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

PRODUCT_DB_FILE = "products.csv"
_FIELDNAMES = ["barcode", "name", "category", "note"]


class ProductDB:
    """Simple CSV-backed product database."""

    def __init__(self, csv_path: str = PRODUCT_DB_FILE) -> None:
        self.csv_path = csv_path
        self.products: dict[str, dict] = {}
        self._ensure_file()
        self.load()

    def _ensure_file(self) -> None:
        if not os.path.exists(self.csv_path):
            try:
                with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerow(_FIELDNAMES)
            except OSError as e:
                logger.error(f"[ProductDB] สร้างไฟล์ไม่สำเร็จ: {e}")

    def load(self) -> None:
        """โหลดข้อมูลจาก CSV เข้า dict."""
        self.products = {}
        try:
            with open(self.csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    barcode = row.get("barcode", "").strip()
                    if barcode:
                        self.products[barcode] = {
                            "name": row.get("name", ""),
                            "category": row.get("category", ""),
                            "note": row.get("note", ""),
                        }
        except OSError as e:
            logger.error(f"[ProductDB] โหลดไม่สำเร็จ: {e}")

    def lookup(self, barcode: str) -> Optional[dict]:
        """คืนข้อมูลสินค้า หรือ None ถ้าไม่พบ."""
        return self.products.get(barcode)

    def add(self, barcode: str, name: str = "", category: str = "", note: str = "") -> None:
        """เพิ่มหรืออัปเดตสินค้า."""
        is_new = barcode not in self.products
        self.products[barcode] = {"name": name, "category": category, "note": note}
        if is_new:
            self._append_one(barcode, name, category, note)
        else:
            self._save_all()

    def _append_one(self, barcode: str, name: str, category: str, note: str) -> None:
        """Append a single row to CSV (fast for new barcodes)."""
        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow([barcode, name, category, note])
        except OSError as e:
            logger.warning(f"[ProductDB] append ไม่สำเร็จ: {e} — บันทึกใหม่ทั้งหมดแทน")
            self._save_all()

    def _save_all(self) -> None:
        """เขียน CSV ใหม่ทั้งหมด."""
        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(_FIELDNAMES)
                for bc, info in self.products.items():
                    writer.writerow([bc, info["name"], info["category"], info["note"]])
        except OSError as e:
            logger.error(f"[ProductDB] บันทึกไม่สำเร็จ: {e}")
