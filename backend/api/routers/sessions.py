"""
Sessions router — shooting session tracking.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Session, Photo, User

router = APIRouter()


@router.post("/start", status_code=201)
async def start_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # End any active session first
    result = await db.execute(
        select(Session).where(Session.user_id == user.id, Session.is_active == True)
    )
    active = result.scalar_one_or_none()
    if active:
        active.is_active = False
        active.ended_at = datetime.utcnow()

    session = Session(user_id=user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": session.id, "started_at": session.started_at.isoformat()}


@router.post("/{session_id}/end")
async def end_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="ไม่พบเซสชัน")
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์จบเซสชันนี้")

    session.is_active = False
    session.ended_at = datetime.utcnow()

    # Count photos in this session
    count = (await db.execute(
        select(func.count()).where(Photo.session_id == session_id, Photo.is_deleted == False)
    )).scalar() or 0
    session.photo_count = count

    # Count distinct barcodes
    bc_count = (await db.execute(
        select(func.count(func.distinct(Photo.barcode))).where(
            Photo.session_id == session_id, Photo.is_deleted == False
        )
    )).scalar() or 0
    session.barcode_count = bc_count

    await db.commit()
    return {"message": "จบเซสชันแล้ว", "photo_count": count, "barcode_count": bc_count}


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    total = (await db.execute(select(func.count()).select_from(Session))).scalar() or 0

    result = await db.execute(
        select(Session).order_by(Session.started_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    sessions = result.scalars().all()

    data = [{
        "id": s.id,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "photo_count": s.photo_count,
        "barcode_count": s.barcode_count,
        "is_active": s.is_active,
    } for s in sessions]

    return {"data": data, "total": total, "page": page, "limit": limit}


@router.get("/active")
async def get_active_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session).where(Session.user_id == user.id, Session.is_active == True)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    return {
        "id": session.id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "photo_count": session.photo_count,
    }
