"""
test_viewer_generator.py — Unit tests for gen_viewer.py
"""
import json
import os
import pytest

from gen_viewer import generate_viewer


@pytest.fixture
def viewer_dir(tmp_path):
    """Create a 360 dir with _size_map.json and dummy frames."""
    barcode = "SKU001"
    base = tmp_path / barcode
    for sz in ["S", "M", "L", "OG"]:
        d = base / sz
        d.mkdir(parents=True)
        for i in range(4):
            (d / f"{barcode}_360_{i:02d}_{sz}.jpg").write_bytes(b"\xff\xd8dummy")

    size_map = {
        sz: [f"{sz}/{barcode}_360_{i:02d}_{sz}.jpg" for i in range(4)]
        for sz in ["S", "M", "L", "OG"]
    }
    (base / "_size_map.json").write_text(json.dumps(size_map), encoding="utf-8")
    return base, barcode


class TestGenerateViewer:
    def test_creates_viewer_html(self, viewer_dir):
        base, barcode = viewer_dir
        path = generate_viewer(str(base), barcode)
        assert os.path.exists(path)
        assert path.endswith("viewer.html")

    def test_html_contains_barcode(self, viewer_dir):
        base, barcode = viewer_dir
        path = generate_viewer(str(base), barcode)
        html = open(path, encoding="utf-8").read()
        assert barcode in html

    def test_html_contains_size_map(self, viewer_dir):
        base, barcode = viewer_dir
        path = generate_viewer(str(base), barcode)
        html = open(path, encoding="utf-8").read()
        assert "SIZE_MAP" in html
        assert '"S"' in html
        assert '"M"' in html
        assert '"L"' in html

    def test_html_is_self_contained(self, viewer_dir):
        base, barcode = viewer_dir
        path = generate_viewer(str(base), barcode)
        html = open(path, encoding="utf-8").read()
        assert "<script>" in html
        assert "<style>" in html
        assert "</html>" in html

    def test_raises_when_no_size_map(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            generate_viewer(str(tmp_path), "MISSING")

    def test_frame_count_matches(self, viewer_dir):
        base, barcode = viewer_dir
        path = generate_viewer(str(base), barcode)
        html = open(path, encoding="utf-8").read()
        assert "Frame 1 / 4" in html
