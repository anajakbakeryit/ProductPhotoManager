# Database Rules (SQLAlchemy + PostgreSQL)

## IDs
- ใช้ Integer auto-increment (SERIAL) เป็น primary key
- ใช้ unique constraint บน barcode

## Soft Delete
- Photo model มี `is_deleted` + `deleted_at`
- ทุก query ต้อง filter `is_deleted == False`
- **ห้าม hard delete** ข้อมูลรูปภาพ

## Indexes
- `products.barcode` — unique index
- `photos.barcode` + `photos.angle` — composite index
- `photos.status` — index
- `photos.session_id` — index
- `activity_log.created_at` — descending index

## Migrations
- ใช้ Alembic สำหรับ schema changes
- ตอน dev ใช้ `Base.metadata.create_all()` (auto-create)
- ตอน production ใช้ `alembic upgrade head`

## Settings
- ใช้ JSONB column (`AppSettings.config`) เก็บ config ทั้งหมด
- Singleton pattern: 1 row ใน settings table
