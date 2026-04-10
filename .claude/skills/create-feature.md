---
description: สร้าง Full-Stack Feature ใหม่ (Backend API + Frontend Page)
user_invocable: true
---

# /create-feature — Full-Stack Feature

## ขั้นตอน

1. **ถาม input**: ชื่อ feature, ข้อมูลอะไร, หน้า UI เป็นยังไง
2. **Backend**:
   - สร้าง SQLAlchemy model (ถ้าต้องการ table ใหม่)
   - สร้าง FastAPI router + Pydantic schemas
   - Register ใน main.py
3. **Frontend**:
   - สร้าง page component
   - เพิ่ม route + sidebar
   - เชื่อม API ด้วย React Query
4. **Review**: ใช้ `code-reviewer` agent ตรวจ
5. **Test**: ทดสอบ end-to-end
