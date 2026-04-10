---
description: Debug และ fix bug อย่างเป็นระบบ
user_invocable: true
---

# /fix-bug — Debug & Fix

## ขั้นตอน

1. **เข้าใจปัญหา**: ถาม user ว่าเกิดอะไร, reproduce ยังไง
2. **ค้นหา root cause**:
   - ดู console errors (browser + backend terminal)
   - Trace จาก frontend → API → backend → DB
   - ค้นหาโค้ดที่เกี่ยวข้อง
3. **Fix**: แก้ที่ root cause ไม่ใช่ workaround
4. **Verify**: ทดสอบว่า fix ทำงาน + ไม่ break อย่างอื่น
5. **Test**: `pytest tests/ -v` ยังผ่าน
