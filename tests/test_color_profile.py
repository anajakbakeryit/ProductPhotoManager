"""
test_color_profile.py — Unit tests for utils/color_profile.py
"""
import io
import os
import pytest
from PIL import Image, ImageCms

from utils.color_profile import to_srgb, save_multi_resolution, _SRGB_ICC


def make_rgb_image(w=100, h=100, color=(200, 100, 50)) -> Image.Image:
    img = Image.new("RGB", (w, h), color)
    img.info["icc_profile"] = _SRGB_ICC
    return img


def make_rgba_image(w=100, h=100) -> Image.Image:
    img = Image.new("RGBA", (w, h), (200, 100, 50, 180))
    img.info["icc_profile"] = _SRGB_ICC
    return img


class TestToSrgb:
    def test_rgb_passthrough(self):
        img = make_rgb_image()
        result = to_srgb(img)
        assert result.mode == "RGB"
        assert result.info.get("icc_profile") == _SRGB_ICC

    def test_rgba_preserved(self):
        img = make_rgba_image()
        result = to_srgb(img)
        assert result.mode == "RGBA"
        assert result.info.get("icc_profile") == _SRGB_ICC

    def test_palette_converted_to_rgb(self):
        img = Image.new("P", (50, 50))
        result = to_srgb(img)
        assert result.mode in ("RGB", "RGBA")

    def test_grayscale_converted(self):
        img = Image.new("L", (50, 50), 128)
        result = to_srgb(img)
        assert result.mode == "RGB"

    def test_image_with_no_icc_profile(self):
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        # No icc_profile key in info
        result = to_srgb(img)
        assert result.mode == "RGB"
        assert result.info.get("icc_profile") == _SRGB_ICC


class TestSaveMultiResolution:
    def test_creates_smlog_dirs(self, tmp_path):
        img = make_rgb_image(2000, 2000)
        save_multi_resolution(img, str(tmp_path), "test_base")
        for sz in ["S", "M", "L", "OG"]:
            assert (tmp_path / sz).is_dir(), f"Missing dir: {sz}"
            files = list((tmp_path / sz).iterdir())
            assert len(files) == 1

    def test_og_is_original_size(self, tmp_path):
        img = make_rgb_image(500, 400)
        save_multi_resolution(img, str(tmp_path), "base")
        og = Image.open(tmp_path / "OG" / "base_OG.jpg")
        assert og.size == (500, 400)

    def test_s_resized(self, tmp_path):
        img = make_rgb_image(2000, 1500)
        save_multi_resolution(img, str(tmp_path), "base")
        s = Image.open(tmp_path / "S" / "base_S.jpg")
        assert max(s.size) <= 480

    def test_small_image_not_upscaled(self, tmp_path):
        img = make_rgb_image(200, 200)  # smaller than S (480)
        save_multi_resolution(img, str(tmp_path), "base")
        s = Image.open(tmp_path / "S" / "base_S.jpg")
        assert s.size == (200, 200)  # no upscale

    def test_png_cutout_saved(self, tmp_path):
        img = make_rgba_image(300, 300)
        save_multi_resolution(img, str(tmp_path), "cutout_base", ext=".png", is_png=True)
        og = tmp_path / "OG" / "cutout_base_OG.png"
        assert og.exists()
        assert Image.open(og).mode == "RGBA"

    def test_icc_profile_embedded(self, tmp_path):
        img = make_rgb_image(600, 600)
        save_multi_resolution(img, str(tmp_path), "icc_test")
        og = Image.open(tmp_path / "OG" / "icc_test_OG.jpg")
        assert og.info.get("icc_profile") is not None
