"""
Gallery router — browse/filter/search all photos + activity log.
"""
import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Photo, Product, ActivityLog, User
from backend.api.services.storage import get_storage

router = APIRouter()


@router.get("")
async def gallery(
    search: str = Query(""),
    category: str = Query(""),
    angle: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Browse all photos with filters."""
    query = select(Photo).where(Photo.is_deleted == False)

    if search:
        query = query.join(Product, Photo.product_id == Product.id, isouter=True).where(
            Photo.barcode.ilike(f"%{search}%")
            | Product.name.ilike(f"%{search}%")
            | Product.category.ilike(f"%{search}%")
        )
    if angle:
        query = query.where(Photo.angle == angle)
    if category:
        query = query.join(Product).where(Product.category == category)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

    query = query.order_by(Photo.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    photos = result.scalars().all()

    storage = get_storage()
    data = []
    for p in photos:
        base = os.path.splitext(p.filename)[0]
        data.append({
            "id": p.id,
            "barcode": p.barcode,
            "angle": p.angle,
            "filename": p.filename,
            "status": p.status,
            "has_cutout": p.has_cutout,
            "has_watermark": p.has_watermark,
            "width": p.width,
            "height": p.height,
            "thumbnail_url": storage.get_url(f"original/{p.barcode}/S/{base}_S.jpg"),
            "preview_url": storage.get_url(f"original/{p.barcode}/M/{base}_M.jpg"),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"data": data, "total": total, "page": page, "limit": limit}


@router.get("/activity")
async def activity_log(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get recent activity log entries."""
    result = await db.execute(
        select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()

    return [{
        "id": log.id,
        "photo_id": log.photo_id,
        "action": log.action,
        "message": log.message,
        "status": log.status,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in logs]
