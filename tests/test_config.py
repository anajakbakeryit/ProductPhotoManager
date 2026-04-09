"""
test_config.py — Unit tests for core/config.py
"""
import json
import os
import pytest

from core.config import load_config, save_config, validate_config, DEFAULT_CONFIG


class TestValidateConfig:
    def test_valid_default_config(self):
        errors = validate_config(DEFAULT_CONFIG.copy())
        assert errors == []

    def test_opacity_out_of_range_low(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["watermark_opacity"] = 5
        errors = validate_config(cfg)
        assert any("watermark_opacity" in e for e in errors)

    def test_opacity_out_of_range_high(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["watermark_opacity"] = 101
        errors = validate_config(cfg)
        assert any("watermark_opacity" in e for e in errors)

    def test_scale_out_of_range(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["watermark_scale"] = 100
        errors = validate_config(cfg)
        assert any("watermark_scale" in e for e in errors)

    def test_invalid_bg_color(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["bg_color"] = [256, 0, 0]
        errors = validate_config(cfg)
        assert any("bg_color" in e for e in errors)

    def test_empty_extensions(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["image_extensions"] = []
        errors = validate_config(cfg)
        assert any("image_extensions" in e for e in errors)

    def test_spin_too_low(self):
        cfg = DEFAULT_CONFIG.copy()
        cfg["spin360_total"] = 2
        errors = validate_config(cfg)
        assert any("spin360_total" in e for e in errors)


class TestLoadConfig:
    def test_returns_default_when_no_file(self, tmp_path):
        cfg = load_config(str(tmp_path / "nonexistent.json"))
        assert cfg["watch_folder"] == ""
        assert "angles" in cfg

    def test_merges_with_defaults(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text(json.dumps({"watch_folder": "/test"}), encoding="utf-8")
        result = load_config(str(cfg_path))
        assert result["watch_folder"] == "/test"
        assert "output_folder" in result  # merged from defaults

    def test_handles_corrupt_json(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text("NOT JSON {{{", encoding="utf-8")
        result = load_config(str(cfg_path))
        assert result == DEFAULT_CONFIG.copy()

    def test_unknown_keys_logged(self, tmp_path, caplog):
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text(json.dumps({"unknown_key": "value"}), encoding="utf-8")
        import logging
        with caplog.at_level(logging.WARNING, logger="core.config"):
            load_config(str(cfg_path))
        assert any("unknown_key" in r.message for r in caplog.records)


class TestSaveConfig:
    def test_saves_and_loads(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        cfg = DEFAULT_CONFIG.copy()
        cfg["watch_folder"] = "/saved/path"
        save_config(cfg, str(cfg_path))
        loaded = load_config(str(cfg_path))
        assert loaded["watch_folder"] == "/saved/path"

    def test_adds_version(self, tmp_path):
        cfg_path = tmp_path / "config.json"
        cfg = DEFAULT_CONFIG.copy()
        save_config(cfg, str(cfg_path))
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        assert "config_version" in raw
