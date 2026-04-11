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


@router.get("/employees")
async def get_employee_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Per-employee photo stats for dashboard."""
    result = await db.execute(
        select(
            Photo.uploaded_by,
            func.count(Photo.id).label("photo_count"),
            func.count(func.distinct(Photo.barcode)).label("barcode_count"),
            func.avg(Photo.quality_score).label("avg_quality"),
        )
        .where(Photo.is_deleted == False, Photo.uploaded_by.isnot(None))
        .group_by(Photo.uploaded_by)
        .order_by(func.count(Photo.id).desc())
    )
    rows = result.all()

    # Count quality issues
    issues_result = await db.execute(
        select(Photo.uploaded_by, func.count(Photo.id))
        .where(Photo.is_deleted == False, Photo.quality_score.isnot(None), Photo.quality_score < 3)
        .group_by(Photo.uploaded_by)
    )
    issues_map = dict(issues_result.all())

    # Get user display names
    user_ids = [r.uploaded_by for r in rows if r.uploaded_by]
    users_result = await db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids))) if user_ids else None
    names = dict(users_result.all()) if users_result else {}

    return [
        {
            "user_id": r.uploaded_by,
            "display_name": names.get(r.uploaded_by, ""),
            "photo_count": r.photo_count,
            "barcode_count": r.barcode_count,
            "avg_quality": round(float(r.avg_quality), 1) if r.avg_quality else None,
            "issues_count": issues_map.get(r.uploaded_by, 0),
        }
        for r in rows
    ]
