"""
Settings router — app configuration CRUD + watermark upload.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import AppSettings, User
from backend.api.services.storage import get_storage
from core.config import DEFAULT_CONFIG, validate_config

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_config_dict(db: AsyncSession) -> dict:
    """Get merged config dict (DB settings + watermark key)."""
    result = await db.execute(select(AppSettings))
    settings_row = result.scalar_one_or_none()
    if not settings_row:
        return {**DEFAULT_CONFIG}
    config = {**DEFAULT_CONFIG, **settings_row.config}
    if settings_row.watermark_key:
        config["_watermark_key"] = settings_row.watermark_key
    return config


class SettingsUpdate(BaseModel):
    config: dict


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(AppSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return {"config": DEFAULT_CONFIG, "watermark_url": None}

    storage = get_storage()
    wm_url = storage.get_url(settings.watermark_key) if settings.watermark_key else None
    return {"config": settings.config, "watermark_url": wm_url}


@router.put("")
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Merge with defaults then validate
    merged = {**DEFAULT_CONFIG, **body.config}
    errors = validate_config(merged)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    result = await db.execute(select(AppSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AppSettings(config=merged, updated_by=user.id)
        db.add(settings)
    else:
        settings.config = merged
        settings.updated_by = user.id

    await db.commit()
    return {"message": "บันทึกการตั้งค่าแล้ว", "config": settings.config}


@router.post("/watermark")
async def upload_watermark(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="ไฟล์ลายน้ำต้องเป็น PNG")

    content = await file.read()

    # Validate PNG magic bytes
    PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
    if not content.startswith(PNG_MAGIC):
        raise HTTPException(status_code=400, detail="ไฟล์ไม่ใช่ PNG จริง")
    if len(content) > 10 * 1024 * 1024:  # 10 MB max
        raise HTTPException(status_code=400, detail="ไฟล์ลายน้ำใหญ่เกิน 10 MB")
    storage = get_storage()
    key = f"_watermarks/watermark_{int(datetime.now().timestamp())}.png"
    storage.upload(content, key)

    result = await db.execute(select(AppSettings))
    settings = result.scalar_one_or_none()
    if settings:
        settings.watermark_key = key
        settings.updated_by = user.id
    else:
        settings = AppSettings(config=DEFAULT_CONFIG, watermark_key=key, updated_by=user.id)
        db.add(settings)

    await db.commit()
    return {"message": "อัปโหลดลายน้ำแล้ว", "watermark_url": storage.get_url(key)}


# ── Watch Folder ────────────────────────────────────

from backend.api.services.watch_folder import start_watch_folder, stop_watch_folder, is_watching


@router.post("/watch-folder/start")
async def start_watching(
    body: dict,
    _user: User = Depends(get_current_user),
):
    folder_path = body.get("folder_path", "")
    if not folder_path:
        raise HTTPException(status_code=400, detail="กรุณาระบุ folder_path")

    def upload_callback(file_path: str, barcode: str, angle: str):
        logger.info(f"Watch folder auto-upload: {file_path} → {barcode}/{angle}")
        # Note: actual upload happens via pipeline — this logs the intent
        # In production, integrate with the photo upload pipeline here

    success = start_watch_folder(folder_path, upload_callback)
    if success:
        return {"message": f"เริ่มติดตามโฟลเดอร์: {folder_path}", "watching": True}
    raise HTTPException(status_code=500, detail="ไม่สามารถเริ่มติดตามได้")


@router.post("/watch-folder/stop")
async def stop_watching(
    _user: User = Depends(get_current_user),
):
    stop_watch_folder()
    return {"message": "หยุดติดตามโฟลเดอร์แล้ว", "watching": False}


@router.get("/watch-folder/status")
async def watch_status(
    _user: User = Depends(get_current_user),
):
    return {"watching": is_watching()}
