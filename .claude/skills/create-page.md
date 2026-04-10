---
description: สร้าง React page ใหม่ + routing + sidebar menu
user_invocable: true
---

# /create-page — สร้าง Frontend Page

## ขั้นตอน

1. **ถาม input**:
   - ชื่อ page (เช่น `customers`)
   - Route path (เช่น `/customers`)
   - ข้อมูลอะไรที่จะแสดง

2. **สร้างไฟล์**:
   - `frontend/src/pages/{name}/page.tsx`

3. **ตาม pattern**:
   - Reference: `frontend/src/pages/shooting/page.tsx`
   - ใช้ React Query สำหรับ data fetching
   - ใช้ Metronic/Radix components
   - UI text ภาษาไทย
   - Responsive design

4. **เพิ่ม route** ใน `frontend/src/routing/app-routing-setup.tsx`:
   ```tsx
   import { NewPage } from '@/pages/{name}/page';
   // ภายใต้ ProtectedRoute:
   <Route path="/{name}" element={<NewPage />} />
   ```

5. **เพิ่ม sidebar** ใน `frontend/src/config/layout-1.config.tsx`

6. **Verify**: `npx vite build` ผ่าน
