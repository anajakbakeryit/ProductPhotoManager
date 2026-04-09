"""
core/config.py — โหลด / บันทึก / ตรวจสอบ / ค่าเริ่มต้น config
"""
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
CONFIG_VERSION = 1

DEFAULT_ANGLES = [
    {"id": "front",   "label": "Front",   "label_th": "ด้านหน้า",    "key": "F1"},
    {"id": "back",    "label": "Back",    "label_th": "ด้านหลัง",    "key": "F2"},
    {"id": "left",    "label": "Left",    "label_th": "ด้านซ้าย",   "key": "F3"},
    {"id": "right",   "label": "Right",   "label_th": "ด้านขวา",    "key": "F4"},
    {"id": "top",     "label": "Top",     "label_th": "ด้านบน",     "key": "F5"},
    {"id": "bottom",  "label": "Bottom",  "label_th": "ด้านล่าง",   "key": "F6"},
    {"id": "detail",  "label": "Detail",  "label_th": "รายละเอียด", "key": "F7"},
    {"id": "package", "label": "Package", "label_th": "แพ็คเกจ",    "key": "F8"},
]

DEFAULT_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "watch_folder": "",
    "output_folder": "",
    "watermark_path": "",
    "watermark_opacity": 40,
    "watermark_scale": 20,
    "watermark_position": "bottom-right",
    "watermark_margin": 30,
    "bg_color": [255, 255, 255],
    "image_extensions": [".jpg", ".jpeg", ".cr2", ".cr3", ".arw", ".nef", ".tif", ".tiff", ".png"],
    "angles": DEFAULT_ANGLES,
    "auto_increment": True,
    "copy_mode": False,
    "enable_cutout": True,
    "enable_watermark": True,
    "enable_wm_original": True,
    "spin360_total": 24,
    "video360_remove_bg": False,
    "export_folder": "",
    "import_folder": "",
}


def validate_config(cfg: dict) -> list[str]:
    """ตรวจสอบค่า config คืนรายการ error (ถ้ามี)."""
    errors: list[str] = []

    opacity = cfg.get("watermark_opacity", 40)
    if not isinstance(opacity, (int, float)) or not (10 <= opacity <= 100):
        errors.append(f"watermark_opacity ต้องอยู่ระหว่าง 10-100 (ได้ {opacity!r})")

    scale = cfg.get("watermark_scale", 20)
    if not isinstance(scale, (int, float)) or not (5 <= scale <= 50):
        errors.append(f"watermark_scale ต้องอยู่ระหว่าง 5-50 (ได้ {scale!r})")

    bg = cfg.get("bg_color", [255, 255, 255])
    if not (isinstance(bg, list) and len(bg) == 3
            and all(isinstance(v, int) and 0 <= v <= 255 for v in bg)):
        errors.append(f"bg_color ต้องเป็น [R,G,B] แต่ละค่า 0-255 (ได้ {bg!r})")

    exts = cfg.get("image_extensions", [])
    if not isinstance(exts, list) or not exts:
        errors.append("image_extensions ต้องเป็น list ที่ไม่ว่าง")

    spin = cfg.get("spin360_total", 24)
    if not isinstance(spin, int) or not (4 <= spin <= 360):
        errors.append(f"spin360_total ต้องอยู่ระหว่าง 4-360 (ได้ {spin!r})")

    margin = cfg.get("watermark_margin", 30)
    if not isinstance(margin, int) or not (0 <= margin <= 500):
        errors.append(f"watermark_margin ต้องอยู่ระหว่าง 0-500 (ได้ {margin!r})")

    return errors


def load_config(path: str = CONFIG_FILE) -> dict:
    """โหลด config จากไฟล์ JSON merge กับค่า default."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)

            # Log unknown keys (deprecated fields)
            known = set(DEFAULT_CONFIG.keys())
            unknown = set(saved.keys()) - known
            if unknown:
                logger.warning(f"[config] พบ key ที่ไม่รู้จัก: {unknown}")

            cfg = {**DEFAULT_CONFIG, **saved}

            # Validate and log errors but don't crash
            errors = validate_config(cfg)
            for err in errors:
                logger.warning(f"[config] ค่าไม่ถูกต้อง: {err}")

            return cfg
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"[config] โหลดไม่สำเร็จ: {e} — ใช้ค่า default แทน")

    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict, path: str = CONFIG_FILE) -> None:
    """บันทึก config ลงไฟล์ JSON."""
    cfg["config_version"] = CONFIG_VERSION
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"[config] บันทึกไม่สำเร็จ: {e}")
        raise
