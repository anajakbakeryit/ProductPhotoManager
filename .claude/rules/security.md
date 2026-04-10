# Security Rules

## JWT & Authentication
- Access token เก็บใน **JS variable (in-memory)** — ห้ามเก็บใน localStorage
- Dev mode: `DEV_MODE=true` ข้าม auth ทั้งหมด
- Production: ทุก API endpoint ต้องผ่าน `Depends(get_current_user)`

## Public Endpoints (ไม่ต้อง auth)
- `GET /api/health` — health check + dev mode flag

## Input Validation
- Backend: Pydantic schemas validate ทุก request body
- Frontend: Zod + React Hook Form สำหรับ form validation
- Sanitize barcode ก่อนใช้เป็น filename/path (`utils/sanitize.py`)

## File Upload Security
- ตรวจ file extension ก่อน accept
- Sanitize barcode ก่อนใช้เป็น storage key
- ห้ามให้ user กำหนด storage path โดยตรง

## Secrets
- **ห้าม commit** `.env` files
- ใช้ environment variables สำหรับ `DATABASE_URL`, `JWT_SECRET`
