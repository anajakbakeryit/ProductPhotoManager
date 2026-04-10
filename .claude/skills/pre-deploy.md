---
description: Pre-deploy checklist ตรวจสอบก่อน deploy
user_invocable: true
---

# /pre-deploy — Pre-Deploy Checklist

## ตรวจสอบ

- [ ] `pytest tests/ -v` — ทุก test ผ่าน
- [ ] `cd frontend && npx vite build` — frontend build สำเร็จ
- [ ] `cd frontend && npx tsc --noEmit` — TypeScript ไม่มี error
- [ ] ไม่มี `console.log` ค้างใน frontend
- [ ] ไม่มี `.env` หรือ secrets ใน git
- [ ] `DEV_MODE` ตั้งเป็น `false` สำหรับ production
- [ ] API health check ทำงาน: `curl localhost:8000/api/health`
- [ ] ทดสอบ upload รูปจริง + preview แสดง
- [ ] Git status clean — ไม่มีไฟล์ค้าง
