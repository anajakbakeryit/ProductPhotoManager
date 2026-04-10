"""
Stats router — dashboard data: totals, daily uploads, pending.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, Photo, Session, User

router = APIRouter()


@router.get("")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Dashboard summary stats."""
    total_products = (await db.execute(select(func.count()).select_from(Product))).scalar() or 0
    total_photos = (await db.execute(
        select(func.count()).where(Photo.is_deleted == False)
    )).scalar() or 0

    today = datetime.now(tz=timezone.utc).date()
    photos_today = (await db.execute(
        select(func.count()).where(
            Photo.is_deleted == False,
            cast(Photo.created_at, Date) == today,
        )
    )).scalar() or 0

    pending = (await db.execute(
        select(func.count()).where(Photo.status.in_(["uploaded", "processing"]))
    )).scalar() or 0

    active_sessions = (await db.execute(
        select(func.count()).where(Session.is_active == True)
    )).scalar() or 0

    return {
        "total_products": total_products,
        "total_photos": total_photos,
        "photos_today": photos_today,
        "pending_processing": pending,
        "active_sessions": active_sessions,
    }


@router.get("/daily")
async def get_daily_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Daily upload counts for chart."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            cast(Photo.created_at, Date).label("date"),
            func.count(Photo.id).label("count"),
        )
        .where(Photo.is_deleted == False, Photo.created_at >= since)
        .group_by(cast(Photo.created_at, Date))
        .order_by(cast(Photo.created_at, Date))
    )
    rows = result.all()
    return [{"date": str(r.date), "count": r.count} for r in rows]
