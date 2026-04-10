"""
Image processing pipeline — runs in background thread.
Reuses core/image_processor.py watermark logic + utils/color_profile.py.
"""
import asyncio
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageEnhance

from utils.color_profile import to_srgb, save_multi_resolution, _SRGB_ICC
from backend.api.services.storage import get_storage

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeline")

# Optional rembg
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


def _add_watermark(base_img: Image.Image, wm_path: str, config: dict) -> Image.Image:
    """Overlay watermark PNG on base image. Reuses logic from core/image_processor.py."""
    wm = Image.open(wm_path).convert("RGBA")

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

    positions = {
        "center": ((base_w - wm_target_w) // 2, (base_h - wm_target_h) // 2),
        "bottom-left": (margin, base_h - wm_target_h - margin),
        "top-right": (base_w - wm_target_w - margin, margin),
        "top-left": (margin, margin),
        "bottom-right": (base_w - wm_target_w - margin, base_h - wm_target_h - margin),
    }
    x, y = positions.get(position, positions["bottom-right"])

    result = base_img.copy()
    result.paste(wm, (x, y), wm)
    return result


def _process_photo_sync(photo_id: int, barcode: str, filename: str, config: dict):
    """Synchronous pipeline: cutout + watermark. Runs in thread pool."""
    storage = get_storage()
    base_name = os.path.splitext(filename)[0]
    original_key = f"original/{barcode}/OG/{base_name}_OG.jpg"

    if not storage.exists(original_key):
        logger.error(f"[pipeline] original not found: {original_key}")
        return {"status": "error", "error": "original not found"}

    results = {"photo_id": photo_id, "has_cutout": False, "has_watermark": False, "has_wm_original": False}

    # Load original
    original_path = storage.get_path(original_key)
    orig_img = to_srgb(Image.open(original_path)).convert("RGBA")
    bg_color = tuple(config.get("bg_color", [255, 255, 255]))

    # Watermark file
    wm_key = config.get("_watermark_key", "")
    wm_path = storage.get_path(wm_key) if wm_key and storage.exists(wm_key) else None

    # ── Step 1: Watermark on Original ──
    if config.get("enable_wm_original", True) and wm_path:
        try:
            wm_img = _add_watermark(orig_img, wm_path, config)
            final = Image.new("RGB", wm_img.size, bg_color)
            final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
            final.info["icc_profile"] = _SRGB_ICC

            with tempfile.TemporaryDirectory() as tmpdir:
                save_multi_resolution(final, tmpdir, base_name)
                for size in ["S", "M", "L", "OG"]:
                    for f in os.listdir(os.path.join(tmpdir, size)):
                        storage.upload_file(
                            os.path.join(tmpdir, size, f),
                            f"watermarked_original/{barcode}/{size}/{f}"
                        )
            results["has_wm_original"] = True
            logger.info(f"[pipeline] {filename}: watermark_original done")
        except Exception as e:
            logger.error(f"[pipeline] {filename}: watermark_original failed: {e}")

    # ── Step 2: Background Removal ──
    cutout_img = None
    if config.get("enable_cutout", True) and HAS_REMBG:
        try:
            cutout_img = rembg_remove(orig_img)
            with tempfile.TemporaryDirectory() as tmpdir:
                save_multi_resolution(cutout_img, tmpdir, base_name, ext=".png", is_png=True)
                for size in ["S", "M", "L", "OG"]:
                    for f in os.listdir(os.path.join(tmpdir, size)):
                        storage.upload_file(
                            os.path.join(tmpdir, size, f),
                            f"cutout/{barcode}/{size}/{f}"
                        )
            results["has_cutout"] = True
            logger.info(f"[pipeline] {filename}: cutout done")
        except Exception as e:
            logger.error(f"[pipeline] {filename}: cutout failed: {e}")

    # ── Step 3: Watermark on Cutout ──
    if config.get("enable_watermark", True) and cutout_img and wm_path:
        try:
            wm_img = _add_watermark(cutout_img, wm_path, config)
            final = Image.new("RGB", wm_img.size, bg_color)
            final.paste(wm_img, mask=wm_img.split()[3] if wm_img.mode == "RGBA" else None)
            final.info["icc_profile"] = _SRGB_ICC

            with tempfile.TemporaryDirectory() as tmpdir:
                save_multi_resolution(final, tmpdir, base_name)
                for size in ["S", "M", "L", "OG"]:
                    for f in os.listdir(os.path.join(tmpdir, size)):
                        storage.upload_file(
                            os.path.join(tmpdir, size, f),
                            f"watermarked/{barcode}/{size}/{f}"
                        )
            results["has_watermark"] = True
            logger.info(f"[pipeline] {filename}: watermark done")
        except Exception as e:
            logger.error(f"[pipeline] {filename}: watermark failed: {e}")

    results["status"] = "done"
    return results


# Singleton sync engine (created once, reused across pipeline threads)
_sync_engine = None


def _get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        from sqlalchemy import create_engine
        from backend.api.config import settings as app_settings
        sync_url = app_settings.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
        _sync_engine = create_engine(sync_url, pool_size=2, max_overflow=0)
    return _sync_engine


async def enqueue_processing(photo_id: int, barcode: str, filename: str, config: dict):
    """Enqueue photo for background processing. Returns immediately."""
    loop = asyncio.get_running_loop()

    # Broadcast: processing started
    from backend.api.websocket import ws_manager
    await ws_manager.broadcast({
        "type": "processing_start", "photo_id": photo_id,
        "barcode": barcode, "filename": filename,
    })

    def _run_and_update():
        results = _process_photo_sync(photo_id, barcode, filename, config)
        _update_photo_status(photo_id, results)
        # Schedule WebSocket broadcast from event loop
        try:
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast({
                    "type": "processing_done" if results.get("status") == "done" else "processing_error",
                    "photo_id": photo_id, "barcode": barcode,
                    "status": results.get("status", "error"),
                    "has_cutout": results.get("has_cutout", False),
                    "has_watermark": results.get("has_watermark", False),
                }),
                loop,
            )
        except Exception as e:
            logger.warning(f"[pipeline] WS broadcast failed: {e}")

    loop.run_in_executor(_executor, _run_and_update)


def _update_photo_status(photo_id: int, results: dict):
    """Update photo record after pipeline completes (sync, called from thread)."""
    from sqlalchemy import update
    from sqlalchemy.orm import Session as SyncSession
    from backend.api.models.db import Photo

    engine = _get_sync_engine()
    try:
        with SyncSession(engine) as session:
            session.execute(
                update(Photo).where(Photo.id == photo_id).values(
                    status=results.get("status", "error"),
                    has_cutout=results.get("has_cutout", False),
                    has_watermark=results.get("has_watermark", False),
                    has_wm_original=results.get("has_wm_original", False),
                )
            )
            session.commit()
        logger.info(f"[pipeline] photo {photo_id}: DB updated → {results.get('status')}")
    except Exception as e:
        logger.error(f"[pipeline] photo {photo_id}: DB update failed: {e}")
