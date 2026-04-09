"""
Product Photo Manager
=====================
ระบบจัดการถ่ายภาพสินค้า - ยิง Barcode + เลือกมุมถ่าย + Auto Rename
+ Auto Remove Background + Auto Watermark
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import time
import threading
import json
import csv
from datetime import datetime
from queue import Queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageCms, ImageTk
import io
import html as html_mod

# Try import rembg (optional - will show warning if not installed)
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

# Try import OpenCV (optional - needed for Video→360° feature)
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# =============================================================================
# CONFIG
# =============================================================================
CONFIG_FILE = "config.json"
PRODUCT_DB_FILE = "products.csv"
SESSION_FILE = "session_state.json"

# sRGB ICC profile bytes — embedded in every output JPEG for color accuracy
_SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


import re
import logging
from collections import deque

def _setup_logging() -> logging.Logger:
    """Phase 6: ตั้งค่า logging ให้บันทึกลงไฟล์ด้วย (rotation 5 MB, เก็บ 3 ไฟล์)."""
    from logging.handlers import RotatingFileHandler
    fmt = logging.Formatter(
        "%(asctime)s [%(threadName)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        root.addHandler(ch)

    # File handler (rotating)
    try:
        fh = RotatingFileHandler(
            "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as e:
        logging.warning(f"ไม่สามารถเปิดไฟล์ log: {e}")

    return logging.getLogger(__name__)


logger = _setup_logging()

_BARCODE_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _sanitize_barcode(raw):
    """Sanitize barcode string for safe use as filename / folder name.

    Removes path separators, traversal sequences, control chars,
    and characters illegal in Windows filenames.
    """
    s = raw.strip()
    s = _BARCODE_UNSAFE.sub("_", s)   # replace unsafe chars first
    s = s.replace("..", "")           # block traversal
    s = s.strip("._ ")               # no leading/trailing dots, underscores, spaces
    if not s:
        s = "UNKNOWN"
    return s[:128]                    # cap length


def _to_srgb(img):
    """Convert image to sRGB with proper color management.

    If image has an embedded ICC profile (e.g., AdobeRGB from Canon 5D),
    this properly maps pixel values to sRGB so colors and contrast match.
    Returns RGB image with sRGB ICC profile in .info['icc_profile'].
    """
    icc_data = img.info.get("icc_profile")

    if icc_data and icc_data != _SRGB_ICC:
        # Source has a non-sRGB profile → convert properly
        try:
            src_profile = io.BytesIO(icc_data)
            dst_profile = ImageCms.createProfile("sRGB")

            if img.mode == "RGBA":
                # Split alpha, convert RGB channels, reattach
                r, g, b, a = img.split()
                rgb = Image.merge("RGB", (r, g, b))
                rgb = ImageCms.profileToProfile(
                    rgb, src_profile, dst_profile,
                    renderingIntent=ImageCms.Intent.PERCEPTUAL,
                    outputMode="RGB"
                )
                r2, g2, b2 = rgb.split()
                img = Image.merge("RGBA", (r2, g2, b2, a))
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = ImageCms.profileToProfile(
                    img, src_profile, dst_profile,
                    renderingIntent=ImageCms.Intent.PERCEPTUAL,
                    outputMode="RGB"
                )
        except Exception as e:
            logger.warning(f"[_to_srgb] ICC แปลงสีล้มเหลว: {e} — ใช้โหมดสีดิบแทน")
            # Fallback: just convert mode
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
    else:
        # No profile or already sRGB — just ensure correct mode
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

    img.info["icc_profile"] = _SRGB_ICC
    return img


# Multi-resolution presets (long edge in px)
MULTI_RES = {
    "S": {"max_px": 480, "quality": 85},
    "M": {"max_px": 800, "quality": 90},
    "L": {"max_px": 1200, "quality": 93},
}


def save_multi_resolution(img, folder, base_name, ext=".jpg", is_png=False):
    """Save image in S/M/L/OG sub-folders.

    Args:
        img: PIL Image (RGB or RGBA), should already be _to_srgb() converted
        folder: e.g. output_root/original/barcode
        base_name: filename without extension, e.g. 'SKU001_front_01'
        ext: output extension (.jpg or .png)
        is_png: if True, save as PNG (for cutout with transparency)
    """
    icc = img.info.get("icc_profile", _SRGB_ICC)

    # OG - original size
    og_dir = os.path.join(folder, "OG")
    os.makedirs(og_dir, exist_ok=True)
    og_path = os.path.join(og_dir, f"{base_name}_OG{ext}")
    if is_png:
        img.save(og_path, "PNG", icc_profile=icc)
    else:
        img_rgb = img.convert("RGB") if img.mode != "RGB" else img
        img_rgb.save(og_path, "JPEG", quality=95, subsampling=0, icc_profile=icc)

    orig_w, orig_h = img.size

    # S / M / L
    for sz_key, cfg in MULTI_RES.items():
        sz_dir = os.path.join(folder, sz_key)
        os.makedirs(sz_dir, exist_ok=True)
        max_px = cfg["max_px"]

        if orig_w <= max_px and orig_h <= max_px:
            resized = img
        else:
            ratio = min(max_px / orig_w, max_px / orig_h)
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            resized = img.resize((new_w, new_h), Image.LANCZOS)

        sz_path = os.path.join(sz_dir, f"{base_name}_{sz_key}{ext}")
        if is_png:
            resized.save(sz_path, "PNG", icc_profile=icc)
        else:
            resized_rgb = resized.convert("RGB") if resized.mode != "RGB" else resized
            resized_rgb.save(sz_path, "JPEG", quality=cfg["quality"],
                             subsampling=0, icc_profile=icc)

DEFAULT_CONFIG = {
    "watch_folder": "",
    "output_folder": "",
    "watermark_path": "",
    "watermark_opacity": 40,
    "watermark_scale": 20,
    "watermark_position": "bottom-right",
    "watermark_margin": 30,
    "bg_color": [255, 255, 255],
    "image_extensions": [".jpg", ".jpeg", ".cr2", ".cr3", ".arw", ".nef", ".tif", ".tiff", ".png"],
    "angles": [
        {"id": "front", "label": "Front", "label_th": "ด้านหน้า", "key": "F1"},
        {"id": "back", "label": "Back", "label_th": "ด้านหลัง", "key": "F2"},
        {"id": "left", "label": "Left", "label_th": "ด้านซ้าย", "key": "F3"},
        {"id": "right", "label": "Right", "label_th": "ด้านขวา", "key": "F4"},
        {"id": "top", "label": "Top", "label_th": "ด้านบน", "key": "F5"},
        {"id": "bottom", "label": "Bottom", "label_th": "ด้านล่าง", "key": "F6"},
        {"id": "detail", "label": "Detail", "label_th": "รายละเอียด", "key": "F7"},
        {"id": "package", "label": "Package", "label_th": "แพ็คเกจ", "key": "F8"},
    ],
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

# =============================================================================
# COLORS
# =============================================================================
C = {
    "bg":           "#0f1117",
    "surface":      "#1a1d27",
    "surface2":     "#232734",
    "border":       "#2e3348",
    "text":         "#e2e4ed",
    "text_dim":     "#6b7394",
    "text_muted":   "#4a5170",
    "accent":       "#6c8cff",
    "accent_hover": "#8ba4ff",
    "green":        "#4ade80",
    "green_dim":    "#1a3a2a",
    "red":          "#f87171",
    "red_dim":      "#3a1a1a",
    "yellow":       "#fbbf24",
    "yellow_dim":   "#3a321a",
    "orange":       "#fb923c",
    "purple":       "#a78bfa",
    "barcode_bg":   "#141720",
    "btn_idle":     "#282d3e",
    "btn_active":   "#6c8cff",
    "btn_hover":    "#323850",
    "log_bg":       "#0c0e14",
    "tag_bg":       "#2a2f42",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# =============================================================================
# PRODUCT DATABASE (CSV)
# =============================================================================
class ProductDB:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.products = {}
        self._ensure_file()
        self.load()

    def _ensure_file(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["barcode", "name", "category", "note"])

    def load(self):
        self.products = {}
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

    def lookup(self, barcode):
        return self.products.get(barcode)

    def add(self, barcode, name="", category="", note=""):
        is_new = barcode not in self.products
        self.products[barcode] = {"name": name, "category": category, "note": note}
        if is_new:
            self._append_one(barcode, name, category, note)
        else:
            self._save_all()

    def _append_one(self, barcode, name, category, note):
        """Append a single row to CSV (fast for new barcodes)."""
        try:
            with open(self.csv_path, "a", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerow([barcode, name, category, note])
        except Exception as e:
            logger.warning(f"[ProductDB] append ไม่สำเร็จ: {e} — บันทึกใหม่ทั้งหมดแทน")
            self._save_all()

    def _save_all(self):
        with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["barcode", "name", "category", "note"])
            for barcode, info in self.products.items():
                writer.writerow([barcode, info["name"], info["category"], info["note"]])


# =============================================================================
# IMAGE PROCESSOR (Background Thread)
# =============================================================================
class ImageProcessor(threading.Thread):
    """Background thread that processes images: remove BG → add watermark."""

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.queue = Queue()
        self._running = True

    def enqueue(self, task):
        """Add a processing task: dict with original_path, barcode, filename, etc."""
        self.queue.put(task)
        self.app.after(0, self.app._update_pipeline_status)

    @property
    def pending_count(self):
        return self.queue.qsize()

    def run(self):
        while self._running:
            try:
                task = self.queue.get(timeout=1)
            except Exception:
                continue
            try:
                self._process(task)
            except Exception as e:
                self.app.after(0, self.app.log, f"   ประมวลผลผิดพลาด: {e}", "error")

    def stop(self):
        self._running = False

    def _process(self, task):
        original_path = task["original_path"]
        barcode = task["barcode"]
        base_name = os.path.splitext(task["filename"])[0]
        output_root = task["output_root"]
        config = task["config"]

        watermark_path = config.get("watermark_path", "")
        has_wm_file = watermark_path and os.path.exists(watermark_path)

        # ── Step 1: Watermark on Original (no BG removal) ──
        if config.get("enable_wm_original", True):
            if has_wm_file:
                self.app.after(0, self.app.log,
                               f"   กำลังใส่ลายน้ำ (ต้นฉบับ): {task['filename']}...", "dim")

                orig_img = _to_srgb(Image.open(original_path)).convert("RGBA")
                wm_img = self._add_watermark(orig_img, watermark_path, config)

                # Flatten to RGB
                bg_color = tuple(config.get("bg_color", [255, 255, 255]))
                final = Image.new("RGB", wm_img.size, bg_color)
                final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
                final.info["icc_profile"] = _SRGB_ICC

                wm_orig_dir = os.path.join(output_root, "watermarked_original", barcode)
                os.makedirs(wm_orig_dir, exist_ok=True)

                # Multi-resolution only (no root file)
                save_multi_resolution(final, wm_orig_dir, base_name)

                self.app.after(0, self.app.log,
                               f"   \u2713 ลายน้ำต้นฉบับ: watermarked_original/{barcode}/ (S/M/L/OG)",
                               "success")
            else:
                self.app.after(0, self.app.log,
                               "   ยังไม่ได้ตั้งค่าไฟล์ลายน้ำ ข้ามลายน้ำต้นฉบับ", "warning")

        # ── Step 2: Remove background ──
        if config.get("enable_cutout", True):
            self.app.after(0, self.app.log,
                           f"   กำลังลบพื้นหลัง: {task['filename']}...", "dim")

            img = _to_srgb(Image.open(original_path)).convert("RGBA")

            if HAS_REMBG:
                cutout_img = rembg_remove(img)
            else:
                cutout_img = img
                self.app.after(0, self.app.log,
                               "   ยังไม่ได้ติดตั้ง rembg ข้ามการลบพื้นหลัง", "warning")

            # Save cutout - multi-resolution only (no root file)
            cutout_dir = os.path.join(output_root, "cutout", barcode)
            os.makedirs(cutout_dir, exist_ok=True)

            save_multi_resolution(cutout_img, cutout_dir, base_name, ext=".png", is_png=True)

            self.app.after(0, self.app.log,
                           f"   \u2713 ลบพื้นหลัง: cutout/{barcode}/ (S/M/L/OG)", "success")

            # ── Step 3: Add watermark on the cutout ──
            if config.get("enable_watermark", True):
                if has_wm_file:
                    wm_img = self._add_watermark(cutout_img, watermark_path, config)

                    bg_color = tuple(config.get("bg_color", [255, 255, 255]))
                    final = Image.new("RGB", wm_img.size, bg_color)
                    final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
                    final.info["icc_profile"] = _SRGB_ICC

                    wm_dir = os.path.join(output_root, "watermarked", barcode)
                    os.makedirs(wm_dir, exist_ok=True)

                    # Multi-resolution only (no root file)
                    save_multi_resolution(final, wm_dir, base_name)

                    self.app.after(0, self.app.log,
                                   f"   \u2713 ลายน้ำ: watermarked/{barcode}/ (S/M/L/OG)",
                                   "success")
                else:
                    self.app.after(0, self.app.log,
                                   "   ยังไม่ได้ตั้งค่าไฟล์ลายน้ำ ข้าม", "warning")

        # Update pipeline status
        self.app.after(0, self.app._on_pipeline_done)

    def _add_watermark(self, base_img, watermark_path, config):
        """Overlay watermark PNG on base image."""
        wm = Image.open(watermark_path).convert("RGBA")

        # Scale watermark relative to base image
        scale_pct = config.get("watermark_scale", 20) / 100.0
        base_w, base_h = base_img.size
        wm_target_w = int(base_w * scale_pct)
        wm_ratio = wm_target_w / wm.width
        wm_target_h = int(wm.height * wm_ratio)
        wm = wm.resize((wm_target_w, wm_target_h), Image.LANCZOS)

        # Apply opacity
        opacity = config.get("watermark_opacity", 40) / 100.0
        alpha = wm.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm.putalpha(alpha)

        # Position
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

        # Composite
        result = base_img.copy()
        result.paste(wm, (x, y), wm)
        return result


# =============================================================================
# FILE WATCHER
# =============================================================================
class PhotoWatcher(FileSystemEventHandler):
    def __init__(self, app, extensions):
        self.app = app
        self.extensions = [e.lower() for e in extensions]
        self._processed = set()

    def on_created(self, event):
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in self.extensions:
            self._wait_and_process(event.src_path)

    def _wait_and_process(self, filepath):
        def _do():
            prev_size = -1
            for _ in range(60):
                try:
                    curr_size = os.path.getsize(filepath)
                    if curr_size == prev_size and curr_size > 0:
                        break
                    prev_size = curr_size
                except OSError:
                    pass
                time.sleep(0.5)
            if filepath not in self._processed:
                # Limit set size to prevent unbounded memory growth
                if len(self._processed) > 5000:
                    # Discard half the oldest entries (set has no order, just trim)
                    self._processed = set(list(self._processed)[2500:])
                self._processed.add(filepath)
                self.app.after(0, self.app.process_new_photo, filepath)

        threading.Thread(target=_do, daemon=True).start()


# =============================================================================
# MAIN APPLICATION
# =============================================================================
class ProductPhotoApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ระบบจัดการถ่ายภาพสินค้า")
        self.geometry("1050x850")
        self.configure(bg=C["bg"])
        self.minsize(950, 750)

        # State
        self.config = load_config()
        self.product_db = ProductDB(PRODUCT_DB_FILE)
        self.current_barcode = ""
        self.current_angle = ""
        self.current_product_info = None
        self.angle_counters = {}
        self.session_photos = []
        self.observer = None
        self.is_watching = False
        self.pipeline_pending = 0
        self.is_360_mode = False
        self.spin360_counter = 0

        # Multi-level undo stack (Phase 4)
        self._undo_stack: deque = deque(maxlen=20)

        # Phase 6: O(1) angle label lookup dict {angle_id: (label, label_th)}
        self._angle_label_map: dict[str, tuple[str, str]] = {
            a["id"]: (a["label"], a.get("label_th", a["label"]))
            for a in self.config["angles"]
        }

        # Thread safety locks
        self._config_lock = threading.Lock()
        self._session_lock = threading.Lock()
        self._counter_lock = threading.Lock()

        # Image processor thread
        self.processor = ImageProcessor(self)
        self.processor.start()

        self._build_ui()

        # Keyboard shortcuts
        for angle in self.config["angles"]:
            aid = angle["id"]
            self.bind(f"<{angle['key']}>", lambda e, a=aid: self.select_angle(a))

        self.bind("<Control-z>", lambda e: self.undo_last_photo())
        self.after(100, lambda: self.barcode_entry.focus_set())
        self.after(500, self._restore_session)
        self.after(1000, self._startup_checks)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================================================================
    # UI BUILD
    # =========================================================================
    def _build_ui(self):
        # Scrollable main container
        outer = tk.Frame(self, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = tk.Frame(canvas, bg=C["bg"], padx=16, pady=12)
        main_window = canvas.create_window((0, 0), window=main, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(main_window, width=canvas.winfo_width())
        main.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- HEADER ---
        header = tk.Frame(main, bg=C["bg"])
        header.pack(fill="x", pady=(0, 12))

        tk.Label(header, text="ระบบจัดการถ่ายภาพสินค้า",
                 font=("Segoe UI Semibold", 16), fg=C["text"], bg=C["bg"]
                 ).pack(side="left")

        self.session_badge = tk.Label(
            header, text="  เซสชัน: 0 รูป  ",
            font=("Segoe UI", 9), fg=C["text_dim"], bg=C["tag_bg"], padx=10, pady=3
        )
        self.session_badge.pack(side="right")

        tk.Button(
            header, text="ตั้งค่า", font=("Segoe UI Semibold", 9),
            fg=C["text_dim"], bg=C["surface2"], activebackground=C["btn_hover"],
            activeforeground=C["text"], relief="flat", cursor="hand2",
            padx=10, pady=2, command=self._open_settings
        ).pack(side="right", padx=(0, 4))

        self.import_btn = tk.Button(
            header, text="นำเข้า", font=("Segoe UI Semibold", 9),
            fg=C["green"], bg=C["surface2"], activebackground=C["btn_hover"],
            activeforeground=C["green"], relief="flat", cursor="hand2",
            padx=10, pady=2, command=self.import_photos
        )
        self.import_btn.pack(side="right", padx=(0, 4))

        self.export_btn = tk.Button(
            header, text="ส่งออก", font=("Segoe UI Semibold", 9),
            fg=C["accent"], bg=C["surface2"], activebackground=C["btn_hover"],
            activeforeground=C["accent"], relief="flat", cursor="hand2",
            padx=10, pady=2, command=self.export_report
        )
        self.export_btn.pack(side="right", padx=(0, 4))

        self.undo_btn = tk.Button(
            header, text="เลิกทำ", font=("Segoe UI Semibold", 9),
            fg=C["red"], bg=C["surface2"], activebackground=C["btn_hover"],
            activeforeground=C["red"], relief="flat", cursor="hand2",
            padx=10, pady=2, command=self.undo_last_photo
        )
        self.undo_btn.pack(side="right", padx=(0, 4))

        # --- TOP ROW: Folders + Pipeline + Status ---
        top_row = tk.Frame(main, bg=C["bg"])
        top_row.pack(fill="x", pady=(0, 8))

        # Left: Folders
        folders_panel = tk.Frame(top_row, bg=C["surface"], padx=16, pady=12,
                                 highlightbackground=C["border"], highlightthickness=1)
        folders_panel.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(folders_panel, text="โฟลเดอร์",
                 font=("Segoe UI Semibold", 9), fg=C["text_dim"], bg=C["surface"]
                 ).grid(row=0, column=0, sticky="w", columnspan=3, pady=(0, 8))

        tk.Label(folders_panel, text="ต้นทาง", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"]).grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.watch_folder_var = tk.StringVar(value=self.config["watch_folder"])
        tk.Entry(folders_panel, textvariable=self.watch_folder_var, font=("Segoe UI", 10),
                 bg=C["surface2"], fg=C["text"], relief="flat", insertbackground=C["text"],
                 highlightthickness=0).grid(row=1, column=1, sticky="ew", padx=(0, 6), ipady=3)
        self._make_browse_btn(folders_panel, self.browse_watch).grid(row=1, column=2)

        tk.Label(folders_panel, text="ปลายทาง", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"]).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.output_folder_var = tk.StringVar(value=self.config["output_folder"])
        tk.Entry(folders_panel, textvariable=self.output_folder_var, font=("Segoe UI", 10),
                 bg=C["surface2"], fg=C["text"], relief="flat", insertbackground=C["text"],
                 highlightthickness=0).grid(row=2, column=1, sticky="ew", padx=(0, 6), ipady=3, pady=(6, 0))
        self._make_browse_btn(folders_panel, self.browse_output).grid(row=2, column=2, pady=(6, 0))

        folders_panel.columnconfigure(1, weight=1)

        # Right: Status
        status_panel = tk.Frame(top_row, bg=C["surface"], padx=16, pady=12,
                                highlightbackground=C["border"], highlightthickness=1, width=200)
        status_panel.pack(side="right", fill="y", padx=(6, 0))
        status_panel.pack_propagate(False)

        tk.Label(status_panel, text="สถานะ", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(anchor="w")

        si = tk.Frame(status_panel, bg=C["surface"])
        si.pack(fill="x", pady=(10, 6))
        self.status_dot = tk.Label(si, text="\u25cf", font=("Segoe UI", 14),
                                   fg=C["red"], bg=C["surface"])
        self.status_dot.pack(side="left")
        self.status_text = tk.Label(si, text="  หยุดอยู่", font=("Segoe UI Semibold", 11),
                                    fg=C["red"], bg=C["surface"])
        self.status_text.pack(side="left")

        self.watch_btn = tk.Button(
            status_panel, text="เริ่ม", font=("Segoe UI Semibold", 11),
            fg=C["bg"], bg=C["green"], activebackground=C["accent_hover"],
            relief="flat", cursor="hand2", padx=20, pady=4, command=self.toggle_watching
        )
        self.watch_btn.pack(fill="x", pady=(8, 0))

        # --- POST-PROCESSING PIPELINE ---
        pipeline_section = tk.Frame(main, bg=C["surface"], padx=20, pady=14,
                                    highlightbackground=C["border"], highlightthickness=1)
        pipeline_section.pack(fill="x", pady=(0, 8))

        pp_header = tk.Frame(pipeline_section, bg=C["surface"])
        pp_header.pack(fill="x", pady=(0, 10))

        tk.Label(pp_header, text="ขั้นตอนประมวลผล",
                 font=("Segoe UI Semibold", 9), fg=C["text_dim"], bg=C["surface"]
                 ).pack(side="left")

        self.pipeline_badge = tk.Label(
            pp_header, text="  ว่าง  ", font=("Segoe UI", 8),
            fg=C["text_dim"], bg=C["tag_bg"], padx=6, pady=1
        )
        self.pipeline_badge.pack(side="right")

        # Phase 4: Progress bar สำหรับ pipeline
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Pipeline.Horizontal.TProgressbar",
                        troughcolor=C["surface2"], background=C["accent"],
                        borderwidth=0, thickness=4)
        self.pipeline_progress = ttk.Progressbar(
            pipeline_section, style="Pipeline.Horizontal.TProgressbar",
            orient="horizontal", mode="indeterminate", length=200
        )
        self.pipeline_progress.pack(fill="x", pady=(0, 4))

        # Pipeline flow diagram - Row 1: cutout pipeline
        flow_frame = tk.Frame(pipeline_section, bg=C["surface"])
        flow_frame.pack(fill="x", pady=(0, 4))

        self._make_pipeline_step(flow_frame, "original/", "ต้นฉบับ", C["text_dim"], 0)
        tk.Label(flow_frame, text="\u2192", font=("Segoe UI", 14), fg=C["text_muted"],
                 bg=C["surface"]).grid(row=0, column=1, padx=6)
        self._make_pipeline_step(flow_frame, "cutout/", "ลบพื้นหลัง", C["orange"], 2)
        tk.Label(flow_frame, text="\u2192", font=("Segoe UI", 14), fg=C["text_muted"],
                 bg=C["surface"]).grid(row=0, column=3, padx=6)
        self._make_pipeline_step(flow_frame, "watermarked/", "ลบพื้นหลัง + ลายน้ำ", C["purple"], 4)

        # Pipeline flow diagram - Row 2: watermark-only pipeline
        flow_frame2 = tk.Frame(pipeline_section, bg=C["surface"])
        flow_frame2.pack(fill="x", pady=(4, 10))

        self._make_pipeline_step(flow_frame2, "original/", "ต้นฉบับ", C["text_dim"], 0)
        tk.Label(flow_frame2, text="\u2192", font=("Segoe UI", 14), fg=C["text_muted"],
                 bg=C["surface"]).grid(row=0, column=1, padx=6)
        self._make_pipeline_step(flow_frame2, "watermarked_original/", "ลายน้ำอย่างเดียว", C["green"], 2)

        # Pipeline settings row
        settings_row = tk.Frame(pipeline_section, bg=C["surface"])
        settings_row.pack(fill="x")

        # Cutout toggle
        self.cutout_var = tk.BooleanVar(value=self.config.get("enable_cutout", True))
        tk.Checkbutton(settings_row, text="ลบพื้นหลัง",
                       variable=self.cutout_var, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       command=self._on_toggle_cutout
                       ).pack(side="left", padx=(0, 20))

        # Watermark toggle (on cutout)
        self.wm_var = tk.BooleanVar(value=self.config.get("enable_watermark", True))
        tk.Checkbutton(settings_row, text="ลายน้ำ + ลบพื้นหลัง",
                       variable=self.wm_var, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       command=self._on_toggle_watermark
                       ).pack(side="left", padx=(0, 20))

        # Watermark on original (no BG removal)
        self.wm_orig_var = tk.BooleanVar(value=self.config.get("enable_wm_original", True))
        tk.Checkbutton(settings_row, text="ลายน้ำอย่างเดียว",
                       variable=self.wm_orig_var, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       command=self._on_toggle_wm_original
                       ).pack(side="left", padx=(0, 20))

        # rembg status
        if HAS_REMBG:
            tk.Label(settings_row, text="\u2713 rembg", font=("Consolas", 9),
                     fg=C["green"], bg=C["surface"]).pack(side="right")
        else:
            tk.Label(settings_row, text="\u2717 ยังไม่ได้ติดตั้ง rembg", font=("Consolas", 9),
                     fg=C["red"], bg=C["surface"]).pack(side="right")

        # Watermark file row
        wm_row = tk.Frame(pipeline_section, bg=C["surface"])
        wm_row.pack(fill="x", pady=(8, 0))

        tk.Label(wm_row, text="ลายน้ำ", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left", padx=(0, 8))

        self.wm_path_var = tk.StringVar(value=self.config.get("watermark_path", ""))
        tk.Entry(wm_row, textvariable=self.wm_path_var, font=("Segoe UI", 10),
                 bg=C["surface2"], fg=C["text"], relief="flat",
                 insertbackground=C["text"], highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=3)
        self._make_browse_btn(wm_row, self.browse_watermark).pack(side="left")

        # Watermark options row
        wm_opt = tk.Frame(pipeline_section, bg=C["surface"])
        wm_opt.pack(fill="x", pady=(6, 0))

        tk.Label(wm_opt, text="ความโปร่งใส", font=("Segoe UI", 9),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left", padx=(0, 4))
        self.opacity_var = tk.IntVar(value=self.config.get("watermark_opacity", 40))
        opacity_scale = tk.Scale(wm_opt, from_=10, to=100, orient="horizontal",
                                 variable=self.opacity_var, length=120,
                                 bg=C["surface"], fg=C["text"], troughcolor=C["surface2"],
                                 highlightthickness=0, font=("Segoe UI", 8),
                                 command=lambda v: self._save_wm_settings())
        opacity_scale.pack(side="left", padx=(0, 16))

        tk.Label(wm_opt, text="ขนาด %", font=("Segoe UI", 9),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left", padx=(0, 4))
        self.wm_scale_var = tk.IntVar(value=self.config.get("watermark_scale", 20))
        scale_scale = tk.Scale(wm_opt, from_=5, to=50, orient="horizontal",
                               variable=self.wm_scale_var, length=120,
                               bg=C["surface"], fg=C["text"], troughcolor=C["surface2"],
                               highlightthickness=0, font=("Segoe UI", 8),
                               command=lambda v: self._save_wm_settings())
        scale_scale.pack(side="left", padx=(0, 16))

        tk.Label(wm_opt, text="ตำแหน่ง", font=("Segoe UI", 9),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left", padx=(0, 4))
        self.position_var = tk.StringVar(value=self.config.get("watermark_position", "bottom-right"))
        pos_menu = ttk.Combobox(wm_opt, textvariable=self.position_var, width=12,
                                values=["bottom-right", "bottom-left", "top-right", "top-left", "center"],
                                state="readonly")
        pos_menu.pack(side="left")
        pos_menu.bind("<<ComboboxSelected>>", lambda e: self._save_wm_settings())

        # --- BARCODE SECTION ---
        barcode_section = tk.Frame(main, bg=C["surface"], padx=20, pady=16,
                                   highlightbackground=C["border"], highlightthickness=1)
        barcode_section.pack(fill="x", pady=(0, 8))

        bc_top = tk.Frame(barcode_section, bg=C["surface"])
        bc_top.pack(fill="x")
        tk.Label(bc_top, text="สแกนบาร์โค้ด", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(side="left")
        self.product_tag = tk.Label(bc_top, text="", font=("Segoe UI", 9),
                                    fg=C["accent"], bg=C["tag_bg"], padx=8, pady=2)

        bc_input_row = tk.Frame(barcode_section, bg=C["surface"])
        bc_input_row.pack(fill="x", pady=(10, 0))

        tk.Label(bc_input_row, text="\u2581\u2583\u2585\u2587\u2585\u2583\u2581",
                 font=("Consolas", 16), fg=C["text_dim"], bg=C["barcode_bg"],
                 padx=10, pady=6).pack(side="left")

        self.barcode_entry = tk.Entry(
            bc_input_row, font=("Consolas", 26, "bold"),
            bg=C["barcode_bg"], fg=C["yellow"],
            insertbackground=C["yellow"], relief="flat",
            highlightthickness=2, highlightcolor=C["accent"],
            highlightbackground=C["border"]
        )
        self.barcode_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(2, 0))
        self.barcode_entry.bind("<Return>", self.on_barcode_scan)

        self.product_info_frame = tk.Frame(barcode_section, bg=C["surface"])
        self.product_info_frame.pack(fill="x", pady=(8, 0))
        self.current_state_label = tk.Label(
            self.product_info_frame, text="รอสแกนบาร์โค้ด...",
            font=("Segoe UI", 12), fg=C["text_muted"], bg=C["surface"], anchor="w"
        )
        self.current_state_label.pack(side="left")

        # --- PREVIEW THUMBNAIL ---
        preview_section = tk.Frame(main, bg=C["surface"], padx=20, pady=10,
                                   highlightbackground=C["border"], highlightthickness=1)
        preview_section.pack(fill="x", pady=(0, 8))

        preview_header = tk.Frame(preview_section, bg=C["surface"])
        preview_header.pack(fill="x", pady=(0, 6))
        tk.Label(preview_header, text="ภาพล่าสุด", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(side="left")
        self.preview_info_label = tk.Label(
            preview_header, text="", font=("Segoe UI", 9),
            fg=C["text_muted"], bg=C["surface"]
        )
        self.preview_info_label.pack(side="right")

        self.preview_canvas = tk.Label(
            preview_section, bg=C["surface2"], width=80, height=5,
            relief="flat", anchor="center"
        )
        self.preview_canvas.pack(fill="x", ipady=40)
        self._preview_photo_ref = None  # prevent GC

        # --- ANGLE SELECTION ---
        angle_section = tk.Frame(main, bg=C["surface"], padx=20, pady=16,
                                 highlightbackground=C["border"], highlightthickness=1)
        angle_section.pack(fill="x", pady=(0, 8))

        angle_header = tk.Frame(angle_section, bg=C["surface"])
        angle_header.pack(fill="x", pady=(0, 10))
        tk.Label(angle_header, text="มุมถ่ายภาพ", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(side="left")
        tk.Label(angle_header, text="F1 - F8", font=("Consolas", 9),
                 fg=C["text_muted"], bg=C["tag_bg"], padx=6, pady=1).pack(side="right")

        angles_grid = tk.Frame(angle_section, bg=C["surface"])
        angles_grid.pack(fill="x")

        self.angle_buttons = {}
        for i, angle in enumerate(self.config["angles"]):
            btn_frame = tk.Frame(angles_grid, bg=C["btn_idle"], padx=1, pady=1,
                                 highlightbackground=C["border"], highlightthickness=1)
            btn_frame.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky="nsew")

            btn = tk.Button(
                btn_frame, text=f"{angle.get('label_th', angle['label'])}",
                font=("Segoe UI", 11), bg=C["btn_idle"], fg=C["text"],
                activebackground=C["btn_hover"], activeforeground=C["text"],
                relief="flat", cursor="hand2", height=2,
                command=lambda a=angle["id"]: self.select_angle(a)
            )
            btn.pack(fill="both", expand=True, side="top")

            key_label = tk.Label(btn_frame, text=angle["key"], font=("Consolas", 8),
                                 fg=C["text_muted"], bg=C["btn_idle"])
            key_label.pack(side="bottom", pady=(0, 2))

            count_label = tk.Label(btn_frame, text="", font=("Segoe UI", 8),
                                   fg=C["text_dim"], bg=C["btn_idle"])
            count_label.pack(side="bottom")

            self.angle_buttons[angle["id"]] = (btn, btn_frame, key_label, count_label)

        for c in range(4):
            angles_grid.columnconfigure(c, weight=1)

        # --- 360 SPIN MODE ---
        spin_section = tk.Frame(main, bg=C["surface"], padx=20, pady=14,
                                highlightbackground=C["border"], highlightthickness=1)
        spin_section.pack(fill="x", pady=(0, 8))

        spin_header = tk.Frame(spin_section, bg=C["surface"])
        spin_header.pack(fill="x", pady=(0, 8))
        tk.Label(spin_header, text="โหมดหมุน 360\u00b0", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(side="left")

        self.spin_mode_badge = tk.Label(
            spin_header, text="  ปิด  ", font=("Segoe UI", 8),
            fg=C["text_dim"], bg=C["tag_bg"], padx=6, pady=1
        )
        self.spin_mode_badge.pack(side="right")

        spin_controls = tk.Frame(spin_section, bg=C["surface"])
        spin_controls.pack(fill="x")

        self.spin_toggle_btn = tk.Button(
            spin_controls, text="เริ่ม 360\u00b0",
            font=("Segoe UI Semibold", 11), fg="#fff", bg="#e67e22",
            activebackground="#d35400", relief="flat", cursor="hand2",
            padx=20, pady=6, command=self.toggle_360_mode
        )
        self.spin_toggle_btn.pack(side="left", padx=(0, 16))

        self.video360_btn = tk.Button(
            spin_controls, text="วิดีโอ → 360°",
            font=("Segoe UI Semibold", 11), fg="#fff", bg="#8e44ad",
            activebackground="#7d3c98", relief="flat", cursor="hand2",
            padx=20, pady=6, command=self._video_to_360
        )
        self.video360_btn.pack(side="left", padx=(0, 8))

        # Remove BG checkbox for Video→360
        self.video360_bg_var = tk.BooleanVar(value=self.config.get("video360_remove_bg", False))
        tk.Checkbutton(
            spin_controls, text="ตัด BG",
            variable=self.video360_bg_var, font=("Segoe UI", 10),
            fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
            activebackground=C["surface"], activeforeground=C["text"],
            command=self._on_toggle_video360_bg
        ).pack(side="left", padx=(0, 16))

        tk.Label(spin_controls, text="จำนวนช็อต:", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left", padx=(0, 4))
        self.spin_total_var = tk.IntVar(value=self.config.get("spin360_total", 24))
        spin_total_menu = ttk.Combobox(spin_controls, textvariable=self.spin_total_var,
                                       width=4, values=[12, 24, 36, 72], state="readonly")
        spin_total_menu.pack(side="left", padx=(0, 16))
        spin_total_menu.bind("<<ComboboxSelected>>", lambda e: self._save_spin_settings())

        # Progress display
        self.spin_progress_label = tk.Label(
            spin_controls, text="",
            font=("Consolas", 12, "bold"), fg=C["text_muted"], bg=C["surface"]
        )
        self.spin_progress_label.pack(side="left", padx=(8, 0))

        # Progress bar
        self.spin_progress_frame = tk.Frame(spin_section, bg=C["surface"])
        self.spin_progress_frame.pack(fill="x", pady=(8, 0))

        self.spin_bar_bg = tk.Frame(self.spin_progress_frame, bg=C["surface2"], height=8)
        self.spin_bar_bg.pack(fill="x")
        self.spin_bar_fg = tk.Frame(self.spin_bar_bg, bg=C["text_muted"], height=8, width=0)
        self.spin_bar_fg.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        # --- ACTIVITY LOG ---
        log_section = tk.Frame(main, bg=C["surface"], padx=16, pady=12,
                               highlightbackground=C["border"], highlightthickness=1)
        log_section.pack(fill="both", expand=True)

        log_header = tk.Frame(log_section, bg=C["surface"])
        log_header.pack(fill="x", pady=(0, 8))
        tk.Label(log_header, text="บันทึกกิจกรรม", font=("Segoe UI Semibold", 9),
                 fg=C["text_dim"], bg=C["surface"]).pack(side="left")
        self.photo_count_label = tk.Label(
            log_header, text="0 รูป", font=("Segoe UI", 9),
            fg=C["green"], bg=C["green_dim"], padx=8, pady=2
        )
        self.photo_count_label.pack(side="right")

        log_container = tk.Frame(log_section, bg=C["log_bg"])
        log_container.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_container, bg=C["log_bg"], fg=C["text_dim"],
            font=("Consolas", 9), relief="flat", state="disabled",
            selectbackground=C["accent"], selectforeground="#fff",
            padx=10, pady=6, spacing1=2, highlightthickness=0, borderwidth=0
        )
        scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview,
                                 bg=C["surface2"], troughcolor=C["log_bg"],
                                 highlightthickness=0, borderwidth=0)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_text.tag_configure("success", foreground=C["green"])
        self.log_text.tag_configure("warning", foreground=C["yellow"])
        self.log_text.tag_configure("error", foreground=C["red"])
        self.log_text.tag_configure("info", foreground=C["accent"])
        self.log_text.tag_configure("dim", foreground=C["text_muted"])

    # =========================================================================
    # UI HELPERS
    # =========================================================================
    def _make_browse_btn(self, parent, command):
        return tk.Button(parent, text="...", font=("Segoe UI", 9),
                         bg=C["surface2"], fg=C["text_dim"],
                         activebackground=C["btn_hover"], activeforeground=C["text"],
                         relief="flat", cursor="hand2", padx=8, pady=1, command=command)

    def _make_pipeline_step(self, parent, folder, label, color, col):
        frame = tk.Frame(parent, bg=C["surface2"], padx=12, pady=8,
                         highlightbackground=color, highlightthickness=1)
        frame.grid(row=0, column=col, sticky="nsew")
        tk.Label(frame, text=folder, font=("Consolas", 9, "bold"),
                 fg=color, bg=C["surface2"]).pack()
        tk.Label(frame, text=label, font=("Segoe UI", 8),
                 fg=C["text_dim"], bg=C["surface2"]).pack()
        parent.columnconfigure(col, weight=1)
        return frame

    # =========================================================================
    # SETTINGS HANDLERS
    # =========================================================================
    def browse_watch(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ต้นทาง")
        if folder:
            self.watch_folder_var.set(folder)
            self.config["watch_folder"] = folder
            save_config(self.config)

    def browse_output(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if folder:
            self.output_folder_var.set(folder)
            self.config["output_folder"] = folder
            save_config(self.config)

    def browse_watermark(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ลายน้ำ (PNG โปร่งใส)",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if path:
            self.wm_path_var.set(path)
            self.config["watermark_path"] = path
            save_config(self.config)
            self.log(f"ตั้งค่าลายน้ำ: {os.path.basename(path)}", "info")

    def _on_toggle_cutout(self):
        self.config["enable_cutout"] = self.cutout_var.get()
        save_config(self.config)

    def _on_toggle_watermark(self):
        self.config["enable_watermark"] = self.wm_var.get()
        save_config(self.config)

    def _on_toggle_wm_original(self):
        self.config["enable_wm_original"] = self.wm_orig_var.get()
        save_config(self.config)

    def _save_wm_settings(self):
        self.config["watermark_opacity"] = self.opacity_var.get()
        self.config["watermark_scale"] = self.wm_scale_var.get()
        self.config["watermark_position"] = self.position_var.get()
        self.config["watermark_path"] = self.wm_path_var.get()
        save_config(self.config)

    def _save_spin_settings(self):
        self.config["spin360_total"] = self.spin_total_var.get()
        save_config(self.config)

    def _on_toggle_video360_bg(self):
        self.config["video360_remove_bg"] = self.video360_bg_var.get()
        save_config(self.config)

    # =========================================================================
    # VIDEO → 360°
    # =========================================================================
    def _video_to_360(self):
        """Open a video file and extract evenly-spaced frames to create 360° viewer."""
        if not HAS_CV2:
            messagebox.showerror(
                "ต้องติดตั้ง OpenCV",
                "ฟีเจอร์ วิดีโอ → 360° ต้องติดตั้ง opencv-python\n\n"
                "pip install opencv-python"
            )
            return

        if not self.current_barcode:
            messagebox.showwarning("คำเตือน", "กรุณาสแกนบาร์โค้ดก่อน!")
            return

        output_root = self.config.get("output_folder", "")
        if not output_root:
            messagebox.showerror("ข้อผิดพลาด", "กรุณาตั้งค่าโฟลเดอร์ปลายทางก่อน!")
            return

        # Open file dialog to pick video
        video_path = filedialog.askopenfilename(
            title="เลือกวิดีโอสำหรับ 360°",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm"),
                ("MP4", "*.mp4"),
                ("MOV", "*.mov"),
                ("AVI", "*.avi"),
                ("All files", "*.*"),
            ]
        )
        if not video_path:
            return

        barcode = self.current_barcode
        total_frames = self.spin_total_var.get()
        remove_bg = self.video360_bg_var.get()

        mode_str = " + ลบพื้นหลัง" if remove_bg else ""
        self.log(f"── วิดีโอ → 360°{mode_str}: {os.path.basename(video_path)}", "info")
        self.log(f"   บาร์โค้ด: {barcode} | กำลังแยก {total_frames} เฟรม...", "info")

        if remove_bg and not HAS_REMBG:
            self.log("   ⚠ ยังไม่ได้ติดตั้ง rembg — ข้ามการลบพื้นหลัง", "warning")
            remove_bg = False

        # Disable button during processing
        self.video360_btn.configure(state="disabled", text="กำลังประมวลผล...", bg=C["text_muted"])

        bg_color = tuple(self.config.get("bg_color", [255, 255, 255]))

        # Run extraction in background thread
        threading.Thread(
            target=self._video_to_360_worker,
            args=(video_path, barcode, total_frames, output_root, remove_bg, bg_color),
            daemon=True,
        ).start()

    def _video_to_360_worker(self, video_path, barcode, total_frames, output_root,
                             remove_bg=False, bg_color=(255, 255, 255)):
        """Background thread: extract frames from video → multi-res → viewer.
        If remove_bg=True, runs rembg on each frame and flattens to bg_color."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.after(0, lambda: self.log("   ✗ ไม่สามารถเปิดไฟล์วิดีโอ!", "error"))
                self.after(0, self._video360_btn_reset)
                return

            video_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = video_total / fps if fps > 0 else 0

            # ── Detect limited color range (16-235) common in H.264/H.265 ──
            # OpenCV does NOT auto-convert limited→full range during YUV→BGR.
            # Most camera video (Canon, Sony, etc.) uses limited range.
            limited_range = False

            # Method 1: Check codec pixel format via FFmpeg backend
            # yuv420p=0 → limited; yuvj420p=12 → full (JPEG range)
            try:
                pix_fmt = int(cap.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT))
                FULL_RANGE_FMTS = {12, 13, 14, 25}   # yuvj420p/422p/444p/440p
                LIMITED_RANGE_FMTS = {0, 2, 4, 5, 6, 7, 8, 62, 63, 64, 65, 66, 67}
                if pix_fmt in FULL_RANGE_FMTS:
                    limited_range = False
                elif pix_fmt in LIMITED_RANGE_FMTS:
                    limited_range = True
                # else: unknown → fall through to heuristic
            except Exception as e:
                logger.warning(f"[video360] ตรวจ pixel format ไม่ได้: {e} — ใช้ heuristic แทน")
                limited_range = False  # safe default: assume full range

            # Method 2: Percentile-based heuristic (robust against outliers)
            # Uses grayscale (≈luma) to avoid BGR channel mixing issues
            if not limited_range:
                sample_idx = int(video_total * 0.30)
                cap.set(cv2.CAP_PROP_POS_FRAMES, sample_idx)
                ret_s, sample_frame = cap.read()
                if ret_s and sample_frame is not None:
                    gray = cv2.cvtColor(sample_frame, cv2.COLOR_BGR2GRAY)
                    p995 = float(np.percentile(gray, 99.5))
                    p005 = float(np.percentile(gray, 0.5))
                    # Limited range: brightest area ~220-235; Full: ~250-255
                    if p995 <= 242:
                        limited_range = True
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            range_info = "LIMITED (16-235) → will normalize" if limited_range else "FULL (0-255)"
            self.after(0, lambda: self.log(
                f"   Video: {video_total} frames, {fps:.1f} fps, {duration:.1f}s  |  Color range: {range_info}", "dim"
            ))

            if video_total < total_frames:
                self.after(0, lambda: self.log(
                    f"   ⚠ Video has only {video_total} frames, using {video_total} instead of {total_frames}",
                    "warning"
                ))
                total_frames = video_total

            # Calculate evenly-spaced frame indices
            # Skip first and last few frames (often black/transition)
            margin_pct = 0.02  # skip first/last 2% of video
            start_frame = int(video_total * margin_pct)
            end_frame = int(video_total * (1 - margin_pct))
            usable_frames = end_frame - start_frame

            if usable_frames < total_frames:
                start_frame = 0
                end_frame = video_total
                usable_frames = video_total

            target_indices = set()
            index_list = []
            for i in range(total_frames):
                idx = start_frame + int(i * usable_frames / total_frames)
                idx = min(idx, video_total - 1)
                target_indices.add(idx)
                index_list.append(idx)

            # Create output dirs
            original_dir = os.path.join(output_root, "original", barcode)
            spin_dir = os.path.join(output_root, "360", barcode)
            for d in [original_dir, spin_dir]:
                for sz in ["S", "M", "L", "OG"]:
                    os.makedirs(os.path.join(d, sz), exist_ok=True)

            SIZES = {"S": 480, "M": 800, "L": 1200}
            base_names = []
            extracted = 0

            # Sequential read: decode frames in order (much faster than random seek)
            # Collect target frames into a dict, then process in index order
            collected_frames = {}
            max_target = max(target_indices)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            for fno in range(start_frame, max_target + 1):
                ret, frame = cap.read()
                if not ret:
                    break
                if fno in target_indices:
                    collected_frames[fno] = frame

            for i, frame_idx in enumerate(index_list):
                frame_num = i + 1
                base = f"{barcode}_360_{frame_num:02d}"

                frame = collected_frames.get(frame_idx)
                if frame is None:
                    self.after(0, lambda n=frame_num: self.log(
                        f"   ไม่สามารถอ่านเฟรม {n}", "warning"
                    ))
                    continue

                # Normalize limited color range → full range in YCrCb space.
                # Y (luma):  16-235  → 0-255  (scale = 255/219)
                # Cr/Cb:     16-240  → 0-255  (scale = 255/224)
                # Doing it in YCrCb is correct; doing it in BGR is only
                # approximate because BGR channels mix luma + chroma.
                if limited_range:
                    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb).astype(np.float32)
                    ycrcb[:, :, 0] = np.clip((ycrcb[:, :, 0] - 16.0) * (255.0 / 219.0), 0, 255)
                    ycrcb[:, :, 1] = np.clip((ycrcb[:, :, 1] - 16.0) * (255.0 / 224.0), 0, 255)
                    ycrcb[:, :, 2] = np.clip((ycrcb[:, :, 2] - 16.0) * (255.0 / 224.0), 0, 255)
                    frame = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)

                # Convert BGR (OpenCV) → RGB (PIL)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                orig_w, orig_h = img.size

                # ── Determine image for 360/ ──
                if remove_bg:
                    # Remove background with rembg
                    img_rgba = img.convert("RGBA")
                    cutout = rembg_remove(img_rgba)
                    # USE ONLY ALPHA MASK from rembg — keep original RGB
                    # (rembg sometimes alters foreground colors)
                    alpha = cutout.split()[3]
                    img_orig_rgba = img.convert("RGBA")
                    img_orig_rgba.putalpha(alpha)
                    # Flatten original-color RGBA → RGB on bg_color
                    img_360 = Image.new("RGB", img.size, bg_color)
                    img_360.paste(img_orig_rgba, mask=alpha)
                else:
                    img_360 = img.convert("RGB") if img.mode != "RGB" else img

                # ── Save raw frame to original/ (always keep raw) ──
                img_raw = img.convert("RGB") if img.mode != "RGB" else img
                og_path_orig = os.path.join(original_dir, "OG", f"{base}_OG.jpg")
                img_raw.save(og_path_orig, "JPEG", quality=95,
                             subsampling=0, icc_profile=_SRGB_ICC)

                for sz_key, max_px in SIZES.items():
                    if orig_w <= max_px and orig_h <= max_px:
                        resized = img_raw
                    else:
                        ratio = min(max_px / orig_w, max_px / orig_h)
                        resized = img_raw.resize(
                            (int(orig_w * ratio), int(orig_h * ratio)), Image.LANCZOS
                        )
                    quality = 85 if sz_key == "S" else (90 if sz_key == "M" else 93)
                    resized.save(
                        os.path.join(original_dir, sz_key, f"{base}_{sz_key}.jpg"),
                        "JPEG", quality=quality, subsampling=0, icc_profile=_SRGB_ICC
                    )

                # ── Save processed frame to 360/ (raw or bg-removed) ──
                w360, h360 = img_360.size
                og_path_360 = os.path.join(spin_dir, "OG", f"{base}_OG.jpg")
                img_360.save(og_path_360, "JPEG", quality=95,
                             subsampling=0, icc_profile=_SRGB_ICC)

                for sz_key, max_px in SIZES.items():
                    if w360 <= max_px and h360 <= max_px:
                        resized = img_360
                    else:
                        ratio = min(max_px / w360, max_px / h360)
                        resized = img_360.resize(
                            (int(w360 * ratio), int(h360 * ratio)), Image.LANCZOS
                        )
                    quality = 85 if sz_key == "S" else (90 if sz_key == "M" else 93)
                    resized.save(
                        os.path.join(spin_dir, sz_key, f"{base}_{sz_key}.jpg"),
                        "JPEG", quality=quality, subsampling=0, icc_profile=_SRGB_ICC
                    )

                base_names.append(base)
                extracted += 1

                # Progress update every frame (rembg is slow) or every 4 frames
                step = 1 if remove_bg else 4
                if frame_num % step == 0 or frame_num == total_frames:
                    pct = int(frame_num / total_frames * 100)
                    bg_tag = " [ลบพื้นหลัง]" if remove_bg else ""
                    self.after(0, lambda p=pct, n=frame_num, t=bg_tag: self.log(
                        f"   เฟรม {n}/{total_frames} ({p}%){t}", "dim"
                    ))

            cap.release()

            if not base_names:
                self.after(0, lambda: self.log("   ✗ ไม่สามารถแยกเฟรมจากวิดีโอได้!", "error"))
                self.after(0, self._video360_btn_reset)
                return

            bg_msg = " + ลบพื้นหลัง" if remove_bg else ""
            self.after(0, lambda: self.log(
                f"   ✓ แยกเฟรมสำเร็จ {extracted} เฟรม (S/M/L/OG){bg_msg}", "success"
            ))

            # Build size_map and save _size_map.json
            size_map = {}
            for sz_key in ["S", "M", "L", "OG"]:
                size_map[sz_key] = [f"{sz_key}/{b}_{sz_key}.jpg" for b in base_names]

            with open(os.path.join(spin_dir, "_size_map.json"), "w") as f:
                json.dump(size_map, f)

            # Generate viewer.html — images are already in 360/ so use
            # _generate_360_viewer which will use fast-path copy (harmless
            # since files already exist, shutil.copy2 will just overwrite)
            self._generate_360_viewer(barcode, extracted)

            # Open viewer in browser
            viewer_path = os.path.join(spin_dir, "viewer.html")
            if os.path.exists(viewer_path):
                import webbrowser
                webbrowser.open(viewer_path)

            self.after(0, self._video360_btn_reset)

        except Exception as e:
            self.after(0, lambda: self.log(f"   ✗ วิดีโอ → 360° ล้มเหลว: {e}", "error"))
            self.after(0, self._video360_btn_reset)

    def _video360_btn_reset(self):
        """Reset the VIDEO → 360° button back to normal state."""
        self.video360_btn.configure(
            state="normal", text="วิดีโอ → 360°", bg="#8e44ad"
        )

    # =========================================================================
    # 360 SPIN MODE
    # =========================================================================
    def toggle_360_mode(self):
        if not self.current_barcode:
            messagebox.showwarning("คำเตือน", "กรุณาสแกนบาร์โค้ดก่อน!")
            return

        if self.is_360_mode:
            self._stop_360_mode()
        else:
            self._start_360_mode()

    def _start_360_mode(self):
        self.is_360_mode = True
        self.spin360_counter = 0
        self.current_angle = "360"
        total = self.spin_total_var.get()

        # Update UI
        self.spin_toggle_btn.configure(text="หยุด 360\u00b0", bg=C["red"])
        self.spin_mode_badge.configure(text="  ทำงาน  ", fg=C["orange"])
        self.spin_progress_label.configure(
            text=f"0 / {total}", fg=C["yellow"]
        )
        self.spin_bar_fg.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        # Dim angle buttons
        for aid, (btn, frame, key_lbl, cnt_lbl) in self.angle_buttons.items():
            btn.configure(state="disabled", bg=C["surface2"])
            frame.configure(bg=C["surface2"])

        self.current_state_label.configure(
            text=f"{self.current_barcode}  \u2014  โหมด 360\u00b0  \u2014  0/{total}",
            fg=C["orange"]
        )
        self.log(f"   360\u00b0 เริ่ม: {self.current_barcode} ({total} ช็อต)", "info")
        self.barcode_entry.focus_set()

    def _stop_360_mode(self):
        self.is_360_mode = False
        total = self.spin_total_var.get()
        count = self.spin360_counter

        # Update UI
        self.spin_toggle_btn.configure(text="เริ่ม 360\u00b0", bg="#e67e22")
        self.spin_mode_badge.configure(text="  ปิด  ", fg=C["text_dim"])

        # Re-enable angle buttons
        for aid, (btn, frame, key_lbl, cnt_lbl) in self.angle_buttons.items():
            btn.configure(state="normal", bg=C["btn_idle"])
            frame.configure(bg=C["btn_idle"])

        self.current_angle = ""

        if count > 0:
            self.log(f"   360\u00b0 เสร็จ: {count}/{total} ช็อต", "info")
            # Generate HTML viewer in background thread (don't block UI)
            if count >= 2:
                barcode = self.current_barcode  # capture before it changes
                self.log(f"   \u23f3 กำลังสร้าง 360\u00b0 viewer...", "info")
                threading.Thread(
                    target=self._generate_360_viewer_bg,
                    args=(barcode, count),
                    daemon=True,
                ).start()

    def _update_360_progress(self):
        total = self.spin_total_var.get()
        count = self.spin360_counter
        progress = count / total if total > 0 else 0

        self.spin_progress_label.configure(
            text=f"{count} / {total}",
            fg=C["green"] if count >= total else C["yellow"]
        )
        self.spin_bar_fg.configure(bg=C["green"] if count >= total else C["orange"])
        self.spin_bar_fg.place(x=0, y=0, relheight=1.0, relwidth=progress)

        self.current_state_label.configure(
            text=f"{self.current_barcode}  \u2014  โหมด 360\u00b0  \u2014  {count}/{total}",
            fg=C["green"] if count >= total else C["orange"]
        )

        # Auto-stop when complete
        if count >= total:
            self.log(f"   360\u00b0 เสร็จสมบูรณ์! ({total} ช็อต)", "success")
            self._stop_360_mode()

    def _generate_360_viewer_bg(self, barcode, total_shots):
        """Background thread wrapper — catches errors that would be swallowed."""
        try:
            self._generate_360_viewer(barcode, total_shots)
        except Exception as e:
            self.after(0, lambda: self.log(f"   \u2717 360\u00b0 Viewer ล้มเหลว: {e}", "error"))

    def _generate_360_viewer(self, barcode, total_shots):
        """Generate an HTML file with interactive 360 spin viewer + multi-resolution.
        Can be called from background thread — uses self.after() for GUI updates."""
        output_root = self.config["output_folder"]
        spin_dir = os.path.join(output_root, "360", barcode)
        original_dir = os.path.join(output_root, "original", barcode)

        # Resolution presets: S, M, L, OG
        SIZES = {
            "S": 480,
            "M": 800,
            "L": 1200,
        }

        # Create subfolders
        for sz in list(SIZES.keys()) + ["OG"]:
            os.makedirs(os.path.join(spin_dir, sz), exist_ok=True)

        supported_ext = self.config.get("image_extensions",
                                         [".jpg", ".jpeg", ".cr2", ".cr3", ".arw", ".nef", ".tif", ".tiff", ".png"])

        base_names = []
        copied_count = 0
        resized_count = 0

        for i in range(1, total_shots + 1):
            base = f"{barcode}_360_{i:02d}"

            # === FAST PATH: copy pre-generated S/M/L/OG from original/ ===
            all_copied = True
            for sz_key in ["S", "M", "L", "OG"]:
                src = os.path.join(original_dir, sz_key, f"{base}_{sz_key}.jpg")
                dst = os.path.join(spin_dir, sz_key, f"{base}_{sz_key}.jpg")
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                else:
                    all_copied = False
                    break

            if all_copied:
                base_names.append(base)
                copied_count += 1
                continue

            # === SLOW PATH: open source image and resize ===
            src_path = None
            og_path = os.path.join(original_dir, "OG", f"{base}_OG.jpg")
            if os.path.exists(og_path):
                src_path = og_path
            else:
                # Check root folder (old structure / any extension)
                for ext in supported_ext:
                    fname = f"{base}{ext}"
                    img_path = os.path.join(original_dir, fname)
                    if os.path.exists(img_path):
                        src_path = img_path
                        break

            if not src_path:
                self.after(0, lambda i=i: self.log(f"   360 เฟรม {i}: ไม่พบไฟล์ต้นฉบับ", "warning"))
                continue

            try:
                img = _to_srgb(Image.open(src_path))
                icc = img.info.get("icc_profile", _SRGB_ICC)
                orig_w, orig_h = img.size

                # OG - original size
                img.save(os.path.join(spin_dir, "OG", f"{base}_OG.jpg"), "JPEG",
                         quality=95, subsampling=0, icc_profile=icc)

                # S, M, L - resize (use MULTI_RES quality config)
                for sz_key, max_px in SIZES.items():
                    if orig_w <= max_px and orig_h <= max_px:
                        resized = img
                    else:
                        ratio = min(max_px / orig_w, max_px / orig_h)
                        resized = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.LANCZOS)
                    q = MULTI_RES[sz_key]["quality"] if sz_key in MULTI_RES else 93
                    resized.save(os.path.join(spin_dir, sz_key, f"{base}_{sz_key}.jpg"), "JPEG",
                                 quality=q, subsampling=0, icc_profile=icc)

                base_names.append(base)
                resized_count += 1

            except Exception as e:
                self.after(0, lambda e=e, i=i: self.log(f"   360 ปรับขนาดเฟรม {i} ผิดพลาด: {e}", "warning"))

        if not base_names:
            self.after(0, lambda: self.log("   \u2717 ไม่พบรูป 360 สำหรับสร้าง viewer", "warning"))
            return

        # Build JSON maps for each size
        size_map = {}
        for sz_key in ["S", "M", "L", "OG"]:
            size_map[sz_key] = [f"{sz_key}/{b}_{sz_key}.jpg" for b in base_names]

        # Save _size_map.json (for gen_viewer.py fallback)
        with open(os.path.join(spin_dir, "_size_map.json"), "w") as f:
            json.dump(size_map, f)

        n_frames = len(base_names)
        safe_barcode = html_mod.escape(barcode, quote=True)
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>360 View - {safe_barcode}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #1a1a2e; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: 'Segoe UI', sans-serif; color: #e2e4ed; }}
h1 {{ margin-bottom: 16px; font-size: 20px; font-weight: 400; color: #6b7394; }}
h1 span {{ color: #6c8cff; font-weight: 600; }}
.viewer {{ position: relative; cursor: grab; user-select: none; border: 2px solid #2e3348; border-radius: 8px; overflow: hidden; background: #fff; touch-action: none; }}
canvas {{ display: block; }}
.hint {{ margin-top: 16px; color: #4a5170; font-size: 13px; }}
.controls {{ display: flex; gap: 16px; margin-top: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }}
.bar {{ display: flex; gap: 4px; margin-top: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; background: #2e3348; transition: background 0.1s; }}
.dot.a {{ background: #6c8cff; }}
.info {{ margin-top: 10px; color: #4a5170; font-size: 12px; }}
.zoom-bar {{ display: flex; align-items: center; gap: 8px; }}
.zoom-bar button {{ background: #2e3348; color: #e2e4ed; border: none; border-radius: 4px; width: 30px; height: 30px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
.zoom-bar button:hover {{ background: #6c8cff; }}
.zoom-label {{ font-size: 13px; color: #6b7394; min-width: 50px; text-align: center; }}
.zoom-slider {{ -webkit-appearance: none; width: 100px; height: 4px; background: #2e3348; border-radius: 2px; outline: none; }}
.zoom-slider::-webkit-slider-thumb {{ -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: #6c8cff; cursor: pointer; }}
.loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); color: #6c8cff; font-size: 14px; z-index: 10; }}
.res-bar {{ display: flex; gap: 4px; align-items: center; }}
.res-bar span {{ font-size: 11px; color: #6b7394; margin-right: 4px; }}
.res-btn {{ background: #2e3348; color: #8890a8; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }}
.res-btn:hover {{ background: #3a4060; color: #e2e4ed; }}
.res-btn.active {{ background: #6c8cff; color: #fff; }}
</style>
</head>
<body>
<h1>360&deg; <span>{safe_barcode}</span></h1>
<div class="viewer" id="viewer">
    <canvas id="cv"></canvas>
    <div class="loading" id="loading">Loading 0%</div>
</div>
<p class="hint">Drag = Rotate (with momentum) &nbsp;|&nbsp; Scroll = Zoom &nbsp;|&nbsp; Double-click = Reset</p>
<div class="controls">
    <div class="zoom-bar">
        <button id="zo" title="Zoom Out">&minus;</button>
        <input type="range" class="zoom-slider" id="zs" min="100" max="500" value="100">
        <button id="zi" title="Zoom In">+</button>
        <span class="zoom-label" id="zl">100%</span>
    </div>
    <div class="res-bar">
        <span>Quality:</span>
        <button class="res-btn" data-sz="S">S <small>({SIZES['S']}px)</small></button>
        <button class="res-btn" data-sz="M">M <small>({SIZES['M']}px)</small></button>
        <button class="res-btn active" data-sz="L">L <small>({SIZES['L']}px)</small></button>
        <button class="res-btn" data-sz="OG">OG</button>
    </div>
</div>
<div class="bar" id="bar"></div>
<p class="info" id="info">Frame 1 / {n_frames}</p>
<script>
(function(){{
var SIZE_MAP = {json.dumps(size_map)};
var curSize = 'L';
var SRC = SIZE_MAP[curSize];
var N = SRC.length;

// Canvas size — will be set after first image loads to match aspect ratio
var MAX_CW = 900;
var CW = MAX_CW, CH = MAX_CW;
var aspectDetected = false;

var cv = document.getElementById('cv');
var ctx = cv.getContext('2d');
var viewer = document.getElementById('viewer');
var info = document.getElementById('info');
var bar = document.getElementById('bar');
var loadEl = document.getElementById('loading');
var slider = document.getElementById('zs');
var zLabel = document.getElementById('zl');

cv.width = CW; cv.height = CH;

// ── Preload frames per size ──
var frames = new Array(N);
var dots = [];
var frameCache = {{}};

for (var i = 0; i < N; i++) {{
    var d = document.createElement('div');
    d.className = 'dot' + (i === 0 ? ' a' : '');
    bar.appendChild(d);
    dots.push(d);
}}

function adaptCanvas(bmp) {{
    if (aspectDetected) return;
    aspectDetected = true;
    var iw = bmp.width, ih = bmp.height;
    if (iw > 0 && ih > 0) {{
        var ratio = ih / iw;
        CW = Math.min(MAX_CW, Math.max(600, iw));
        CH = Math.round(CW * ratio);
        // Clamp height
        if (CH > 800) {{ CH = 800; CW = Math.round(CH / ratio); }}
        if (CH < 300) {{ CH = 300; CW = Math.round(CH / ratio); }}
        cv.width = CW; cv.height = CH;
    }}
}}

function loadSize(sz, onDone) {{
    if (frameCache[sz]) {{
        frames = frameCache[sz];
        if (onDone) onDone();
        return;
    }}
    var arr = new Array(N);
    var cnt = 0;
    loadEl.style.display = '';
    loadEl.textContent = 'Loading ' + sz + ' 0%';
    var srcs = SIZE_MAP[sz];
    for (var i = 0; i < N; i++) {{
        var im = new Image();
        im.src = srcs[i];
        im.onload = (function(idx) {{
            return function() {{
                createImageBitmap(this).then(function(bmp) {{
                    if (idx === 0) adaptCanvas(bmp);
                    arr[idx] = bmp;
                    cnt++;
                    loadEl.textContent = 'Loading ' + sz + ' ' + Math.round(cnt/N*100) + '%';
                    if (cnt === N) {{
                        frameCache[sz] = arr;
                        frames = arr;
                        loadEl.style.display = 'none';
                        if (onDone) onDone();
                    }}
                }});
            }};
        }})(i);
    }}
}}

loadSize('L', function() {{ draw(); }});

// ── Resolution switcher ──
var resButtons = document.querySelectorAll('.res-btn');
resButtons.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
        var sz = this.dataset.sz;
        if (sz === curSize) return;
        curSize = sz;
        SRC = SIZE_MAP[sz];
        resButtons.forEach(function(b) {{ b.classList.remove('active'); }});
        this.classList.add('active');
        loadSize(sz, function() {{ draw(); }});
    }});
}});

// ── State ──
var cur = 0, zoom = 1, panX = 0, panY = 0;
var dirty = true;

function draw() {{
    if (!frames[cur]) return;
    ctx.setTransform(1,0,0,1,0,0);
    ctx.clearRect(0, 0, CW, CH);
    ctx.setTransform(zoom, 0, 0, zoom, panX, panY);
    var f = frames[cur];
    // Fill canvas completely — no letterboxing
    var scale = Math.max(CW / f.width, CH / f.height);
    var w = f.width * scale, h = f.height * scale;
    var x = (CW - w) / 2, y = (CH - h) / 2;
    ctx.drawImage(f, x, y, w, h);
    dirty = false;
}}

function schedDraw() {{
    if (!dirty) {{ dirty = true; requestAnimationFrame(draw); }}
}}

function show(idx) {{
    cur = ((idx % N) + N) % N;
    info.textContent = 'Frame ' + (cur+1) + ' / ' + N;
    for (var i = 0; i < N; i++) dots[i].className = i === cur ? 'dot a' : 'dot';
    schedDraw();
}}

// ── Zoom ──
var ZMIN = 1, ZMAX = 5;

function applyZoomUI() {{
    var p = Math.round(zoom * 100);
    slider.value = p;
    zLabel.textContent = p + '%';
    viewer.style.cursor = zoom > 1 ? 'move' : 'grab';
}}

function zoomAt(nz, cx, cy) {{
    nz = Math.min(ZMAX, Math.max(ZMIN, nz));
    var ix = (cx - panX) / zoom;
    var iy = (cy - panY) / zoom;
    panX = cx - ix * nz;
    panY = cy - iy * nz;
    zoom = nz;
    if (zoom <= 1) {{ zoom = 1; panX = 0; panY = 0; }}
    applyZoomUI(); schedDraw();
}}

function zoomCtr(nz) {{ zoomAt(nz, CW/2, CH/2); }}

// ── Inertia physics ──
var dragging = false, panning = false, lastX = 0, lastY = 0;
var velocity = 0, lastMoveTime = 0, accumDx = 0;
var inertiaRaf = 0;
var FRICTION = 0.92;
var VEL_SCALE = 0.3;
var VEL_MIN = 0.08;

function stopInertia() {{ cancelAnimationFrame(inertiaRaf); inertiaRaf = 0; velocity = 0; }}

function startInertia() {{
    if (Math.abs(velocity) < VEL_MIN) return;
    function tick() {{
        velocity *= FRICTION;
        if (Math.abs(velocity) < VEL_MIN) {{ velocity = 0; return; }}
        accumDx += velocity;
        var steps = Math.trunc(accumDx);
        if (steps !== 0) {{ show(cur + steps); accumDx -= steps; }}
        inertiaRaf = requestAnimationFrame(tick);
    }}
    accumDx = 0;
    inertiaRaf = requestAnimationFrame(tick);
}}

// ── Auto-play ──
var autoplay = null, autoDelay = null;
function stopAuto() {{ clearTimeout(autoDelay); clearInterval(autoplay); autoplay = null; autoDelay = null; }}

// ── Mouse drag + inertia ──
viewer.addEventListener('mousedown', function(e) {{
    stopInertia();
    stopAuto();
    if (zoom > 1) {{
        panning = true;
    }} else {{
        dragging = true;
        velocity = 0;
        lastMoveTime = performance.now();
    }}
    lastX = e.clientX; lastY = e.clientY;
    e.preventDefault();
}});

window.addEventListener('mousemove', function(e) {{
    if (dragging) {{
        var now = performance.now();
        var dx = e.clientX - lastX;
        var sens = Math.max(3, Math.round(CW / N));
        velocity = (dx / sens) * VEL_SCALE;
        velocity = Math.max(-4, Math.min(4, velocity));
        if (Math.abs(dx) > sens) {{
            show(cur + (dx > 0 ? 1 : -1));
            lastX = e.clientX;
        }}
        lastMoveTime = now;
    }} else if (panning) {{
        panX += e.clientX - lastX;
        panY += e.clientY - lastY;
        lastX = e.clientX; lastY = e.clientY;
        applyZoomUI(); schedDraw();
    }}
}});

window.addEventListener('mouseup', function() {{
    if (dragging) {{
        dragging = false;
        if (performance.now() - lastMoveTime < 100) {{
            startInertia();
        }}
    }}
    panning = false;
}});

// ── Touch + inertia + pinch-zoom ──
var pinching = false, pinchDist = 0, pinchZoom = 1;
function getTouchDist(t) {{ return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }}
function getTouchCenter(t) {{ return [(t[0].clientX + t[1].clientX) / 2, (t[0].clientY + t[1].clientY) / 2]; }}

viewer.addEventListener('touchstart', function(e) {{
    stopAuto(); stopInertia();
    if (e.touches.length === 2) {{
        pinching = true; dragging = false; panning = false;
        pinchDist = getTouchDist(e.touches);
        pinchZoom = zoom;
        e.preventDefault(); return;
    }}
    pinching = false;
    if (zoom > 1) {{ panning = true; }} else {{
        dragging = true; velocity = 0; lastMoveTime = performance.now();
    }}
    lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
}}, {{ passive: false }});

window.addEventListener('touchmove', function(e) {{
    if (pinching && e.touches.length === 2) {{
        e.preventDefault();
        var nd = getTouchDist(e.touches);
        var center = getTouchCenter(e.touches);
        var rect = cv.getBoundingClientRect();
        zoomAt(pinchZoom * nd / pinchDist,
               (center[0] - rect.left) * (CW / rect.width),
               (center[1] - rect.top) * (CH / rect.height));
        return;
    }}
    if (dragging) {{
        var dx = e.touches[0].clientX - lastX;
        var sens = Math.max(3, Math.round(CW / N));
        velocity = (dx / sens) * VEL_SCALE;
        velocity = Math.max(-4, Math.min(4, velocity));
        if (Math.abs(dx) > sens) {{ show(cur + (dx > 0 ? 1 : -1)); lastX = e.touches[0].clientX; }}
        lastMoveTime = performance.now();
    }} else if (panning) {{
        panX += e.touches[0].clientX - lastX;
        panY += e.touches[0].clientY - lastY;
        lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
        applyZoomUI(); schedDraw();
    }}
}}, {{ passive: false }});

window.addEventListener('touchend', function(e) {{
    if (e.touches.length < 2) pinching = false;
    if (e.touches.length === 0) {{
        if (dragging && performance.now() - lastMoveTime < 100) startInertia();
        dragging = false; panning = false;
    }}
}});

// ── Scroll zoom ──
viewer.addEventListener('wheel', function(e) {{
    e.preventDefault(); stopAuto(); stopInertia();
    var rect = cv.getBoundingClientRect();
    var f = 1.12;
    zoomAt(e.deltaY < 0 ? zoom * f : zoom / f,
           (e.clientX - rect.left) * (CW / rect.width),
           (e.clientY - rect.top) * (CH / rect.height));
}}, {{ passive: false }});

// ── Buttons ──
document.getElementById('zi').addEventListener('click', function() {{ zoomCtr(zoom * 1.3); }});
document.getElementById('zo').addEventListener('click', function() {{ zoomCtr(zoom / 1.3); }});
slider.addEventListener('input', function() {{ zoomCtr(parseInt(slider.value) / 100); }});

viewer.addEventListener('dblclick', function() {{
    zoom = 1; panX = 0; panY = 0; stopInertia();
    applyZoomUI(); schedDraw();
}});

// ── Keyboard ──
window.addEventListener('keydown', function(e) {{
    if (e.key === 'ArrowLeft') {{ stopInertia(); show(cur - 1); }}
    else if (e.key === 'ArrowRight') {{ stopInertia(); show(cur + 1); }}
    else if (e.key === '+' || e.key === '=') zoomCtr(zoom * 1.15);
    else if (e.key === '-') zoomCtr(zoom / 1.15);
    else if (e.key === '0') {{ zoom = 1; panX = 0; panY = 0; stopInertia(); applyZoomUI(); schedDraw(); }}
    else if (e.key === '1') document.querySelector('[data-sz="S"]').click();
    else if (e.key === '2') document.querySelector('[data-sz="M"]').click();
    else if (e.key === '3') document.querySelector('[data-sz="L"]').click();
    else if (e.key === '4') document.querySelector('[data-sz="OG"]').click();
}});

// ── Auto-play hover ──
viewer.addEventListener('mouseenter', function() {{
    if (zoom <= 1 && !dragging && velocity === 0) {{
        autoDelay = setTimeout(function() {{
            if (!dragging && !panning && zoom <= 1 && velocity === 0)
                autoplay = setInterval(function() {{ show(cur + 1); }}, 120);
        }}, 800);
    }}
}});
viewer.addEventListener('mouseleave', stopAuto);
viewer.addEventListener('mousedown', stopAuto);

}})();
</script>
</body>
</html>"""

        html_path = os.path.join(spin_dir, "viewer.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        method = f"คัดลอก {copied_count}" if copied_count else f"ปรับขนาด {resized_count}"
        self.after(0, lambda: self.log(
            f"   \u2713 360 Viewer: 360/{barcode}/viewer.html ({n_frames} เฟรม, {method})", "success"
        ))

    def _update_preview(self, image_path):
        """Show thumbnail of the last captured image in the preview panel."""
        try:
            img = Image.open(image_path)
            # Fit within 400x150
            max_w, max_h = 400, 150
            ratio = min(max_w / img.width, max_h / img.height)
            if ratio < 1:
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.preview_canvas.configure(image=photo)
            self._preview_photo_ref = photo  # prevent GC
            fname = os.path.basename(image_path)
            self.preview_info_label.configure(text=fname)
        except Exception as e:
            logger.warning(f"[preview] แสดงภาพตัวอย่างไม่ได้: {e}")

    def _update_pipeline_status(self):
        pending = self.pipeline_pending
        if pending <= 0:
            self.pipeline_pending = 0
            self.pipeline_badge.configure(
                text="  ว่าง  ", fg=C["text_dim"], bg=C["tag_bg"]
            )
            self.pipeline_progress.stop()
            self.pipeline_progress.configure(value=0)
        else:
            self.pipeline_badge.configure(
                text=f"  กำลังประมวลผล {pending}  ", fg="#fff", bg=C["orange"]
            )
            if not self.pipeline_progress.cget("mode") == "indeterminate":
                self.pipeline_progress.configure(mode="indeterminate")
            self.pipeline_progress.start(15)

    def _on_pipeline_done(self):
        """Called by ImageProcessor after finishing one task."""
        self.pipeline_pending = max(0, self.pipeline_pending - 1)
        self._update_pipeline_status()
        # แสดงพื้นที่ดิสก์ใน log ทุก 10 งาน
        if self.pipeline_pending == 0:
            output_root = self.config.get("output_folder", "")
            if output_root:
                try:
                    stat = shutil.disk_usage(output_root)
                    free_gb = stat.free / (1024 ** 3)
                    self.log(f"   💾 พื้นที่เหลือ: {free_gb:.1f} GB", "dim")
                except OSError:
                    pass

    # =========================================================================
    # BARCODE
    # =========================================================================
    def on_barcode_scan(self, event=None):
        raw = self.barcode_entry.get().strip()
        if not raw:
            return
        barcode = _sanitize_barcode(raw)

        # Stop 360 mode if active
        if self.is_360_mode:
            self._stop_360_mode()

        self.current_barcode = barcode
        self.current_angle = ""
        self.angle_counters = {}

        for aid, (btn, frame, key_lbl, cnt_lbl) in self.angle_buttons.items():
            btn.configure(bg=C["btn_idle"], fg=C["text"])
            frame.configure(bg=C["btn_idle"])
            key_lbl.configure(bg=C["btn_idle"])
            cnt_lbl.configure(bg=C["btn_idle"], text="")

        product = self.product_db.lookup(barcode)
        if product and product["name"]:
            self.current_product_info = product
            tag_text = f"  {product['name']}"
            if product["category"]:
                tag_text += f"  |  {product['category']}"
            self.product_tag.configure(text=tag_text)
            self.product_tag.pack(side="right")
        else:
            self.current_product_info = None
            self.product_tag.configure(text="  สินค้าใหม่  ")
            self.product_tag.pack(side="right")
            self.product_db.add(barcode)

        self.current_state_label.configure(
            text=f"{barcode}  \u2014  เลือกมุมถ่ายภาพ", fg=C["yellow"]
        )
        self.log(f"\u2500\u2500 สแกน: {barcode}", "info")
        self.barcode_entry.delete(0, tk.END)
        self.barcode_entry.focus_set()

    # =========================================================================
    # ANGLE SELECTION
    # =========================================================================
    def select_angle(self, angle_id):
        if not self.current_barcode:
            messagebox.showwarning("คำเตือน", "กรุณาสแกนบาร์โค้ดก่อน!")
            return

        # Block angle change during 360 mode
        if self.is_360_mode:
            self.log("   ไม่สามารถเปลี่ยนมุมระหว่างโหมด 360°", "warning")
            return

        self.current_angle = angle_id

        label = angle_id
        label_th = angle_id
        for a in self.config["angles"]:
            if a["id"] == angle_id:
                label = a["label"]
                label_th = a.get("label_th", label)
                break

        for aid, (btn, frame, key_lbl, cnt_lbl) in self.angle_buttons.items():
            if aid == angle_id:
                btn.configure(bg=C["btn_active"], fg="#ffffff")
                frame.configure(bg=C["btn_active"], highlightbackground=C["accent"])
                key_lbl.configure(bg=C["btn_active"], fg="#ffffff")
                cnt_lbl.configure(bg=C["btn_active"], fg="#ffffff")
            else:
                btn.configure(bg=C["btn_idle"], fg=C["text"])
                frame.configure(bg=C["btn_idle"], highlightbackground=C["border"])
                key_lbl.configure(bg=C["btn_idle"], fg=C["text_muted"])
                cnt_lbl.configure(bg=C["btn_idle"], fg=C["text_dim"])

        count = self.angle_counters.get(angle_id, 0)
        self.current_state_label.configure(
            text=f"{self.current_barcode}  \u2014  {label_th} ({label})  \u2014  {count} รูป",
            fg=C["accent"]
        )
        self.log(f"   มุม: {label_th} ({label})", "dim")
        self.barcode_entry.focus_set()

    # =========================================================================
    # WATCH FOLDER
    # =========================================================================
    def toggle_watching(self):
        if self.is_watching:
            self.stop_watching()
        else:
            self.start_watching()

    def start_watching(self):
        watch_dir = self.watch_folder_var.get()
        output_dir = self.output_folder_var.get()

        if not watch_dir or not os.path.isdir(watch_dir):
            messagebox.showerror("ข้อผิดพลาด", "กรุณาเลือกโฟลเดอร์ต้นทางที่ถูกต้อง")
            return
        if not output_dir:
            messagebox.showerror("ข้อผิดพลาด", "กรุณาเลือกโฟลเดอร์ปลายทาง")
            return

        self.config["watch_folder"] = watch_dir
        self.config["output_folder"] = output_dir
        save_config(self.config)

        # Create all output sub-directories
        for sub in ["original", "cutout", "watermarked", "watermarked_original", "360"]:
            os.makedirs(os.path.join(output_dir, sub), exist_ok=True)

        handler = PhotoWatcher(self, self.config["image_extensions"])
        self.observer = Observer()
        self.observer.schedule(handler, watch_dir, recursive=False)
        self.observer.start()
        self.is_watching = True

        self.watch_btn.configure(text="หยุด", bg=C["red"])
        self.status_dot.configure(fg=C["green"])
        self.status_text.configure(text="  กำลังทำงาน", fg=C["green"])

        self.log(f"กำลังดูโฟลเดอร์: {watch_dir}", "success")
        self.log(f"ปลายทาง: {output_dir}", "dim")

    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.is_watching = False
        self.watch_btn.configure(text="เริ่ม", bg=C["green"])
        self.status_dot.configure(fg=C["red"])
        self.status_text.configure(text="  หยุดอยู่", fg=C["red"])
        self.log("หยุดการเฝ้าดูแล้ว", "warning")

    # =========================================================================
    # PROCESS NEW PHOTO
    # =========================================================================
    def process_new_photo(self, filepath):
        if not self.current_barcode:
            self.log(f"ไฟล์ใหม่: {os.path.basename(filepath)} \u2014 ยังไม่ได้สแกนบาร์โค้ด!", "warning")
            return
        if not self.current_angle:
            self.log(f"ไฟล์ใหม่: {os.path.basename(filepath)} \u2014 ยังไม่ได้เลือกมุม!", "warning")
            self.current_state_label.configure(
                text=f"{self.current_barcode}  \u2014  กรุณาเลือกมุมถ่ายก่อน!", fg=C["red"]
            )
            return

        barcode = self.current_barcode
        angle = self.current_angle
        ext = os.path.splitext(filepath)[1].lower()
        output_root = self.config["output_folder"]

        # Phase 3: ตรวจสอบพื้นที่ดิสก์ก่อนบันทึก
        if output_root and not self._check_disk_space(output_root, warn_only=False):
            return

        # --- 360 MODE ---
        if self.is_360_mode and angle == "360":
            self.spin360_counter += 1
            count = self.spin360_counter
            new_filename = f"{barcode}_360_{count:02d}{ext}"

            original_dir = os.path.join(output_root, "original", barcode)
            os.makedirs(original_dir, exist_ok=True)
            original_path = os.path.join(original_dir, new_filename)

            try:
                if self.config.get("copy_mode"):
                    shutil.copy2(filepath, original_path)
                else:
                    shutil.move(filepath, original_path)

                self.session_photos.append({
                    "barcode": barcode, "angle": "360",
                    "filename": new_filename, "path": original_path,
                    "time": datetime.now().strftime("%H:%M:%S"),
                })

                self.log(f"   \u2713 360\u00b0 #{count}: {new_filename}", "success")

                # Generate multi-resolution (S/M/L/OG) then remove root file
                try:
                    orig_img = _to_srgb(Image.open(original_path))
                    base_name = os.path.splitext(new_filename)[0]
                    save_multi_resolution(orig_img, original_dir, base_name)
                    og_path = os.path.join(original_dir, "OG", f"{base_name}_OG.jpg")
                    if os.path.exists(og_path):
                        os.remove(original_path)
                    self.log(f"   \u2713 Multi-Res: S/M/L/OG", "dim")
                    # Preview: show S thumbnail
                    s_path = os.path.join(original_dir, "S", f"{base_name}_S.jpg")
                    if os.path.exists(s_path):
                        self._update_preview(s_path)
                except Exception as e:
                    self.log(f"   ปรับขนาดหลายระดับผิดพลาด: {e}", "warning")

                total = len(self.session_photos)
                self.photo_count_label.configure(text=f"{total} รูป")
                self.session_badge.configure(text=f"  เซสชัน: {total} รูป  ")
                self._save_session()

                self._update_360_progress()

            except Exception as e:
                self.log(f"   ข้อผิดพลาด: {e}", "error")
            return

        # --- NORMAL MODE ---
        # Duplicate detection: check if files already exist for this barcode+angle
        count = self.angle_counters.get(angle, 0) + 1
        if count == 1:
            existing_dir = os.path.join(output_root, "original", barcode, "OG")
            if os.path.isdir(existing_dir):
                existing = [f for f in os.listdir(existing_dir)
                            if f.startswith(f"{barcode}_{angle}_")]
                if existing:
                    ok = messagebox.askyesno(
                        "พบไฟล์ซ้ำ",
                        f"บาร์โค้ด '{barcode}' มุม '{angle}' มีรูปอยู่แล้ว "
                        f"{len(existing)} รูป\n\nต้องการถ่ายเพิ่มหรือไม่?",
                    )
                    if not ok:
                        self.log(f"   ข้ามไฟล์ซ้ำ: {barcode}/{angle}", "warning")
                        return
                    count = len(existing) + 1
                    self.angle_counters[angle] = count - 1

        self.angle_counters[angle] = count

        new_filename = f"{barcode}_{angle}_{count:02d}{ext}"

        # Save original to original/ subfolder
        original_dir = os.path.join(output_root, "original", barcode)
        os.makedirs(original_dir, exist_ok=True)
        original_path = os.path.join(original_dir, new_filename)

        try:
            if self.config.get("copy_mode"):
                shutil.copy2(filepath, original_path)
            else:
                shutil.move(filepath, original_path)

            photo_entry = {
                "barcode": barcode, "angle": angle,
                "filename": new_filename, "path": original_path,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
            self.session_photos.append(photo_entry)
            self._push_undo(photo_entry)  # Phase 4: multi-level undo

            self.log(f"   ✓ Original: original/{barcode}/{new_filename}", "success")

            # Generate multi-resolution (S/M/L/OG) then remove root file
            base_name = os.path.splitext(new_filename)[0]
            og_path = original_path  # fallback if multi-res fails
            try:
                orig_img = _to_srgb(Image.open(original_path))
                save_multi_resolution(orig_img, original_dir, base_name)
                # Remove root file (keep only S/M/L/OG)
                og_path = os.path.join(original_dir, "OG", f"{base_name}_OG.jpg")
                if os.path.exists(og_path):
                    os.remove(original_path)
                self.log(f"   \u2713 Multi-Res: S/M/L/OG", "dim")
                # Preview: show S thumbnail
                s_path = os.path.join(original_dir, "S", f"{base_name}_S.jpg")
                if os.path.exists(s_path):
                    self._update_preview(s_path)
            except Exception as e:
                self.log(f"   ปรับขนาดหลายระดับผิดพลาด: {e}", "warning")

            total = len(self.session_photos)
            self.photo_count_label.configure(text=f"{total} รูป")
            self.session_badge.configure(text=f"  เซสชัน: {total} รูป  ")
            self._save_session()

            if angle in self.angle_buttons:
                _, _, _, cnt_lbl = self.angle_buttons[angle]
                cnt_lbl.configure(text=f"{count}")

            # Phase 6: O(1) lookup แทน O(n) loop
            label, label_th = self._angle_label_map.get(angle, (angle, angle))
            self.current_state_label.configure(
                text=f"{barcode}  —  {label_th} ({label})  —  {count} รูป",
                fg=C["green"],
            )

            # Enqueue for post-processing (use OG as source)
            needs_processing = (
                self.config.get("enable_cutout", True)
                or self.config.get("enable_wm_original", True)
            )
            if needs_processing:
                self.pipeline_pending += 1
                self.pipeline_badge.configure(
                    text=f"  กำลังประมวลผล {self.pipeline_pending}  ", fg=C["orange"]
                )
                self.processor.enqueue({
                    "original_path": og_path,
                    "barcode": barcode,
                    "filename": new_filename,
                    "output_root": output_root,
                    "config": self.config.copy(),
                })

        except Exception as e:
            self.log(f"   ข้อผิดพลาด: {e}", "error")

    # =========================================================================
    # LOG
    # =========================================================================
    def log(self, message, tag=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        # Trim log when it gets too long (keep last 500 lines to avoid memory growth)
        try:
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 1000:
                self.log_text.delete("1.0", f"{line_count - 500}.0")
        except Exception:
            pass
        line = f"  {timestamp}  {message}\n"
        if tag:
            self.log_text.insert("end", line, tag)
        else:
            self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # =========================================================================
    # SESSION STATE (auto-save / restore)
    # =========================================================================
    def _save_session(self):
        """Auto-save session state to disk for crash recovery."""
        state = {
            "current_barcode": self.current_barcode,
            "current_angle": self.current_angle,
            "angle_counters": self.angle_counters,
            "spin360_counter": self.spin360_counter,
            "session_photos": self.session_photos[-500:],  # cap at 500
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"[session] บันทึก session ไม่สำเร็จ: {e}")

    def _restore_session(self):
        """Restore session state from disk if available."""
        if not os.path.exists(SESSION_FILE):
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)

            photos = state.get("session_photos", [])
            if not photos:
                return

            saved_at = state.get("saved_at", "unknown")
            ok = messagebox.askyesno(
                "กู้คืนเซสชัน",
                f"พบเซสชันก่อนหน้า ({len(photos)} รูป, บันทึกเมื่อ {saved_at})\n\n"
                "ต้องการกู้คืนบาร์โค้ด มุมถ่าย และตัวนับหรือไม่?",
            )
            if not ok:
                return

            self.session_photos = photos
            self.current_barcode = state.get("current_barcode", "")
            self.current_angle = state.get("current_angle", "")
            self.angle_counters = state.get("angle_counters", {})
            self.spin360_counter = state.get("spin360_counter", 0)

            total = len(self.session_photos)
            self.photo_count_label.configure(text=f"{total} รูป")
            self.session_badge.configure(text=f"  เซสชัน: {total} รูป  ")

            if self.current_barcode:
                self.current_state_label.configure(
                    text=f"{self.current_barcode}  --  กู้คืนแล้ว ({total} รูป)",
                    fg=C["green"]
                )

            # Restore angle counter labels
            for aid, cnt in self.angle_counters.items():
                if aid in self.angle_buttons and cnt > 0:
                    _, _, _, cnt_lbl = self.angle_buttons[aid]
                    cnt_lbl.configure(text=f"{cnt}")

            self.log(f"กู้คืนเซสชัน: {total} รูป, บาร์โค้ด={self.current_barcode}", "success")
        except Exception as e:
            logger.warning(f"[session] กู้คืน session ไม่สำเร็จ: {e}")
            self.log("⚠ ข้อมูล session เสียหาย ไม่สามารถกู้คืนได้", "warning")
            try:
                os.remove(SESSION_FILE)
            except OSError:
                pass

    # =========================================================================
    # SETTINGS WINDOW
    # =========================================================================
    def _open_settings(self):
        """Open a Settings dialog window with all configuration options."""
        if hasattr(self, '_settings_win') and self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_set()
            return

        win = tk.Toplevel(self)
        win.title("ตั้งค่า")
        win.geometry("700x720")
        win.configure(bg=C["bg"])
        win.resizable(True, True)
        win.minsize(600, 500)
        self._settings_win = win

        # Scrollable content
        outer = tk.Frame(win, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        cv = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        content = tk.Frame(cv, bg=C["bg"], padx=20, pady=16)
        content_win = cv.create_window((0, 0), window=content, anchor="nw")

        def _on_cfg(e):
            cv.configure(scrollregion=cv.bbox("all"))
            cv.itemconfig(content_win, width=cv.winfo_width())
        content.bind("<Configure>", _on_cfg)
        cv.bind("<Configure>", _on_cfg)
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # ── Title ──
        tk.Label(content, text="ตั้งค่า", font=("Segoe UI Semibold", 16),
                 fg=C["text"], bg=C["bg"]).pack(anchor="w", pady=(0, 16))

        # Helper: section frame
        def section(title):
            f = tk.Frame(content, bg=C["surface"], padx=16, pady=12,
                         highlightbackground=C["border"], highlightthickness=1)
            f.pack(fill="x", pady=(0, 10))
            tk.Label(f, text=title, font=("Segoe UI Semibold", 10),
                     fg=C["accent"], bg=C["surface"]).pack(anchor="w", pady=(0, 8))
            return f

        # Helper: folder row
        def folder_row(parent, label_text, var, browse_cmd):
            row = tk.Frame(parent, bg=C["surface"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label_text, font=("Segoe UI", 10), fg=C["text_muted"],
                     bg=C["surface"], width=16, anchor="w").pack(side="left")
            ent = tk.Entry(row, textvariable=var, font=("Segoe UI", 10),
                           bg=C["surface2"], fg=C["text"], relief="flat",
                           insertbackground=C["text"], highlightthickness=0)
            ent.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 6))
            tk.Button(row, text="...", font=("Segoe UI", 9),
                      bg=C["surface2"], fg=C["text_dim"],
                      activebackground=C["btn_hover"], activeforeground=C["text"],
                      relief="flat", cursor="hand2", padx=8, pady=1,
                      command=browse_cmd).pack(side="right")
            return ent

        # ============================================================
        # SECTION 1: FOLDERS
        # ============================================================
        s1 = section("โฟลเดอร์")

        self._st_watch_var = tk.StringVar(value=self.config.get("watch_folder", ""))
        self._st_output_var = tk.StringVar(value=self.config.get("output_folder", ""))
        self._st_export_var = tk.StringVar(value=self.config.get("export_folder", ""))
        self._st_import_var = tk.StringVar(value=self.config.get("import_folder", ""))

        def _browse_dir(var):
            d = filedialog.askdirectory(parent=win)
            if d:
                var.set(d)

        folder_row(s1, "โฟลเดอร์ต้นทาง", self._st_watch_var,
                   lambda: _browse_dir(self._st_watch_var))
        folder_row(s1, "โฟลเดอร์ปลายทาง", self._st_output_var,
                   lambda: _browse_dir(self._st_output_var))
        folder_row(s1, "โฟลเดอร์ส่งออก", self._st_export_var,
                   lambda: _browse_dir(self._st_export_var))
        folder_row(s1, "โฟลเดอร์นำเข้า", self._st_import_var,
                   lambda: _browse_dir(self._st_import_var))

        # Copy mode toggle
        self._st_copy_mode = tk.BooleanVar(value=self.config.get("copy_mode", False))
        tk.Checkbutton(s1, text="โหมดคัดลอก (เก็บไฟล์เดิมไว้ในโฟลเดอร์ต้นทาง)",
                       variable=self._st_copy_mode, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       ).pack(anchor="w", pady=(6, 0))

        # ============================================================
        # SECTION 2: WATERMARK
        # ============================================================
        s2 = section("ลายน้ำ")

        self._st_wm_path = tk.StringVar(value=self.config.get("watermark_path", ""))
        def _browse_wm():
            p = filedialog.askopenfilename(
                parent=win, title="เลือกไฟล์ลายน้ำ PNG",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if p:
                self._st_wm_path.set(p)

        folder_row(s2, "ไฟล์ลายน้ำ", self._st_wm_path, _browse_wm)

        # Opacity
        opt_row = tk.Frame(s2, bg=C["surface"])
        opt_row.pack(fill="x", pady=(6, 3))
        tk.Label(opt_row, text="ความโปร่งใส", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_opacity = tk.IntVar(value=self.config.get("watermark_opacity", 40))
        tk.Scale(opt_row, from_=10, to=100, orient="horizontal", variable=self._st_opacity,
                 bg=C["surface"], fg=C["text"], troughcolor=C["surface2"],
                 highlightthickness=0, length=200, sliderrelief="flat"
                 ).pack(side="left", padx=(0, 8))
        tk.Label(opt_row, text="%", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"]).pack(side="left")

        # Scale
        scale_row = tk.Frame(s2, bg=C["surface"])
        scale_row.pack(fill="x", pady=3)
        tk.Label(scale_row, text="ขนาด", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_wm_scale = tk.IntVar(value=self.config.get("watermark_scale", 20))
        tk.Scale(scale_row, from_=5, to=50, orient="horizontal", variable=self._st_wm_scale,
                 bg=C["surface"], fg=C["text"], troughcolor=C["surface2"],
                 highlightthickness=0, length=200, sliderrelief="flat"
                 ).pack(side="left", padx=(0, 8))
        tk.Label(scale_row, text="% ของความกว้างรูป", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"]).pack(side="left")

        # Position
        pos_row = tk.Frame(s2, bg=C["surface"])
        pos_row.pack(fill="x", pady=3)
        tk.Label(pos_row, text="ตำแหน่ง", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_position = tk.StringVar(value=self.config.get("watermark_position", "bottom-right"))
        ttk.Combobox(pos_row, textvariable=self._st_position, width=18,
                     values=["bottom-right", "bottom-left", "top-right", "top-left", "center"],
                     state="readonly").pack(side="left")

        # Margin
        margin_row = tk.Frame(s2, bg=C["surface"])
        margin_row.pack(fill="x", pady=3)
        tk.Label(margin_row, text="ขอบ (พิกเซล)", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_margin = tk.IntVar(value=self.config.get("watermark_margin", 30))
        tk.Scale(margin_row, from_=0, to=100, orient="horizontal", variable=self._st_margin,
                 bg=C["surface"], fg=C["text"], troughcolor=C["surface2"],
                 highlightthickness=0, length=200, sliderrelief="flat"
                 ).pack(side="left")

        # ============================================================
        # SECTION 3: PIPELINE
        # ============================================================
        s3 = section("ขั้นตอนประมวลผล")

        self._st_cutout = tk.BooleanVar(value=self.config.get("enable_cutout", True))
        self._st_wm = tk.BooleanVar(value=self.config.get("enable_watermark", True))
        self._st_wm_orig = tk.BooleanVar(value=self.config.get("enable_wm_original", True))

        tk.Checkbutton(s3, text="ลบพื้นหลัง (cutout/)",
                       variable=self._st_cutout, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       ).pack(anchor="w", pady=2)
        tk.Checkbutton(s3, text="ลายน้ำบนภาพลบพื้นหลัง (watermarked/)",
                       variable=self._st_wm, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       ).pack(anchor="w", pady=2)
        tk.Checkbutton(s3, text="ลายน้ำบนภาพต้นฉบับ (watermarked_original/)",
                       variable=self._st_wm_orig, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       ).pack(anchor="w", pady=2)

        # BG Color
        bg_row = tk.Frame(s3, bg=C["surface"])
        bg_row.pack(fill="x", pady=(6, 0))
        tk.Label(bg_row, text="สีพื้นหลัง", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"], width=20, anchor="w").pack(side="left")
        bg_c = self.config.get("bg_color", [255, 255, 255])
        self._st_bg_r = tk.IntVar(value=bg_c[0])
        self._st_bg_g = tk.IntVar(value=bg_c[1])
        self._st_bg_b = tk.IntVar(value=bg_c[2])
        for lbl, var in [("R:", self._st_bg_r), ("G:", self._st_bg_g), ("B:", self._st_bg_b)]:
            tk.Label(bg_row, text=lbl, font=("Segoe UI", 9), fg=C["text_muted"],
                     bg=C["surface"]).pack(side="left", padx=(4, 0))
            tk.Entry(bg_row, textvariable=var, width=4, font=("Consolas", 10),
                     bg=C["surface2"], fg=C["text"], relief="flat",
                     insertbackground=C["text"], highlightthickness=0
                     ).pack(side="left", padx=(0, 4))

        # ============================================================
        # SECTION 4: 360 SPIN
        # ============================================================
        s4 = section("หมุน 360°")

        shots_row = tk.Frame(s4, bg=C["surface"])
        shots_row.pack(fill="x", pady=3)
        tk.Label(shots_row, text="จำนวนช็อตเริ่มต้น", font=("Segoe UI", 10),
                 fg=C["text_muted"], bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_spin_total = tk.IntVar(value=self.config.get("spin360_total", 24))
        ttk.Combobox(shots_row, textvariable=self._st_spin_total, width=6,
                     values=[12, 24, 36, 72], state="readonly").pack(side="left")

        self._st_v360_bg = tk.BooleanVar(value=self.config.get("video360_remove_bg", False))
        tk.Checkbutton(s4, text="วิดีโอ 360°: ลบพื้นหลังอัตโนมัติ",
                       variable=self._st_v360_bg, font=("Segoe UI", 10),
                       fg=C["text"], bg=C["surface"], selectcolor=C["surface2"],
                       activebackground=C["surface"], activeforeground=C["text"],
                       ).pack(anchor="w", pady=2)

        # ============================================================
        # SECTION 5: FILE EXTENSIONS
        # ============================================================
        s5 = section("นามสกุลไฟล์ที่รองรับ")

        ext_row = tk.Frame(s5, bg=C["surface"])
        ext_row.pack(fill="x")
        tk.Label(ext_row, text="นามสกุลไฟล์", font=("Segoe UI", 10), fg=C["text_muted"],
                 bg=C["surface"], width=16, anchor="w").pack(side="left")
        self._st_extensions = tk.StringVar(
            value=", ".join(self.config.get("image_extensions", []))
        )
        tk.Entry(ext_row, textvariable=self._st_extensions, font=("Consolas", 10),
                 bg=C["surface2"], fg=C["text"], relief="flat",
                 insertbackground=C["text"], highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, ipady=3)

        # ============================================================
        # BUTTONS: SAVE / CANCEL
        # ============================================================
        btn_frame = tk.Frame(content, bg=C["bg"])
        btn_frame.pack(fill="x", pady=(16, 0))

        tk.Button(btn_frame, text="บันทึก", font=("Segoe UI Semibold", 12),
                  fg="#fff", bg=C["green"], activebackground="#38c172",
                  relief="flat", cursor="hand2", padx=30, pady=8,
                  command=lambda: self._save_settings(win)
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="ยกเลิก", font=("Segoe UI Semibold", 12),
                  fg=C["text"], bg=C["surface2"], activebackground=C["btn_hover"],
                  relief="flat", cursor="hand2", padx=30, pady=8,
                  command=win.destroy
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="รีเซ็ตค่าเริ่มต้น", font=("Segoe UI", 10),
                  fg=C["red"], bg=C["surface2"], activebackground=C["btn_hover"],
                  relief="flat", cursor="hand2", padx=16, pady=6,
                  command=lambda: self._reset_defaults(win)
                  ).pack(side="right")

    def _save_settings(self, win):
        """Save all settings from the Settings window to config."""
        # Folders
        self.config["watch_folder"] = self._st_watch_var.get()
        self.config["output_folder"] = self._st_output_var.get()
        self.config["export_folder"] = self._st_export_var.get()
        self.config["import_folder"] = self._st_import_var.get()
        self.config["copy_mode"] = self._st_copy_mode.get()

        # Watermark
        self.config["watermark_path"] = self._st_wm_path.get()
        self.config["watermark_opacity"] = self._st_opacity.get()
        self.config["watermark_scale"] = self._st_wm_scale.get()
        self.config["watermark_position"] = self._st_position.get()
        self.config["watermark_margin"] = self._st_margin.get()

        # Pipeline
        self.config["enable_cutout"] = self._st_cutout.get()
        self.config["enable_watermark"] = self._st_wm.get()
        self.config["enable_wm_original"] = self._st_wm_orig.get()

        # BG Color
        try:
            self.config["bg_color"] = [
                max(0, min(255, self._st_bg_r.get())),
                max(0, min(255, self._st_bg_g.get())),
                max(0, min(255, self._st_bg_b.get())),
            ]
        except (tk.TclError, ValueError) as e:
            messagebox.showerror("ข้อผิดพลาด", f"ค่าสีพื้นหลังไม่ถูกต้อง: {e}\nต้องเป็นตัวเลข 0-255", parent=win)
            return

        # 360
        self.config["spin360_total"] = self._st_spin_total.get()
        self.config["video360_remove_bg"] = self._st_v360_bg.get()

        # Extensions
        ext_str = self._st_extensions.get()
        exts = [e.strip() for e in ext_str.replace(";", ",").split(",") if e.strip()]
        if exts:
            self.config["image_extensions"] = exts

        with self._config_lock:
            save_config(self.config)

        # Sync main UI variables
        self.watch_folder_var.set(self.config["watch_folder"])
        self.output_folder_var.set(self.config["output_folder"])
        self.wm_path_var.set(self.config["watermark_path"])
        self.opacity_var.set(self.config["watermark_opacity"])
        self.wm_scale_var.set(self.config["watermark_scale"])
        self.position_var.set(self.config["watermark_position"])
        self.cutout_var.set(self.config["enable_cutout"])
        self.wm_var.set(self.config["enable_watermark"])
        self.wm_orig_var.set(self.config["enable_wm_original"])
        self.spin_total_var.set(self.config["spin360_total"])
        self.video360_bg_var.set(self.config["video360_remove_bg"])

        self.log("บันทึกการตั้งค่าแล้ว", "success")
        win.destroy()

    def _reset_defaults(self, win):
        """Reset all settings to defaults."""
        ok = messagebox.askyesno("รีเซ็ต", "ต้องการรีเซ็ตการตั้งค่าทั้งหมดหรือไม่?", parent=win)
        if not ok:
            return
        self.config = DEFAULT_CONFIG.copy()
        save_config(self.config)
        self.log("รีเซ็ตการตั้งค่าแล้ว", "warning")
        win.destroy()
        self._open_settings()

    # =========================================================================
    # EXPORT REPORT — Phase 4: HTML + CSV dual output
    # =========================================================================
    def export_report(self):
        """สร้างรายงาน HTML + CSV สรุปรูปแต่ละบาร์โค้ด."""
        output_root = self.config.get("output_folder", "")
        if not output_root:
            messagebox.showwarning("คำเตือน", "ยังไม่ได้ตั้งค่าโฟลเดอร์ปลายทาง")
            return

        original_dir = os.path.join(output_root, "original")
        if not os.path.isdir(original_dir):
            messagebox.showwarning("คำเตือน", "ไม่พบรูปภาพในโฟลเดอร์ปลายทาง")
            return

        # Scan output directory once (Phase 6: single-pass)
        report_rows: list[dict] = []
        for barcode_dir in sorted(os.listdir(original_dir)):
            og_dir = os.path.join(original_dir, barcode_dir, "OG")
            if not os.path.isdir(og_dir):
                continue
            files = [f for f in os.listdir(og_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            angles: dict[str, int] = {}
            total_360 = 0
            for f in files:
                if "_360_" in f:
                    total_360 += 1
                else:
                    parts = f.rsplit("_", 2)
                    if len(parts) >= 3:
                        angle = parts[-2]
                        angles[angle] = angles.get(angle, 0) + 1

            product = self.product_db.lookup(barcode_dir)
            name = product["name"] if product else ""
            category = product["category"] if product else ""

            report_rows.append({
                "barcode": barcode_dir,
                "name": name,
                "category": category,
                "total_photos": len(files),
                "total_360": total_360,
                "angles": angles,
            })

        if not report_rows:
            messagebox.showinfo("ส่งออก", "ไม่พบรูปภาพสำหรับรายงาน")
            return

        export_dir = self.config.get("export_folder", "")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # — ถามผู้ใช้ว่าบันทึกที่ไหน (HTML)
        report_path = filedialog.asksaveasfilename(
            title="บันทึกรายงาน HTML",
            defaultextension=".html",
            filetypes=[("HTML report", "*.html"), ("CSV", "*.csv")],
            initialdir=export_dir if export_dir and os.path.isdir(export_dir) else None,
            initialfile=f"photo_report_{ts}.html",
        )
        if not report_path:
            return

        total_barcodes = len(report_rows)
        total_photos = sum(r["total_photos"] for r in report_rows)
        total_360 = sum(r["total_360"] for r in report_rows)

        # — สร้าง HTML report สไตล์ Metronic dark theme
        if report_path.endswith(".html"):
            self._write_html_report(report_path, report_rows, ts)
        else:
            # CSV fallback
            with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["barcode", "name", "category", "total_photos", "total_360", "angles"]
                )
                writer.writeheader()
                for row in report_rows:
                    row2 = dict(row)
                    row2["angles"] = ", ".join(f"{a}:{c}" for a, c in sorted(row["angles"].items()))
                    writer.writerow(row2)

        self.log(
            f"ส่งออกรายงาน: {total_barcodes} บาร์โค้ด, {total_photos} รูป → {os.path.basename(report_path)}",
            "success",
        )
        messagebox.showinfo(
            "ส่งออกสำเร็จ",
            f"บันทึกรายงานแล้ว!\n\n"
            f"บาร์โค้ด: {total_barcodes}\n"
            f"รูปทั้งหมด: {total_photos}\n"
            f"360°: {total_360} เฟรม",
        )

    def _write_html_report(self, path: str, rows: list, timestamp: str) -> None:
        """เขียน HTML report สวยงาม สไตล์ dark theme (Metronic-inspired)."""
        total_photos = sum(r["total_photos"] for r in rows)
        total_360 = sum(r["total_360"] for r in rows)
        n_sku = len(rows)
        generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        rows_html = ""
        for i, row in enumerate(rows, 1):
            angle_badges = "".join(
                f'<span class="badge">{a}<span class="cnt">{c}</span></span>'
                for a, c in sorted(row["angles"].items())
            )
            rows_html += f"""
            <tr>
                <td class="num">{i}</td>
                <td class="bc">{html_mod.escape(row["barcode"])}</td>
                <td>{html_mod.escape(row["name"])}</td>
                <td>{html_mod.escape(row["category"])}</td>
                <td class="num">{row["total_photos"]}</td>
                <td class="num">{row["total_360"] or "—"}</td>
                <td class="angles">{angle_badges}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>รายงานภาพสินค้า — {timestamp}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:#0f1117;color:#e2e4ed;padding:32px}}
h1{{font-size:22px;font-weight:600;color:#6c8cff;margin-bottom:4px}}
.sub{{color:#6b7394;font-size:13px;margin-bottom:24px}}
.stats{{display:flex;gap:16px;margin-bottom:28px;flex-wrap:wrap}}
.card{{background:#1a1d27;border:1px solid #2e3348;border-radius:8px;padding:16px 24px;min-width:140px}}
.card .val{{font-size:28px;font-weight:700;color:#6c8cff}}
.card .lbl{{font-size:12px;color:#6b7394;margin-top:4px}}
table{{width:100%;border-collapse:collapse;background:#1a1d27;border-radius:8px;overflow:hidden}}
th{{background:#232734;color:#6b7394;font-size:11px;font-weight:600;text-transform:uppercase;padding:10px 14px;text-align:left;border-bottom:1px solid #2e3348}}
td{{padding:10px 14px;border-bottom:1px solid #1e2130;font-size:13px;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#1e2230}}
.num{{text-align:right;color:#6b7394}}
.bc{{font-family:Consolas,monospace;color:#6c8cff;font-weight:600}}
.badge{{display:inline-flex;align-items:center;background:#2a2f42;border-radius:4px;padding:2px 7px;margin:2px;font-size:11px;color:#e2e4ed}}
.badge .cnt{{background:#6c8cff;color:#fff;border-radius:3px;padding:0 5px;margin-left:6px;font-weight:700}}
.footer{{margin-top:24px;color:#4a5170;font-size:11px;text-align:right}}
@media print{{body{{background:#fff;color:#000}}table,th,td{{border-color:#ccc}}}}
</style>
</head>
<body>
<h1>📸 รายงานภาพสินค้า</h1>
<p class="sub">สร้างเมื่อ {generated_at}</p>
<div class="stats">
  <div class="card"><div class="val">{n_sku}</div><div class="lbl">บาร์โค้ด</div></div>
  <div class="card"><div class="val">{total_photos}</div><div class="lbl">รูปทั้งหมด</div></div>
  <div class="card"><div class="val">{total_360}</div><div class="lbl">เฟรม 360°</div></div>
</div>
<table>
<thead><tr>
  <th>#</th><th>บาร์โค้ด</th><th>ชื่อสินค้า</th><th>หมวดหมู่</th>
  <th>รูปทั้งหมด</th><th>360°</th><th>มุมถ่าย</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<div class="footer">ProductPhotoManager — {generated_at}</div>
</body>
</html>"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    # =========================================================================
    # IMPORT PHOTOS
    # =========================================================================
    def import_photos(self):
        """Import photos from import_folder (or file dialog) into the output structure."""
        import_dir = self.config.get("import_folder", "")
        if not import_dir or not os.path.isdir(import_dir):
            import_dir = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่ต้องการนำเข้ารูปภาพ")
        if not import_dir or not os.path.isdir(import_dir):
            return

        output_root = self.config.get("output_folder", "")
        if not output_root:
            messagebox.showerror("ข้อผิดพลาด", "กรุณาตั้งค่าโฟลเดอร์ปลายทางก่อน!")
            return

        exts = set(self.config.get("image_extensions", [".jpg", ".jpeg", ".png"]))
        imported = 0
        skipped = 0
        error_count = 0

        for f in sorted(os.listdir(import_dir)):
            ext = os.path.splitext(f)[1].lower()
            if ext not in exts:
                continue

            # Try to parse filename: {barcode}_{angle}_{count}.ext
            parts = os.path.splitext(f)[0].rsplit("_", 2)
            if len(parts) >= 2:
                barcode = _sanitize_barcode(parts[0])
            else:
                barcode = _sanitize_barcode(os.path.splitext(f)[0])

            src = os.path.join(import_dir, f)
            dst_dir = os.path.join(output_root, "original", barcode)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, f)

            if os.path.exists(dst):
                skipped += 1
                continue

            shutil.copy2(src, dst)

            # Generate multi-res
            try:
                img = _to_srgb(Image.open(dst))
                base_name = os.path.splitext(f)[0]
                save_multi_resolution(img, dst_dir, base_name)
                og_path = os.path.join(dst_dir, "OG", f"{base_name}_OG.jpg")
                if os.path.exists(og_path):
                    os.remove(dst)
            except Exception as e:
                logger.warning(f"[import] ปรับขนาด {f} ไม่สำเร็จ: {e}")
                error_count += 1

            imported += 1

        msg = f"นำเข้า: {imported} รูป, ข้าม {skipped} รูป (มีอยู่แล้ว)"
        if error_count:
            msg += f", ผิดพลาด {error_count} รูป (ดู log)"
        self.log(msg, "success")
        messagebox.showinfo("นำเข้า", f"นำเข้า {imported} รูป\nข้าม {skipped} รูป (ซ้ำ)" +
                            (f"\nผิดพลาด {error_count} รูป" if error_count else ""))

    # =========================================================================
    # UNDO (TRASH) — Phase 4: multi-level undo stack (สูงสุด 20 รายการ)
    # =========================================================================
    def _push_undo(self, photo_entry: dict) -> None:
        """เพิ่มรายการเข้า undo stack และอัปเดตปุ่ม."""
        self._undo_stack.append(photo_entry)
        self._update_undo_btn()

    def _update_undo_btn(self) -> None:
        """อัปเดต label ปุ่มเลิกทำให้แสดงจำนวน undo ที่เหลือ."""
        n = len(self._undo_stack)
        if n == 0:
            self.undo_btn.configure(text="เลิกทำ", fg=C["text_dim"])
        else:
            self.undo_btn.configure(text=f"เลิกทำ ({n})", fg=C["red"])

    def undo_last_photo(self):
        """ย้ายรูปล่าสุดไป _trash/ (เลิกทำได้หลายระดับ)."""
        # ลองดึงจาก undo stack ก่อน ถ้าไม่มีใช้ session_photos
        if self._undo_stack:
            last = self._undo_stack.pop()
            # sync session_photos ด้วย
            self.session_photos = [p for p in self.session_photos
                                   if p.get("filename") != last.get("filename")]
        elif self.session_photos:
            last = self.session_photos.pop()
        else:
            self.log("   ไม่มีอะไรให้เลิกทำ", "warning")
            return

        barcode = last["barcode"]
        base_name = os.path.splitext(last["filename"])[0]
        output_root = self.config.get("output_folder", "")
        if not output_root:
            self._update_undo_btn()
            return

        trash_dir = os.path.join(output_root, "_trash", barcode)
        os.makedirs(trash_dir, exist_ok=True)

        moved = 0
        for sub in ["original", "cutout", "watermarked", "watermarked_original", "360"]:
            sub_dir = os.path.join(output_root, sub, barcode)
            if not os.path.isdir(sub_dir):
                continue
            for sz in ["S", "M", "L", "OG", ""]:
                check_dir = os.path.join(sub_dir, sz) if sz else sub_dir
                if not os.path.isdir(check_dir):
                    continue
                for f in os.listdir(check_dir):
                    if f.startswith(base_name):
                        src = os.path.join(check_dir, f)
                        dst_sub = os.path.join(trash_dir, sub, sz) if sz else os.path.join(trash_dir, sub)
                        os.makedirs(dst_sub, exist_ok=True)
                        try:
                            shutil.move(src, os.path.join(dst_sub, f))
                            moved += 1
                        except OSError as e:
                            logger.warning(f"[undo] ย้ายไฟล์ไม่สำเร็จ {f}: {e}")

        # Update counters
        angle = last.get("angle", "")
        if angle and angle != "360" and angle in self.angle_counters:
            self.angle_counters[angle] = max(0, self.angle_counters[angle] - 1)
            if angle in self.angle_buttons:
                cnt = self.angle_counters[angle]
                _, _, _, cnt_lbl = self.angle_buttons[angle]
                cnt_lbl.configure(text=f"{cnt}" if cnt > 0 else "")
        elif angle == "360":
            self.spin360_counter = max(0, self.spin360_counter - 1)

        total = len(self.session_photos)
        self.photo_count_label.configure(text=f"{total} รูป")
        self.session_badge.configure(text=f"  เซสชัน: {total} รูป  ")
        self._update_undo_btn()
        self._save_session()

        remaining = len(self._undo_stack)
        self.log(
            f"   เลิกทำ: {last['filename']} -> _trash/ (ย้าย {moved} ไฟล์)"
            + (f", เหลือ {remaining} รายการ" if remaining else ""),
            "warning",
        )

    # =========================================================================
    # STARTUP CHECKS (Phase 3)
    # =========================================================================
    def _startup_checks(self):
        """ตรวจสอบ config ตอนเปิดแอป — watermark path, disk space."""
        # 1. ตรวจสอบ watermark path
        wm_path = self.config.get("watermark_path", "")
        if wm_path and not os.path.exists(wm_path):
            self.log(f"⚠ ไฟล์ลายน้ำไม่พบ: {wm_path}", "warning")
            messagebox.showwarning(
                "ไฟล์ลายน้ำหายไป",
                f"ไม่พบไฟล์ลายน้ำ:\n{wm_path}\n\n"
                "กรุณาตั้งค่าใหม่ใน ตั้งค่า > ลายน้ำ",
            )

        # 2. ตรวจสอบพื้นที่ดิสก์ output folder
        output_root = self.config.get("output_folder", "")
        if output_root:
            self._check_disk_space(output_root, warn_only=True)

    def _check_disk_space(self, path: str, warn_only: bool = False) -> bool:
        """ตรวจสอบพื้นที่ดิสก์ คืน True ถ้าพื้นที่เพียงพอ (>500 MB)."""
        try:
            stat = shutil.disk_usage(path)
            free_mb = stat.free / (1024 * 1024)
            free_gb = free_mb / 1024

            if free_mb < 500:
                msg = f"พื้นที่ดิสก์เหลือน้อย: {free_mb:.0f} MB"
                self.log(f"⚠ {msg}", "error")
                if not warn_only:
                    messagebox.showerror("พื้นที่ดิสก์ไม่เพียงพอ", msg + "\n\nกรุณาเพิ่มพื้นที่ก่อนดำเนินการต่อ")
                return False
            elif free_gb < 2:
                self.log(f"⚠ พื้นที่ดิสก์เหลือ {free_gb:.1f} GB — เหลือน้อย", "warning")
            return True
        except OSError:
            return True  # ไม่สามารถตรวจสอบได้ ถือว่าผ่าน

    # =========================================================================
    # CLOSE
    # =========================================================================
    def on_close(self):
        self._save_session()
        self.stop_watching()
        self.processor.stop()
        if self.observer:
            self.observer.join(timeout=5)  # Phase 3: timeout ป้องกัน hang
        self.destroy()


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    app = ProductPhotoApp()
    app.mainloop()
