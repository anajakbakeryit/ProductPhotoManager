"""
core/image_processor.py — Background thread สำหรับประมวลผลภาพ
Pipeline: ลบพื้นหลัง (rembg) → ใส่ลายน้ำ (Pillow)
"""
import logging
import os
import threading
from queue import Queue, Empty
from typing import Any, Callable

from PIL import Image, ImageEnhance

from utils.color_profile import to_srgb, save_multi_resolution, _SRGB_ICC

logger = logging.getLogger(__name__)

# Optional deps
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


class ImageProcessor(threading.Thread):
    """Background thread ที่ประมวลผลภาพ: ลบพื้นหลัง → ใส่ลายน้ำ."""

    def __init__(self, log_fn: Callable, done_fn: Callable) -> None:
        """
        Args:
            log_fn: callable(message, tag) สำหรับ log ข้อความ
            done_fn: callable() เรียกหลังแต่ละงานเสร็จ
        """
        super().__init__(daemon=True, name="ImageProcessor")
        self._log = log_fn
        self._done = done_fn
        self.queue: Queue = Queue()
        self._running = True

    def enqueue(self, task: dict) -> None:
        """เพิ่มงานเข้าคิว task dict: original_path, barcode, filename, output_root, config."""
        self.queue.put(task)

    @property
    def pending_count(self) -> int:
        return self.queue.qsize()

    def run(self) -> None:
        while self._running:
            try:
                task = self.queue.get(timeout=1)
            except Empty:
                continue
            except Exception as e:
                logger.warning(f"[ImageProcessor] queue error: {e}")
                continue
            try:
                self._process(task)
            except Exception as e:
                logger.error(f"[ImageProcessor] ประมวลผลผิดพลาด: {e}", exc_info=True)
                self._log(f"   ประมวลผลผิดพลาด: {e}", "error")
            finally:
                self._done()

    def stop(self) -> None:
        self._running = False

    def _process(self, task: dict) -> None:
        original_path: str = task["original_path"]
        barcode: str = task["barcode"]
        base_name: str = os.path.splitext(task["filename"])[0]
        output_root: str = task["output_root"]
        config: dict = task["config"]

        watermark_path = config.get("watermark_path", "")
        has_wm_file = bool(watermark_path and os.path.exists(watermark_path))

        # ── Step 1: Watermark on Original (no BG removal) ──
        if config.get("enable_wm_original", True):
            if has_wm_file:
                self._log(f"   กำลังใส่ลายน้ำ (ต้นฉบับ): {task['filename']}...", "dim")
                orig_img = to_srgb(Image.open(original_path)).convert("RGBA")
                wm_img = self._add_watermark(orig_img, watermark_path, config)

                bg_color = tuple(config.get("bg_color", [255, 255, 255]))
                final = Image.new("RGB", wm_img.size, bg_color)
                final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
                final.info["icc_profile"] = _SRGB_ICC

                wm_orig_dir = os.path.join(output_root, "watermarked_original", barcode)
                os.makedirs(wm_orig_dir, exist_ok=True)
                save_multi_resolution(final, wm_orig_dir, base_name)
                self._log(f"   ✓ ลายน้ำต้นฉบับ: watermarked_original/{barcode}/ (S/M/L/OG)", "success")
            else:
                self._log("   ยังไม่ได้ตั้งค่าไฟล์ลายน้ำ ข้ามลายน้ำต้นฉบับ", "warning")

        # ── Step 2: Remove background ──
        if config.get("enable_cutout", True):
            self._log(f"   กำลังลบพื้นหลัง: {task['filename']}...", "dim")
            img = to_srgb(Image.open(original_path)).convert("RGBA")

            if HAS_REMBG:
                cutout_img = rembg_remove(img)
            else:
                cutout_img = img
                self._log("   ยังไม่ได้ติดตั้ง rembg ข้ามการลบพื้นหลัง", "warning")

            cutout_dir = os.path.join(output_root, "cutout", barcode)
            os.makedirs(cutout_dir, exist_ok=True)
            save_multi_resolution(cutout_img, cutout_dir, base_name, ext=".png", is_png=True)
            self._log(f"   ✓ ลบพื้นหลัง: cutout/{barcode}/ (S/M/L/OG)", "success")

            # ── Step 3: Watermark on cutout ──
            if config.get("enable_watermark", True):
                if has_wm_file:
                    wm_img = self._add_watermark(cutout_img, watermark_path, config)
                    bg_color = tuple(config.get("bg_color", [255, 255, 255]))
                    final = Image.new("RGB", wm_img.size, bg_color)
                    final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
                    final.info["icc_profile"] = _SRGB_ICC

                    wm_dir = os.path.join(output_root, "watermarked", barcode)
                    os.makedirs(wm_dir, exist_ok=True)
                    save_multi_resolution(final, wm_dir, base_name)
                    self._log(f"   ✓ ลายน้ำ: watermarked/{barcode}/ (S/M/L/OG)", "success")
                else:
                    self._log("   ยังไม่ได้ตั้งค่าไฟล์ลายน้ำ ข้าม", "warning")

    def _add_watermark(self, base_img: Image.Image, watermark_path: str, config: dict) -> Image.Image:
        """Overlay watermark PNG บน base image."""
        wm = Image.open(watermark_path).convert("RGBA")

        scale_pct = config.get("watermark_scale", 20) / 100.0
        base_w, base_h = base_img.size
        wm_target_w = int(base_w * scale_pct)
        wm_ratio = wm_target_w / wm.width
        wm_target_h = int(wm.height * wm_ratio)
        wm = wm.resize((wm_target_w, wm_target_h), Image.LANCZOS)

        opacity = config.get("watermark_opacity", 40) / 100.0
        alpha = wm.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm.putalpha(alpha)

        margin = config.get("watermark_margin", 30)
        position = config.get("watermark_position", "bottom-right")

        if position == "center":
            x = (base_w - wm_target_w) // 2
            y = (base_h - wm_target_h) // 2
        elif position == "bottom-left":
            x = margin
            y = base_h - wm_target_h - margin
        elif position == "top-right":
            x = base_w - wm_target_w - margin
            y = margin
        elif position == "top-left":
            x = margin
            y = margin
        else:  # bottom-right (default)
            x = base_w - wm_target_w - margin
            y = base_h - wm_target_h - margin

        result = base_img.copy()
        result.paste(wm, (x, y), wm)
        return result
