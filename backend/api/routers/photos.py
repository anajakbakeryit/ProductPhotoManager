"""
Photos router — upload, list, delete, undo.
"""
import io
import os
import logging
import tempfile
import zipfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from fastapi.responses import StreamingResponse
from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, Photo, ActivityLog, User
from backend.api.services.storage import get_storage
from utils.sanitize import sanitize_barcode
from utils.color_profile import to_srgb, save_multi_resolution

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_photos(
    files: list[UploadFile] = File(...),
    barcode: str = Form(...),
    angle: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload one or more photos. Auto-rename, generate multi-res, enqueue pipeline."""
    storage = get_storage()
    barcode = sanitize_barcode(barcode)

    # Find active session for this user
    from backend.api.models.db import Session as SessionModel
    active_session = (await db.execute(
        select(SessionModel).where(SessionModel.user_id == user.id, SessionModel.is_active == True)
    )).scalar_one_or_none()
    session_id = active_session.id if active_session else None

    # Find or create product
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        product = Product(barcode=barcode)
        db.add(product)
        await db.flush()

    # Get current max count for this barcode+angle
    count_result = await db.execute(
        select(func.max(Photo.count)).where(
            Photo.barcode == barcode, Photo.angle == angle, Photo.is_deleted == False
        )
    )
    current_max = count_result.scalar() or 0

    # Validate file count + extensions
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".cr2", ".cr3", ".arw", ".nef"}
    MAX_FILES = 50
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB per file

    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"อัปโหลดได้สูงสุด {MAX_FILES} ไฟล์ต่อครั้ง")

    # Validate angle
    ALLOWED_ANGLES = {"front", "back", "left", "right", "top", "bottom", "detail", "package", "360"}
    if angle not in ALLOWED_ANGLES:
        raise HTTPException(status_code=400, detail=f"มุมถ่าย '{angle}' ไม่ถูกต้อง")

    uploaded = []
    for file in files:
        current_max += 1
        ext = os.path.splitext(file.filename or ".jpg")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"ไม่รองรับไฟล์นามสกุล {ext}")
        filename = f"{barcode}_{angle}_{current_max:02d}{ext}"

        # Save to temp file for processing (with size limit)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"ไฟล์ {file.filename} ใหญ่เกิน 100 MB")
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Get image dimensions
            img = Image.open(tmp_path)
            width, height = img.size

            # Generate multi-resolution and upload
            base_name = os.path.splitext(filename)[0]
            orig_dir = os.path.join("original", barcode)

            # Convert to sRGB and save multi-res
            img_srgb = to_srgb(img)
            with tempfile.TemporaryDirectory() as tmpdir:
                save_multi_resolution(img_srgb, tmpdir, base_name)
                # Upload each size to storage
                for size in ["S", "M", "L", "OG"]:
                    size_dir = os.path.join(tmpdir, size)
                    for f in os.listdir(size_dir):
                        key = f"{orig_dir}/{size}/{f}"
                        storage.upload_file(os.path.join(size_dir, f), key)

            original_key = f"{orig_dir}/OG/{base_name}_OG.jpg"

            # Create DB record
            photo = Photo(
                product_id=product.id,
                barcode=barcode,
                angle=angle,
                count=current_max,
                original_key=original_key,
                filename=filename,
                status="uploaded",
                width=width,
                height=height,
                file_size=len(content),
                uploaded_by=user.id,
                session_id=session_id,
            )
            db.add(photo)
            await db.flush()

            # Log activity
            db.add(ActivityLog(
                photo_id=photo.id, action="upload",
                message=f"อัปโหลด {filename}", status="success",
            ))

            uploaded.append({
                "id": photo.id,
                "filename": filename,
                "barcode": barcode,
                "angle": angle,
                "count": current_max,
                "width": width,
                "height": height,
                "preview_url": storage.get_url(f"{orig_dir}/S/{base_name}_S.jpg"),
            })

        finally:
            os.unlink(tmp_path)

    # Update product photo count
    product.photo_count = (product.photo_count or 0) + len(uploaded)
    await db.commit()

    # Enqueue background processing for each photo (cutout + watermark)
    from backend.api.services.pipeline import enqueue_processing
    from backend.api.routers.settings import _get_config_dict
    config = await _get_config_dict(db)
    for item in uploaded:
        await enqueue_processing(item["id"], barcode, item["filename"], config)

    return {"uploaded": uploaded, "total": len(uploaded)}


@router.get("")
async def list_photos(
    barcode: str = Query(""),
    angle: str = Query(""),
    status: str = Query(""),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List photos with filters."""
    query = select(Photo).where(Photo.is_deleted == False)
    if barcode:
        query = query.where(Photo.barcode == barcode)
    if angle:
        query = query.where(Photo.angle == angle)
    if status:
        query = query.where(Photo.status == status)

    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar() or 0

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
            "count": p.count,
            "filename": p.filename,
            "status": p.status,
            "width": p.width,
            "height": p.height,
            "has_cutout": p.has_cutout,
            "has_watermark": p.has_watermark,
            "preview_url": storage.get_url(f"original/{p.barcode}/S/{base}_S.jpg"),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"data": data, "total": total, "page": page, "limit": limit}


