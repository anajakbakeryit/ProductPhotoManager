"""
Users router — CRUD users (admin only), change password.
"""
import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import User

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "user"


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


def _hash_pw(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _check_pw(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def _require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="เฉพาะผู้ดูแลระบบเท่านั้น")


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [{
        "id": u.id, "username": u.username, "display_name": u.display_name,
        "role": u.role, "is_active": u.is_active,
    } for u in users]


@router.post("", status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role ต้องเป็น admin หรือ user")

    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="ชื่อผู้ใช้นี้มีอยู่แล้ว")

    new_user = User(
        username=body.username,
        password_hash=_hash_pw(body.password),
        display_name=body.display_name,
        role=body.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")

    if body.display_name is not None:
        target.display_name = body.display_name
    if body.role is not None:
        if body.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="role ต้องเป็น admin หรือ user")
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active

    await db.commit()
    return {"id": target.id, "username": target.username, "role": target.role, "is_active": target.is_active}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    body: ChangePassword,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin resets any user's password. User changes own password."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้")

    # Non-admin can only change own password
    if user.role != "admin" and user.id != user_id:
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์เปลี่ยนรหัสผ่านผู้อื่น")

    # Verify current password (for self-change)
    if user.id == user_id:
        if not _check_pw(body.current_password, target.password_hash):
            raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร")

    target.password_hash = _hash_pw(body.new_password)
    await db.commit()
    return {"message": "เปลี่ยนรหัสผ่านแล้ว"}


@router.post("/me/change-password")
async def change_own_password(
    body: ChangePassword,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Change own password."""
    if not _check_pw(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร")

    result = await db.execute(select(User).where(User.id == user.id))
    target = result.scalar_one_or_none()
    target.password_hash = _hash_pw(body.new_password)
    await db.commit()
    return {"message": "เปลี่ยนรหัสผ่านแล้ว"}
