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
    # Validate
    errors = validate_config(body.config)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    result = await db.execute(select(AppSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AppSettings(config=body.config, updated_by=user.id)
        db.add(settings)
    else:
        settings.config = body.config
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
