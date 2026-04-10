# ProductPhotoManager — Web App

## Project Overview
Web application สำหรับจัดการถ่ายภาพสินค้าในสตูดิโอ สแกนบาร์โค้ด → เลือกมุมถ่าย → อัปโหลดรูป → ประมวลผลอัตโนมัติ (ลบพื้นหลัง + ใส่ลายน้ำ + Multi-Res)

## Tech Stack
- **Frontend**: React 19 + Vite 7 + Tailwind CSS 4 + Metronic v9.4.8
- **Backend**: FastAPI (Python) + SQLAlchemy + PostgreSQL
- **Image Processing**: Pillow, rembg (background removal), OpenCV (video→360)
- **Storage**: Local filesystem (dev) / GCS (production)
- **Auth**: JWT (python-jose) — dev mode ข้าม login ได้
- **Realtime**: WebSocket สำหรับ pipeline status

## Development
```bash
# วิธีง่ายสุด — ดับเบิลคลิก dev.bat
dev.bat

# หรือรัน manual:
# Terminal 1: PostgreSQL
docker-compose up -d

# Terminal 2: Backend (localhost:8000)
python -m uvicorn backend.api.main:app --reload --port 8000

# Terminal 3: Frontend (localhost:5173)
cd frontend && npx vite
```

## Dev Mode
- `DEV_MODE=true` (default) → ไม่ต้อง login เปิดใช้งานได้เลย
- `DEV_MODE=false` → ต้อง login ด้วย username/password
- Default admin: `admin` / `admin1234`

## Project Structure
```
ProductPhotoManager/
├── backend/                    # FastAPI Python backend
│   ├── api/
│   │   ├── main.py             # FastAPI app, CORS, lifespan, WebSocket
│   │   ├── config.py           # Settings (env vars, defaults)
│   │   ├── deps.py             # Dependencies (DB session, auth, storage)
│   │   ├── websocket.py        # WebSocket manager
│   │   ├── routers/            # API route handlers
│   │   │   ├── auth.py         # Login, JWT, user info
│   │   │   ├── products.py     # Barcode CRUD
│   │   │   ├── photos.py       # Upload, list, delete, undo
│   │   │   ├── settings.py     # App config + watermark upload
│   │   │   ├── sessions.py     # Session tracking
│   │   │   ├── gallery.py      # Photo browsing + activity log
│   │   │   ├── reports.py      # HTML/CSV export
│   │   │   └── spin360.py      # 360° frames + video + viewer
│   │   ├── models/db.py        # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/
│   │       ├── storage.py      # Local/GCS storage abstraction
│   │       └── pipeline.py     # Background image processing
│   └── requirements.txt
├── core/                       # Shared image processing (reused from legacy)
│   ├── image_processor.py      # Watermark + rembg pipeline logic
│   └── config.py               # DEFAULT_CONFIG, validate_config
├── utils/                      # Shared utilities
│   ├── color_profile.py        # to_srgb, save_multi_resolution, _SRGB_ICC
│   ├── sanitize.py             # sanitize_barcode, is_path_within
│   └── constants.py            # MULTI_RES presets
├── frontend/                   # React + Metronic UI
│   ├── src/
│   │   ├── pages/              # ShootingPage, GalleryPage, SettingsPage, etc.
│   │   ├── store/              # Zustand: authStore, shootingStore
│   │   ├── lib/api.ts          # API client (JWT in-memory)
│   │   ├── config/             # Metronic layout + sidebar config
│   │   └── components/         # Metronic UI components (100+)
│   └── package.json
├── tests/                      # pytest unit tests
├── gen_viewer.py               # 360° HTML viewer generator
├── docker-compose.yml          # PostgreSQL for local dev
├── dev.bat                     # One-click dev startup (Windows)
└── dev.sh                      # One-click dev startup (macOS/Linux)
```

## Agent Instructions

### หลักการทำงาน

1. **อ่าน Workflow ก่อนทำงานเสมอ**
   - ก่อนสร้าง API router → อ่าน `workflows/create-api-module.md`
   - ก่อนสร้าง React page → อ่าน `workflows/create-page.md`
   - ก่อนแก้ DB schema → อ่าน `workflows/db-change.md`
   - ก่อน fix bug → อ่าน `workflows/fix-bug.md`

