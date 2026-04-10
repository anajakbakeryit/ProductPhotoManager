# Backend Rules (FastAPI + SQLAlchemy)

## Module Structure
- Pattern: router → service → SQLAlchemy model
- **ห้ามเรียก DB session จาก router โดยตรง** ถ้ามี business logic → ย้ายไป service
- Router files อยู่ใน `backend/api/routers/`
- Reference: `backend/api/routers/products.py`

## Schemas (Pydantic)
- ใช้ Pydantic BaseModel สำหรับ request/response
- ใช้ `model_validate()` + `model_dump()` (Pydantic v2)
- Error messages เป็น**ภาษาไทย**

## Error Handling
- ใช้ FastAPI `HTTPException`:
  - `404` — ไม่พบข้อมูล
  - `400` — input ไม่ถูกต้อง
  - `409` — ข้อมูลซ้ำ
  - `401` — ไม่ได้เข้าสู่ระบบ
  - `403` — ไม่มีสิทธิ์

## Pagination
- Default: `page=1`, `limit=50`
- Response shape: `{ data, total, page, limit }`

## Soft Delete
- ทุก query ต้อง filter `Photo.is_deleted == False`
- Delete = update `is_deleted=True, deleted_at=datetime.utcnow()`
- **ห้าม hard delete**

## Dependencies
- ใช้ `Depends(get_db)` สำหรับ DB session
- ใช้ `Depends(get_current_user)` สำหรับ auth (dev mode skip อัตโนมัติ)

## Async
- Router functions ต้องเป็น `async def`
- ใช้ `await` กับ DB queries
- Image processing หนัก → ใช้ `ThreadPoolExecutor` (background thread)

## File Uploads
- ใช้ `UploadFile` + `File(...)` จาก FastAPI
- เก็บผ่าน `storage.py` service (local dev / GCS production)
