"""
Products router — barcode CRUD.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Product, User

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
    created_at: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, product):
        return cls(
            id=product.id, barcode=product.barcode,
            name=product.name or "", category=product.category or "",
            note=product.note or "", photo_count=product.photo_count or 0,
            created_at=product.created_at.isoformat() if product.created_at else None,
        )


@router.get("")
async def list_products(
    search: str = Query("", description="ค้นหาจากบาร์โค้ด/ชื่อ"),
    category: str = Query("", description="กรองตาม category"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = select(Product)
    if search:
        query = query.where(
            Product.barcode.ilike(f"%{search}%") | Product.name.ilike(f"%{search}%")
        )
    if category:
        query = query.where(Product.category == category)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "data": [ProductOut.from_model(p).model_dump() for p in products],
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