@router.get("/{photo_id}")
async def get_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get photo detail with all variant URLs."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพ")

    storage = get_storage()
    base = os.path.splitext(photo.filename)[0]
    bc = photo.barcode

    urls = {}
    for variant in ["original", "cutout", "watermarked", "watermarked_original"]:
        urls[variant] = {}
        for size in ["S", "M", "L", "OG"]:
            ext = ".png" if variant == "cutout" else ".jpg"
            key = f"{variant}/{bc}/{size}/{base}_{size}{ext}"
            if storage.exists(key):
                urls[variant][size] = storage.get_url(key)

    return {
        "id": photo.id,
        "barcode": bc,
        "angle": photo.angle,
        "filename": photo.filename,
        "status": photo.status,
        "width": photo.width,
        "height": photo.height,
        "urls": urls,
        "created_at": photo.created_at.isoformat() if photo.created_at else None,
    }


@router.post("/{photo_id}/reprocess")
async def reprocess_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run pipeline for a single photo."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id, Photo.is_deleted == False))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพ")

    photo.status = "processing"
    await db.commit()

    from backend.api.services.pipeline import enqueue_processing
    from backend.api.routers.settings import _get_config_dict
    config = await _get_config_dict(db)
    await enqueue_processing(photo.id, photo.barcode, photo.filename, config)

    return {"message": "เริ่มประมวลผลใหม่", "id": photo_id}


@router.post("/batch/delete")
async def batch_delete(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete multiple photos."""
    photo_ids = body.get("photo_ids", [])
    if not photo_ids or len(photo_ids) > 200:
        raise HTTPException(status_code=400, detail="ระบุ photo_ids 1-200 รายการ")

    deleted = 0
    for pid in photo_ids:
        result = await db.execute(select(Photo).where(Photo.id == pid, Photo.is_deleted == False))
        photo = result.scalar_one_or_none()
        if photo and (photo.uploaded_by == user.id or user.role == "admin"):
            photo.is_deleted = True
            photo.deleted_at = datetime.utcnow()
            deleted += 1

    await db.commit()
    return {"message": f"ลบ {deleted} รูป", "deleted": deleted}


@router.post("/batch/reprocess")
async def batch_reprocess(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run pipeline for multiple photos."""
    photo_ids = body.get("photo_ids", [])
    if not photo_ids or len(photo_ids) > 50:
        raise HTTPException(status_code=400, detail="ระบุ photo_ids 1-50 รายการ")

    from backend.api.services.pipeline import enqueue_processing
    from backend.api.routers.settings import _get_config_dict
    config = await _get_config_dict(db)

    queued = 0
    for pid in photo_ids:
        result = await db.execute(select(Photo).where(Photo.id == pid, Photo.is_deleted == False))
        photo = result.scalar_one_or_none()
        if photo:
            photo.status = "processing"
            await db.flush()
            await enqueue_processing(photo.id, photo.barcode, photo.filename, config)
            queued += 1

    await db.commit()
    return {"message": f"เริ่มประมวลผล {queued} รูป", "queued": queued}


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete a photo (owner or admin only)."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพ")
    if photo.uploaded_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ลบรูปภาพนี้")

    photo.is_deleted = True
    photo.deleted_at = datetime.utcnow()

    db.add(ActivityLog(
        photo_id=photo.id, action="delete",
        message=f"ลบ {photo.filename}", status="success",
    ))
    await db.commit()
    return {"message": "ลบรูปภาพแล้ว", "id": photo_id}


@router.post("/{photo_id}/undo")
async def undo_delete(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Restore a soft-deleted photo (owner or admin only)."""
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.is_deleted == True)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพที่ลบ")
    if photo.uploaded_by != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์กู้คืนรูปภาพนี้")

    photo.is_deleted = False
    photo.deleted_at = None

    db.add(ActivityLog(
        photo_id=photo.id, action="undo",
        message=f"กู้คืน {photo.filename}", status="success",
    ))
    await db.commit()
    return {"message": "กู้คืนรูปภาพแล้ว", "id": photo_id}


@router.post("/download-zip")
async def download_zip(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Download multiple photos as ZIP (original/OG)."""
    photo_ids = body.get("photo_ids", [])
    variant = body.get("variant", "original")
    size = body.get("size", "OG")

    if not photo_ids or len(photo_ids) > 200:
        raise HTTPException(status_code=400, detail="ระบุ photo_ids 1-200 รายการ")

    storage = get_storage()
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for pid in photo_ids:
            result = await db.execute(select(Photo).where(Photo.id == pid, Photo.is_deleted == False))
            photo = result.scalar_one_or_none()
            if not photo:
                continue
            base = os.path.splitext(photo.filename)[0]
            ext = ".png" if variant == "cutout" else ".jpg"
            key = f"{variant}/{photo.barcode}/{size}/{base}_{size}{ext}"
            if storage.exists(key):
                data = storage.download(key)
                zf.writestr(f"{photo.barcode}/{photo.filename}", data)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=photos.zip"},
    )
