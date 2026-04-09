"""
test_sanitize.py — Unit tests for utils/sanitize.py
"""
import pytest
from utils.sanitize import sanitize_barcode, is_path_within


class TestSanitizeBarcode:
    def test_normal_barcode(self):
        assert sanitize_barcode("SKU001") == "SKU001"

    def test_strips_whitespace(self):
        assert sanitize_barcode("  SKU001  ") == "SKU001"

    def test_removes_path_separators(self):
        result = sanitize_barcode("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_removes_illegal_windows_chars(self):
        result = sanitize_barcode('SKU:001<>|?*"')
        assert ":" not in result
        assert "<" not in result
        assert ">" not in result
        assert "|" not in result
        assert "?" not in result
        assert "*" not in result
        assert '"' not in result

    def test_empty_becomes_unknown(self):
        assert sanitize_barcode("") == "UNKNOWN"
        assert sanitize_barcode("   ") == "UNKNOWN"
        assert sanitize_barcode("...") == "UNKNOWN"

    def test_caps_at_128_chars(self):
        long_barcode = "A" * 200
        result = sanitize_barcode(long_barcode)
        assert len(result) <= 128

    def test_strips_leading_trailing_dots(self):
        result = sanitize_barcode("...SKU001...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_control_chars_removed(self):
        result = sanitize_barcode("SKU\x00001\x1f")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_thai_barcode(self):
        result = sanitize_barcode("สินค้า001")
        assert result == "สินค้า001"

    def test_traversal_sequence_blocked(self):
        result = sanitize_barcode("foo../bar")
        assert ".." not in result


class TestIsPathWithin:
    def test_child_inside_parent(self, tmp_path):
        child = tmp_path / "sub" / "file.txt"
        assert is_path_within(str(child), str(tmp_path))

    def test_child_equals_parent_returns_false(self, tmp_path):
        # child must be strictly INSIDE parent
        assert not is_path_within(str(tmp_path), str(tmp_path))

    def test_path_traversal_rejected(self, tmp_path):
        parent = tmp_path / "output"
        parent.mkdir()
        traversal = str(parent / ".." / ".." / "etc" / "passwd")
        assert not is_path_within(traversal, str(parent))

    def test_sibling_rejected(self, tmp_path):
        parent = tmp_path / "output"
        sibling = tmp_path / "other"
        parent.mkdir()
        sibling.mkdir()
        assert not is_path_within(str(sibling / "file.txt"), str(parent))
