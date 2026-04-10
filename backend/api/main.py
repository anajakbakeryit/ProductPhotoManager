"""
ProductPhotoManager — FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select

from backend.api.config import settings
from backend.api.deps import engine, async_session
from backend.api.models.db import Base, User, AppSettings
from backend.api.routers import auth, products, photos

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + seed admin user."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    # Seed admin user if not exists
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        if not result.scalar_one_or_none():
            import bcrypt as _bcrypt
            pw_hash = _bcrypt.hashpw(settings.admin_password.encode(), _bcrypt.gensalt()).decode()
            admin = User(
                username=settings.admin_username,
                password_hash=pw_hash,
                display_name="ผู้ดูแลระบบ",
                role="admin",
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Created admin user: {settings.admin_username}")

        # Seed default settings if not exists
        result = await db.execute(select(AppSettings))
        if not result.scalar_one_or_none():
            from core.config import DEFAULT_CONFIG
            default_settings = AppSettings(config=DEFAULT_CONFIG)
            db.add(default_settings)
            await db.commit()
            logger.info("Created default app settings")

    yield

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(photos.router, prefix="/api/photos", tags=["photos"])

# Serve local storage files (dev only)
import os
storage_path = os.path.abspath(settings.storage_local_path)
if os.path.isdir(storage_path):
    app.mount("/api/storage", StaticFiles(directory=storage_path), name="storage")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
