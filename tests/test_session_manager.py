"""
test_session_manager.py — Unit tests for core/session_manager.py
"""
import json
import os
import pytest

from core.session_manager import SessionManager


@pytest.fixture
def mgr(tmp_path):
    return SessionManager(str(tmp_path / "session.json"))


SAMPLE_PHOTOS = [
    {"barcode": "SKU001", "angle": "front", "filename": "SKU001_front_01.jpg",
     "path": "/output/original/SKU001/OG/SKU001_front_01_OG.jpg", "time": "10:00:00"},
]


class TestSessionManager:
    def test_load_returns_none_when_no_file(self, mgr):
        assert mgr.load() is None

    def test_save_and_load(self, mgr):
        mgr.save("SKU001", "front", {"front": 1}, 0, SAMPLE_PHOTOS)
        state = mgr.load()
        assert state is not None
        assert state["current_barcode"] == "SKU001"
        assert len(state["session_photos"]) == 1

    def test_load_returns_none_when_no_photos(self, mgr):
        mgr.save("", "", {}, 0, [])
        assert mgr.load() is None

    def test_caps_photos_at_500(self, mgr):
        photos = [
            {"barcode": f"SKU{i}", "angle": "front",
             "filename": f"SKU{i}_front_01.jpg", "path": "", "time": ""}
            for i in range(600)
        ]
        mgr.save("SKU599", "front", {}, 0, photos)
        state = mgr.load()
        assert len(state["session_photos"]) == 500

    def test_corrupt_json_returns_none(self, tmp_path):
        path = tmp_path / "session.json"
        path.write_text("NOT JSON }{", encoding="utf-8")
        mgr = SessionManager(str(path))
        result = mgr.load()
        assert result is None
        assert not path.exists()  # corrupt file deleted

    def test_delete_removes_file(self, mgr):
        mgr.save("SKU001", "front", {}, 0, SAMPLE_PHOTOS)
        assert os.path.exists(mgr.path)
        mgr.delete()
        assert not os.path.exists(mgr.path)

    def test_delete_nonexistent_file_no_error(self, mgr):
        mgr.delete()  # should not raise
