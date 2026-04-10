"""
ProductPhotoManager — FastAPI Application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.api.config import settings
from backend.api.deps import engine, async_session, get_current_user
from backend.api.models.db import Base, User, AppSettings
from fastapi import WebSocket, WebSocketDisconnect
from backend.api.routers import auth, products, photos
from backend.api.routers import settings as settings_router
from backend.api.routers import sessions, gallery, reports, spin360
from backend.api.websocket import ws_manager

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
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(gallery.router, prefix="/api/gallery", tags=["gallery"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(spin360.router, prefix="/api/spin360", tags=["spin360"])


# WebSocket endpoint for real-time pipeline status
@app.websocket("/ws/processing")
async def ws_processing(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Serve storage files with auth check (dev mode skips auth via deps)
from fastapi.responses import FileResponse as _FileResponse

@app.get("/api/storage/{path:path}")
async def serve_storage(path: str, _user=Depends(get_current_user)):
    """Serve storage files with authentication."""
    from backend.api.services.storage import get_storage
    storage = get_storage()
    if not storage.exists(path):
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")
    return _FileResponse(storage.get_path(path))


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "dev_mode": settings.dev_mode}
