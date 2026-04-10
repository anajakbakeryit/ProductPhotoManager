"""
Photos router — upload, list, delete, undo.
"""
import os
import logging
import tempfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, Photo, ActivityLog, User
from backend.api.services.storage import get_storage
from utils.sanitize import sanitize_barcode
from utils.color_profile import to_srgb, save_multi_resolution

logger = logging.getLogger(__name__)
router = APIRouter()

# Background thread pool for image processing
_pipeline_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pipeline")


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

    uploaded = []
    for file in files:
        current_max += 1
        ext = os.path.splitext(file.filename or ".jpg")[1].lower()
        if not ext:
            ext = ".jpg"
        filename = f"{barcode}_{angle}_{current_max:02d}{ext}"

        # Save to temp file for processing
        content = await file.read()
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


@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Soft delete a photo."""
    result = await db.execute(select(Photo).where(Photo.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพ")

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
    _user: User = Depends(get_current_user),
):
    """Restore a soft-deleted photo."""
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.is_deleted == True)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="ไม่พบรูปภาพที่ลบ")

    photo.is_deleted = False
    photo.deleted_at = None

    db.add(ActivityLog(
        photo_id=photo.id, action="undo",
        message=f"กู้คืน {photo.filename}", status="success",
    ))
    await db.commit()
    return {"message": "กู้คืนรูปภาพแล้ว", "id": photo_id}
