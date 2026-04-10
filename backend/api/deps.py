"""
FastAPI dependencies — DB session, auth, storage.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from backend.api.config import settings

# ── Database ──────────────────────────────────────────────
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


# ── Auth ──────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from backend.api.models.db import User

    # Dev mode: skip auth, return first admin user
    if settings.dev_mode:
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ไม่ได้เข้าสู่ระบบ")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret,
                             algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ไม่ถูกต้อง")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token หมดอายุหรือไม่ถูกต้อง")

    result = await db.execute(select(User).where(User.id == int(user_id), User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ผู้ใช้ไม่พบหรือถูกปิดใช้งาน")
    return user
