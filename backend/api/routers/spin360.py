"""
Spin360 router — 360° frame upload, video extraction, viewer generation.
"""
import json
import logging
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, Photo, User
from backend.api.services.storage import get_storage
from utils.sanitize import sanitize_barcode
from utils.color_profile import to_srgb, save_multi_resolution
from PIL import Image

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/frames")
async def upload_360_frames(
    files: list[UploadFile] = File(...),
    barcode: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload individual 360° frames (already extracted/shot)."""
    storage = get_storage()
    barcode = sanitize_barcode(barcode)

    # Find or create product
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        product = Product(barcode=barcode)
        db.add(product)
        await db.flush()

    uploaded = []
    for i, file in enumerate(files):
        frame_num = i + 1
        ext = os.path.splitext(file.filename or ".jpg")[1].lower() or ".jpg"
        filename = f"{barcode}_360_{frame_num:02d}{ext}"
        base_name = os.path.splitext(filename)[0]

        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            img = to_srgb(Image.open(tmp_path))
            width, height = img.size

            # Save multi-res to 360/ and original/
            for folder_prefix in ["360", "original"]:
                with tempfile.TemporaryDirectory() as tmpdir:
                    save_multi_resolution(img, tmpdir, base_name)
                    for size in ["S", "M", "L", "OG"]:
                        for f in os.listdir(os.path.join(tmpdir, size)):
                            storage.upload_file(
                                os.path.join(tmpdir, size, f),
                                f"{folder_prefix}/{barcode}/{size}/{f}"
                            )

            # DB record
            photo = Photo(
                product_id=product.id, barcode=barcode, angle="360",
                count=frame_num, original_key=f"360/{barcode}/OG/{base_name}_OG.jpg",
                filename=filename, status="done", width=width, height=height,
                file_size=len(content), uploaded_by=user.id,
            )
            db.add(photo)
            uploaded.append({"frame": frame_num, "filename": filename})
        finally:
            os.unlink(tmp_path)

    # Generate _size_map.json
    total = len(uploaded)
    size_map = {}
    for sz in ["S", "M", "L", "OG"]:
        size_map[sz] = [
            f"{sz}/{barcode}_360_{i+1:02d}_{sz}.jpg" for i in range(total)
        ]
    storage.upload(
        json.dumps(size_map).encode("utf-8"),
        f"360/{barcode}/_size_map.json"
    )

    # Generate viewer.html
    from gen_viewer import generate_viewer
    viewer_dir = storage.get_path(f"360/{barcode}")
    try:
        generate_viewer(viewer_dir, barcode)
    except Exception as e:
        logger.warning(f"[spin360] viewer generation failed: {e}")

    product.photo_count = (product.photo_count or 0) + total
    await db.commit()

    return {"uploaded": uploaded, "total": total, "barcode": barcode}


@router.get("/{barcode}")
async def get_360_info(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get 360 frame list + size_map for a barcode."""
    storage = get_storage()
    size_map_key = f"360/{barcode}/_size_map.json"

    if not storage.exists(size_map_key):
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล 360° สำหรับบาร์โค้ดนี้")

    size_map = json.loads(storage.download(size_map_key))
    total = len(size_map.get("M", []))

    # Build URLs
    urls = {}
    for sz, paths in size_map.items():
        urls[sz] = [storage.get_url(f"360/{barcode}/{p}") for p in paths]

    return {"barcode": barcode, "total_frames": total, "size_map": urls}


@router.get("/{barcode}/viewer")
async def get_360_viewer(
    barcode: str,
    _user: User = Depends(get_current_user),
):
    """Return the generated 360° viewer HTML."""
    storage = get_storage()
    viewer_key = f"360/{barcode}/viewer.html"

    if not storage.exists(viewer_key):
        raise HTTPException(status_code=404, detail="ไม่พบ viewer สำหรับบาร์โค้ดนี้")

    html = storage.download(viewer_key).decode("utf-8")
    return HTMLResponse(content=html)
