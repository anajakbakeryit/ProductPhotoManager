"""
Auth router — login, me, user management.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt as _bcrypt
from jose import jwt

from backend.api.config import settings
from backend.api.deps import get_db, get_current_user
from backend.api.models.db import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


def _create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire},
                      settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == body.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not _bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    token = _create_token(user.id)
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "username": user.username,
              "display_name": user.display_name, "role": user.role},
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, username=user.username,
                   display_name=user.display_name, role=user.role)
