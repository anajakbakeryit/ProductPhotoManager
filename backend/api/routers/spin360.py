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


@router.post("/video")
async def upload_video_360(
    file: UploadFile = File(...),
    barcode: str = Form(...),
    total_frames: int = Form(24),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload video → extract evenly-spaced frames → 360 viewer."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise HTTPException(status_code=400, detail="ต้องติดตั้ง opencv-python บน server")

    barcode = sanitize_barcode(barcode)
    if total_frames < 4 or total_frames > 360:
        raise HTTPException(status_code=400, detail="จำนวนเฟรมต้องอยู่ระหว่าง 4-360")

    storage = get_storage()

    # Save video to temp
    content = await file.read()
    if len(content) > 500 * 1024 * 1024:  # 500MB max
        raise HTTPException(status_code=400, detail="วิดีโอใหญ่เกิน 500 MB")

    ext = os.path.splitext(file.filename or ".mp4")[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        video_path = tmp.name

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="ไม่สามารถเปิดไฟล์วิดีโอ")

        video_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if video_total < total_frames:
            total_frames = video_total

        # Calculate evenly-spaced frame indices
        indices = [int(i * video_total / total_frames) for i in range(total_frames)]

        # Find or create product
        result = await db.execute(select(Product).where(Product.barcode == barcode))
        product = result.scalar_one_or_none()
        if not product:
            product = Product(barcode=barcode)
            db.add(product)
            await db.flush()

        # Create dirs
        for folder in ["360", "original"]:
            for sz in ["S", "M", "L", "OG"]:
                os.makedirs(storage.get_path(f"{folder}/{barcode}/{sz}"), exist_ok=True)

        base_names = []
        for i, frame_idx in enumerate(indices):
            frame_num = i + 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            # BGR → RGB → PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = to_srgb(Image.fromarray(frame_rgb))
            base = f"{barcode}_360_{frame_num:02d}"

            # Save multi-res to both 360/ and original/
            for folder in ["360", "original"]:
                with tempfile.TemporaryDirectory() as tmpdir:
                    save_multi_resolution(img, tmpdir, base)
                    for sz in ["S", "M", "L", "OG"]:
                        for f in os.listdir(os.path.join(tmpdir, sz)):
                            storage.upload_file(
                                os.path.join(tmpdir, sz, f),
                                f"{folder}/{barcode}/{sz}/{f}"
                            )

            # DB record
            photo = Photo(
                product_id=product.id, barcode=barcode, angle="360",
                count=frame_num, original_key=f"360/{barcode}/OG/{base}_OG.jpg",
                filename=f"{base}.jpg", status="done",
                width=img.width, height=img.height, uploaded_by=user.id,
            )
            db.add(photo)
            base_names.append(base)

        cap.release()

        if not base_names:
            raise HTTPException(status_code=400, detail="ไม่สามารถแยกเฟรมจากวิดีโอ")

        # Generate size_map + viewer
        size_map = {sz: [f"{sz}/{b}_{sz}.jpg" for b in base_names] for sz in ["S", "M", "L", "OG"]}
        storage.upload(json.dumps(size_map).encode("utf-8"), f"360/{barcode}/_size_map.json")

        from gen_viewer import generate_viewer
        try:
            generate_viewer(storage.get_path(f"360/{barcode}"), barcode)
        except Exception as e:
            logger.warning(f"[spin360] viewer generation failed: {e}")

        product.photo_count = (product.photo_count or 0) + len(base_names)
        await db.commit()

        return {"barcode": barcode, "total_frames": len(base_names), "message": f"แยก {len(base_names)} เฟรมสำเร็จ"}

    finally:
        os.unlink(video_path)


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