2. **ค้นหาก่อนสร้าง**
   - ค้นหา existing components, hooks, utilities ก่อนสร้างใหม่
   - Backend reference: `backend/api/routers/products.py`
   - Frontend reference: `frontend/src/pages/shooting/page.tsx`

3. **ตาม Pattern เดิม**
   - Backend: FastAPI router → service → SQLAlchemy
   - Frontend: React Query + Zustand + Radix/Metronic components
   - ภาษาไทยสำหรับ UI text ทั้งหมด

### Build Workflow
1. **Write** — เขียน code ตาม workflow + rules
2. **Review** — ใช้ `code-reviewer` agent ตรวจ
3. **Test** — `pytest tests/ -v` + ทดสอบ manual
4. **Fix** — แก้ตาม review + test results
5. **Ship** — commit + push

## API Endpoints
```
POST   /api/auth/login              GET    /api/auth/me
GET    /api/products                POST   /api/products
GET    /api/products/:barcode       PUT    /api/products/:barcode
POST   /api/photos/upload           GET    /api/photos
GET    /api/photos/:id              DELETE /api/photos/:id
POST   /api/photos/:id/undo
GET/PUT /api/settings               POST   /api/settings/watermark
POST   /api/sessions/start          POST   /api/sessions/:id/end
GET    /api/sessions                GET    /api/sessions/active
GET    /api/gallery                 GET    /api/gallery/activity
GET    /api/reports/summary         GET    /api/reports/export/html|csv
POST   /api/spin360/frames          GET    /api/spin360/:barcode
GET    /api/spin360/:barcode/viewer
WS     /ws/processing
GET    /api/health
```

## Database Models (SQLAlchemy)
- **User** — id, username, password_hash, display_name, role, is_active
- **Product** — id, barcode (unique), name, category, note, photo_count
- **Photo** — id, product_id, barcode, angle, count, original_key, filename, status, has_cutout, has_watermark, is_deleted
- **Session** — id, user_id, started_at, ended_at, photo_count, barcode_count
- **AppSettings** — id, config (JSONB), watermark_key
- **ActivityLog** — id, photo_id, action, message, status

## Frontend Pages
| Route | Page | หน้าที่ |
|-------|------|---------|
| `/` | ShootingPage | สแกนบาร์โค้ด → เลือกมุม → อัปโหลด → preview |
| `/gallery` | GalleryPage | ดูรูปทั้งหมด, filter, search |
| `/360` | Spin360Page | อัปโหลด 360° frames / viewer |
| `/sessions` | SessionsPage | ประวัติเซสชัน |
| `/reports` | ReportsPage | ส่งออกรายงาน HTML/CSV |
| `/settings` | SettingsPage | ตั้งค่า pipeline, watermark, 360° |
| `/login` | LoginPage | เข้าสู่ระบบ (ไม่แสดงใน dev mode) |

## Coding Conventions
- **Frontend**: TypeScript, camelCase, Radix UI + Tailwind, React Query + Zustand
- **Backend**: Python, snake_case, FastAPI + SQLAlchemy, Pydantic schemas
- **UI text**: ภาษาไทยทั้งหมด
- **Code**: English variable/function names
- **Formatting**: Prettier (frontend), ruff (backend)

## Image Processing Pipeline
```
Upload → original/ (S/M/L/OG) → DB status='uploaded'
  └── Background thread:
      ├── Watermark on Original → watermarked_original/
      ├── rembg Remove BG → cutout/
      ├── Watermark on Cutout → watermarked/
      └── DB status='done' + WebSocket notify
```

## Storage Structure
```
storage/
├── original/{barcode}/S|M|L|OG/
├── cutout/{barcode}/S|M|L|OG/
├── watermarked/{barcode}/S|M|L|OG/
├── watermarked_original/{barcode}/S|M|L|OG/
├── 360/{barcode}/S|M|L|OG/ + viewer.html
├── _trash/
└── _watermarks/
```
