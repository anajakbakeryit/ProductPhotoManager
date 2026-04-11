"""
Auto-update product photo_status based on photo counts.

Status flow: pending → shooting → spin360 → completed
"""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.models.db import Product, Photo

logger = logging.getLogger(__name__)

REQUIRED_ANGLES = {'front', 'back', 'left', 'right', 'top', 'bottom', 'detail', 'package'}


async def update_product_status(db: AsyncSession, barcode: str):
    """Recalculate and update product photo_status."""
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        return

    # Count photos per angle
    angle_result = await db.execute(
        select(Photo.angle, func.count(Photo.id))
        .where(Photo.barcode == barcode, Photo.is_deleted == False)
        .group_by(Photo.angle)
    )
    angle_counts = dict(angle_result.all())

    # Count total photos
    total = sum(angle_counts.values())
    product.photo_count = total

    # Determine status
    covered_angles = set(angle_counts.keys()) & REQUIRED_ANGLES
    all_angles_done = covered_angles == REQUIRED_ANGLES

    if total == 0:
        product.photo_status = "pending"
    elif all_angles_done and product.has_spin360:
        product.photo_status = "completed"
    elif all_angles_done:
        product.photo_status = "spin360"
    else:
        product.photo_status = "shooting"

    # Calculate quality score (average of photo scores)
    score_result = await db.execute(
        select(func.avg(Photo.quality_score))
        .where(Photo.barcode == barcode, Photo.is_deleted == False, Photo.quality_score.isnot(None))
    )
    avg_score = score_result.scalar()
    if avg_score is not None:
        product.quality_score = round(float(avg_score))

    await db.commit()
    logger.info(f"Product {barcode}: status={product.photo_status}, angles={len(covered_angles)}/8, total={total}")
