# ProductPhotoManager

## Project Overview
Desktop application (Python/Tkinter) for managing product photography workflows in a studio environment. Scan barcode → select angle → auto-rename + post-process incoming photos from a camera's watch folder.

## Tech Stack
- **Language**: Python 3
- **GUI**: Tkinter (single-file app: `app.py` ~2900 lines)
- **Image Processing**: Pillow, rembg (background removal), OpenCV (video frame extraction)
- **File Watching**: watchdog
- **ML Runtime**: onnxruntime (used by rembg)
- **Build**: PyInstaller → EXE, Inno Setup → Windows installer

## Architecture
Single-file application (`app.py`) with these main classes:
- **`ProductPhotoApp(tk.Tk)`** — Main GUI application, handles UI, barcode scanning, angle selection, file management
- **`ImageProcessor(threading.Thread)`** — Background thread for post-processing pipeline (remove BG, add watermark)
- **`PhotoWatcher(FileSystemEventHandler)`** — Watches a folder for new image files from camera
- **`ProductDB`** — Simple CSV-based product database (`products.csv`)

### Key Helper Functions
- `_sanitize_barcode()` — Sanitizes barcode input for safe filesystem use
- `_to_srgb()` — ICC color profile conversion to sRGB
- `save_multi_resolution()` — Saves image in S (480px) / M (800px) / L (1200px) / OG sizes

## Output Folder Structure
```
output_folder/
  original/{barcode}/S|M|L|OG/         # Raw originals in 4 sizes
  cutout/{barcode}/S|M|L|OG/           # Background-removed (PNG)
  watermarked/{barcode}/S|M|L|OG/      # Cutout + watermark (JPG)
  watermarked_original/{barcode}/S|M|L|OG/  # Original + watermark (JPG)
  360/{barcode}/S|M|L|OG/              # 360 spin frames + viewer.html
  _trash/{barcode}/                    # Undo destination
```

## File Naming Convention
- Normal: `{barcode}_{angle}_{count:02d}.ext` (e.g., `SKU001_front_01.jpg`)
- 360 mode: `{barcode}_360_{frame:02d}.ext`
- Multi-res suffix: `{base}_{S|M|L|OG}.jpg`

## Configuration
- **`config.json`** — All app settings (folders, watermark, pipeline toggles, angles, extensions)
- **`products.csv`** — Product database (barcode, name, category, note)
- **`session_state.json`** — Auto-saved session for crash recovery (runtime, not committed)

## Key Keyboard Shortcuts
- `F1`-`F8` — Select shooting angle
- `Ctrl+Z` — Undo last photo
- `Enter` — Confirm barcode scan

## Build & Distribution
```bash
# Build EXE (requires PyInstaller)
build.bat

# Build Windows installer (requires Inno Setup 6)
build_installer.bat
```
Output: `dist/ProductPhotoManager-Portable.zip` or `dist/ProductPhotoManager-Setup.exe`

## UI/UX Design Rules
**เมื่อแก้ไข UI/UX ต้องใช้ components จากโฟลเดอร์ `UI COMPONENT` เท่านั้น**

UI Component source: `c:\Users\Park\Downloads\APP NAIPARK\UI COMPONENT\metronic-v9.4.6\`

ใช้ **Metronic v9.4.6** (Tailwind CSS) เป็น design system หลัก:
- **CSS Framework**: Tailwind CSS v4 + @keenthemes/ktui v1.1.0
- **Color Tokens**: CSS variables (`--primary`, `--background`, `--foreground`, `--accent`, `--border`, etc.) รองรับ light/dark theme
- **Components ที่มี**: Menu, Dropzone, Date Picker, Color Picker, Sortable, DataTables, ApexCharts, FullCalendar, Image Input, Rating, Range Slider
- **Typography**: Tailwind default + custom sizes (text-2sm, text-2xs)
- **Radius**: 0.5rem base + sm/md/lg/xl variants
- **Available packages**: HTML demos, HTML starter kit, React demos (Vite/Next.js), React starter kit, Next.js landings, Figma file
- **Key dependencies**: @popperjs/core, apexcharts, tinymce, fullcalendar, leaflet, datatables.net, axios

เมื่อต้องสร้างหรือแก้ไข UI (เช่น 360 viewer HTML, report pages, settings dialog) ให้ดึง styles/patterns จาก Metronic เป็นหลัก

## Language / UX Rules
- **UI ทั้งหมดต้องเป็นภาษาไทยเท่านั้น** — ปุ่ม, ป้ายกำกับ, ข้อความ dialog, ข้อความ log, สถานะ ทุกอย่างต้องเป็นภาษาไทย
- ข้อยกเว้น: ชื่อเทคนิค (rembg, S/M/L/OG, Multi-Res), keyboard shortcuts (F1-F8, Ctrl+Z), ชื่อโฟลเดอร์ output (original/, cutout/, watermarked/)
- เมื่อเพิ่มหรือแก้ไข UI text ใดๆ ต้องใช้ภาษาไทยเสมอ
- ออกแบบ UI ให้เข้าใจง่าย user-friendly — ข้อความสั้นกระชับ สื่อความหมายชัดเจน

## Development Notes
- All image output embeds sRGB ICC profile for color accuracy
- Video→360 handles limited color range (16-235) from H.264/H.265 cameras with YCrCb normalization
- rembg and opencv-python are optional — app runs without them but disables related features
- The 360 viewer HTML is self-contained with embedded JavaScript (canvas-based, supports drag/inertia/pinch-zoom/multi-resolution switching)
- UI uses a dark theme with color constants defined in the `C` dict
- Thai-only UI labels (`label_th` field in angle config for button text)

## Common Tasks
- **Add new angle**: Add entry to `angles` array in `config.json` and `DEFAULT_CONFIG` in `app.py`
- **Change output resolutions**: Modify `MULTI_RES` dict in `app.py`
- **Modify watermark behavior**: See `ImageProcessor._add_watermark()` and `_process()` methods
- **Edit 360 viewer template**: Inline HTML in `_generate_360_viewer()` method (~line 1584)
