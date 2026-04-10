---
description: สร้าง FastAPI router module ใหม่ (router + schemas + tests)
user_invocable: true
---

# /create-module — สร้าง Backend Module

## ขั้นตอน

1. **ถาม input**:
   - ชื่อ module (เช่น `customers`, `orders`)
   - Endpoints ที่ต้องการ (CRUD? custom?)

2. **สร้างไฟล์**:
   - `backend/api/routers/{name}.py` — FastAPI router
   - `backend/api/schemas/{name}.py` — Pydantic schemas (ถ้าจำเป็น)

3. **ตาม pattern**:
   - Reference: `backend/api/routers/products.py`
   - ทุก endpoint มี `Depends(get_current_user)`
   - Pagination: `{ data, total, page, limit }`
   - Error messages ภาษาไทย

4. **Register router** ใน `backend/api/main.py`:
   ```python
   app.include_router({name}.router, prefix="/api/{name}", tags=["{name}"])
   ```

5. **Verify**: รัน backend ดูว่า import ไม่ error
