"""
Products router — barcode CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, Photo, User
from backend.api.services.storage import get_storage

router = APIRouter()


class ProductCreate(BaseModel):
    barcode: str
    name: str = ""
    category: str = ""
    note: str = ""


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    note: str | None = None


class ProductOut(BaseModel):
    id: int
    barcode: str
    name: str
    category: str
    note: str
    photo_count: int
    color: str
    priority: str
    photo_status: str
    has_spin360: bool
    quality_score: int | None
    created_at: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, product):
        return cls(
            id=product.id, barcode=product.barcode,
            name=product.name or "", category=product.category or "",
            note=product.note or "", photo_count=product.photo_count or 0,
            color=getattr(product, 'color', '') or "",
            priority=getattr(product, 'priority', 'normal') or "normal",
            photo_status=getattr(product, 'photo_status', 'pending') or "pending",
            has_spin360=getattr(product, 'has_spin360', False) or False,
            quality_score=getattr(product, 'quality_score', None),
            created_at=product.created_at.isoformat() if product.created_at else None,
        )


@router.get("")
async def list_products(
    search: str = Query("", description="ค้นหาจากบาร์โค้ด/ชื่อ"),
    category: str = Query("", description="กรองตาม category"),
    status: str = Query("", description="กรองตาม photo_status"),
    priority: str = Query("", description="กรองตาม priority"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    import logging
    logger = logging.getLogger(__name__)
    try:
        return await _list_products_impl(db, search, category, status, priority, page, limit)
    except Exception as e:
        logger.error(f"list_products error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline-stats")
async def pipeline_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get counts per photo_status for pipeline dashboard."""
    result = await db.execute(
        select(Product.photo_status, func.count(Product.id))
        .group_by(Product.photo_status)
    )
    counts = dict(result.all())
    return {
        "pending": counts.get("pending", 0),
        "shooting": counts.get("shooting", 0),
        "spin360": counts.get("spin360", 0),
        "completed": counts.get("completed", 0),
        "total": sum(counts.values()),
    }


async def _list_products_impl(db, search, category, status, priority, page, limit):
    query = select(Product)
    if search:
        query = query.where(
            Product.barcode.ilike(f"%{search}%") | Product.name.ilike(f"%{search}%")
        )
    if category:
        query = query.where(Product.category == category)
    if status:
        query = query.where(Product.photo_status == status)
    if priority:
        query = query.where(Product.priority == priority)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Product.id.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    # Enrich with thumbnail, angle progress, last activity
    storage = get_storage()
    enriched = []
    for p in products:
        out = ProductOut.from_model(p).model_dump()

        # Get angle coverage + thumbnail
        photo_result = await db.execute(
            select(Photo.angle, Photo.original_key, Photo.created_at, Photo.uploaded_by)
            .where(Photo.barcode == p.barcode, Photo.is_deleted == False)
            .order_by(Photo.created_at.desc())
        )
        photos = photo_result.all()
        angles_done = list(set(r.angle for r in photos))
        out["angles_done"] = angles_done
        out["angles_total"] = 8

        # Thumbnail (first front photo, or first photo)
        front = next((r for r in photos if r.angle == "front"), None)
        first = front or (photos[0] if photos else None)
        if first:
            key = first.original_key.replace("/OG/", "/S/").replace("_OG.", "_S.")
            out["thumbnail_url"] = storage.get_url(key)
            out["last_activity"] = first.created_at.isoformat() if first.created_at else None
        else:
            out["thumbnail_url"] = None
            out["last_activity"] = None

        enriched.append(out)

    return {
        "data": enriched,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{barcode}")
async def get_product(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")
    return ProductOut.from_model(product)


@router.post("", status_code=201)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Check duplicate
    existing = await db.execute(select(Product).where(Product.barcode == body.barcode))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="บาร์โค้ดนี้มีอยู่แล้ว")

    product = Product(barcode=body.barcode, name=body.name,
                      category=body.category, note=body.note)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductOut.from_model(product)


@router.put("/{barcode}")
async def update_product(
    barcode: str,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="ไม่พบสินค้า")

    if body.name is not None:
        product.name = body.name
    if body.category is not None:
        product.category = body.category
    if body.note is not None:
        product.note = body.note

    await db.commit()
    await db.refresh(product)
    return ProductOut.from_model(product)
