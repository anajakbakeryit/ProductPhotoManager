# ULTRAPLAN: แผนพัฒนา ProductPhotoManager

> แผนปรับปรุงแบบครบวงจร จากการตรวจสอบโค้ดทั้งหมดของ `app.py` (~2937 บรรทัด) สคริปต์เสริม และการตั้งค่า

---

## สารบัญ

1. [สรุปภาพรวม](#สรุปภาพรวม)
2. [การประเมินสถานะปัจจุบัน](#การประเมินสถานะปัจจุบัน)
3. [เฟส 1: แก้ไขปัญหาเร่งด่วน](#เฟส-1-แก้ไขปัญหาเร่งด่วน--ความเสถียร)
4. [เฟส 2: ปรับโครงสร้างสถาปัตยกรรม](#เฟส-2-ปรับโครงสร้างสถาปัตยกรรม)
5. [เฟส 3: ความแข็งแกร่งและคุณภาพ](#เฟส-3-ความแข็งแกร่งและคุณภาพ)
6. [เฟส 4: ฟีเจอร์และ UX/UI](#เฟส-4-ฟีเจอร์และ-uxui)
7. [เฟส 5: การทดสอบและ CI/CD](#เฟส-5-การทดสอบและ-cicd)
8. [เฟส 6: ประสิทธิภาพและความสมบูรณ์](#เฟส-6-ประสิทธิภาพและความสมบูรณ์)
9. [แผนผังการพึ่งพาและความเสี่ยง](#แผนผังการพึ่งพาและความเสี่ยง)
10. [รายการดำเนินการตามไฟล์](#รายการดำเนินการตามไฟล์)

---

## สรุปภาพรวม

ProductPhotoManager เป็น **แอปเดสก์ท็อปที่มีฟีเจอร์ครบ ใช้งานได้จริง** มี UI/UX ที่ดี, จัดการสี ICC ถูกต้อง, มี 360° viewer ที่ทรงพลัง แต่ทั้งแอปอยู่ในไฟล์เดียว 2937 บรรทัด มีปัญหา god-class, การจัดการ error แบบเงียบ, ช่องโหว่ thread-safety และไม่มี test เลย

**เป้าหมาย**: เปลี่ยนจาก prototype ที่ใช้งานได้ เป็นแอป production-grade ที่ดูแลรักษาง่าย โดยไม่กระทบฟังก์ชันที่มีอยู่

**ขอบเขต**: 6 เฟส เรียงตามผลกระทบและความเสี่ยง

---

## การประเมินสถานะปัจจุบัน

### จุดแข็ง
- ฟีเจอร์ครบถ้วน (สแกนบาร์โค้ด, เลือกมุมถ่าย, หมุน 360, ลายน้ำ, ลบพื้นหลัง)
- จัดการ sRGB ICC profile ถูกต้องเพื่อความแม่นยำของสี
- ทำงานได้ราบรื่นแม้ไม่มี deps ที่ไม่บังคับ (rembg, opencv)
- UI ธีมมืดพร้อมปุ่มลัด (F1-F8, Ctrl+Z)
- บันทึก session อัตโนมัติเพื่อกู้คืนเมื่อแอปค้าง
- ส่งออกหลายขนาด (S/M/L/OG) พร้อม JPEG quality แต่ละระดับ

### จุดอ่อน

| หมวดหมู่ | ความรุนแรง | จำนวน |
|----------|-----------|-------|
| `except Exception: pass` แบบเงียบ | สูง | 10+ จุด |
| Thread safety (state ที่ใช้ร่วมกันไม่มี lock) | สูง | 4 objects |
| God class (`ProductPhotoApp` = 2430 บรรทัด) | สูง | 1 คลาส ผสมหลาย concern |
| หน่วยความจำโตไม่หยุด | ปานกลาง | 3 แหล่ง (log widget, `_processed` set, session cache) |
| ไม่มีการตรวจสอบ input | ปานกลาง | ค่า Config, RGB, นามสกุลไฟล์ |
| Path dev แบบ hardcode (`gen_viewer.py`) | ปานกลาง | 2 path |
| ไม่มี test เลย | สูง | 0 ไฟล์ test |
| ไม่มี type hints | ต่ำ | ทั้งโค้ด |

---

## เฟส 1: แก้ไขปัญหาเร่งด่วน & ความเสถียร

**ลำดับความสำคัญ**: ทันที | **ความเสี่ยง**: ต่ำ | **ผลกระทบ**: สูง

แก้ไขเฉพาะจุดเพื่อเพิ่มความน่าเชื่อถือ โดยไม่เปลี่ยนสถาปัตยกรรม

### 1.1 แทนที่ Exception Handler แบบเงียบ

**ปัญหา**: 10+ จุดกลืน exception ด้วย `except Exception: pass` ทำให้ซ่อน bug และสูญเสียข้อมูล

**ตำแหน่งที่ต้องแก้**:
| บรรทัด | บริบท | วิธีแก้ |
|---------|-------|---------|
| ~106 | Fallback ของ helper function | Log warning + return ค่า default ที่ปลอดภัย |
| ~292-293 | CSV append fallback เป็น full rewrite | Log warning, แจ้งผู้ใช้ |
| ~1173-1174 | ตรวจจับ pixel format ของวิดีโอ | Log + ใช้ default ที่ปลอดภัย (full range) |
| ~1993 | ตัวนับ pipeline pending | Log error, reset ตัวนับ |
| ~2354-2355 | โหลด session state | Log คำเตือนข้อมูลเสียหาย, เสนอ reset |
| ~2401-2402 | วนลูป restore session | Log + ข้ามรายการที่เสียหาย |
| ~2698 | ตรวจสอบ RGB ในตั้งค่า | แสดง validation error ใน UI |
| ~2862 | การดำเนินการไฟล์ใน import | Log + แสดงจำนวน error ให้ผู้ใช้ |

**วิธีดำเนินการ**: แทนที่ `except Exception: pass` ทุกจุดด้วย:
```python
except Exception as e:
    logging.warning(f"[บริบท]: {e}")
    # fallback ที่เหมาะสม
```

### 1.2 เพิ่ม Thread Safety สำหรับ Shared State

**ปัญหา**: หลาย object ถูกเข้าถึงจากทั้ง main thread และ `ImageProcessor` thread โดยไม่มีการ sync

**Shared objects ที่ต้องมี lock**:
- `self.config` dict - อ่านจาก processor (บรรทัด ~318), เขียนจากตั้งค่า (บรรทัด ~2318)
- `self.session_photos` list - แก้ไขจาก processor callback และ main thread
- `self.pipeline_pending` counter - อัปเดตจากทั้งสอง thread
- `self.angle_counters` dict - race condition ถ้ารูปมาพร้อมกัน 2 รูป

**วิธีดำเนินการ**: เพิ่ม `threading.Lock()` สำหรับแต่ละ shared resource:
```python
self._config_lock = threading.Lock()
self._session_lock = threading.Lock()
self._counter_lock = threading.Lock()
```

### 1.3 แก้ Race Condition ของตัวนับบาร์โค้ด

**ปัญหา** (บรรทัด ~2223-2241): ถ้ารูป 2 รูปมาที่มุมเดียวกันก่อนที่ตัวนับจะอัปเดต อาจเกิดชื่อไฟล์ซ้ำ

**วิธีดำเนินการ**: ครอบการอ่าน-เพิ่ม-เขียนตัวนับด้วย `self._counter_lock` และตรวจสอบว่าชื่อไฟล์ไม่ซ้ำก่อนเขียน

### 1.4 ลบ Dev Path ที่ Hardcode

**ปัญหา**: `gen_viewer.py` มี:
```python
base_dir = r"C:\Users\ParkBakery\Desktop\TestOutputFolder\360\box3"
barcode = "box3"
```

**วิธีดำเนินการ**: แปลง `gen_viewer.py` ให้รับ CLI arguments หรือ interactive prompts ลบ path ของผู้ใช้ที่ hardcode ทั้งหมด

### 1.5 จำกัดการเติบโตที่ไม่มีขอบเขต

**ปัญหา**: 3 แหล่งที่ทำให้หน่วยความจำรั่วในเซสชันที่รันนาน

| แหล่ง | ตำแหน่ง | วิธีแก้ |
|--------|---------|---------|
| `self.log_text` (Tkinter Text widget) | Activity log | ตัดเหลือ 500 บรรทัดล่าสุดเมื่อเกิน 1000 |
| `PhotoWatcher._processed` set | File watcher | ลบรายการเก่ากว่า 1 ชม. หรือจำกัดที่ 5000 |
| `self.session_photos` | Session tracking | จำกัดที่ 500 แล้ว (ดี) ตรวจสอบการบังคับใช้ |

---

## เฟส 2: ปรับโครงสร้างสถาปัตยกรรม

**ลำดับความสำคัญ**: สูง | **ความเสี่ยง**: ปานกลาง | **ผลกระทบ**: สูง (การดูแลรักษา)

แยก god class ออกเป็นโมดูลที่เน้นหน้าที่เฉพาะ โดยไม่เปลี่ยนพฤติกรรมภายนอก

### 2.1 โครงสร้างโมดูลเป้าหมาย

```
ProductPhotoManager/
  app.py                    # Entry point + ProductPhotoApp controller (กระชับ)
  core/
    __init__.py
    config.py               # โหลด/ตรวจสอบ/ค่าเริ่มต้น/migration ของ Config
    product_db.py            # คลาส ProductDB (แยกออกมาเหมือนเดิม)
    image_processor.py       # Thread ImageProcessor (แยกออกมาเหมือนเดิม)
    photo_watcher.py         # PhotoWatcher (แยกออกมาเหมือนเดิม)
    session_manager.py       # ลอจิกบันทึก/กู้คืน session
    file_manager.py          # ตั้งชื่อไฟล์, บันทึกหลายขนาด, เครื่องมือ path
  ui/
    __init__.py
    main_window.py           # เลย์เอาต์หน้าต่างหลักและการสร้าง frame
    barcode_panel.py         # UI ป้อนบาร์โค้ด + ค้นหาสินค้า
    angle_panel.py           # ปุ่มเลือกมุม + state
    log_panel.py             # Widget แสดงกิจกรรม
    preview_panel.py         # พื้นที่แสดงตัวอย่างภาพ
    settings_dialog.py       # หน้าต่างตั้งค่า (แยกจาก ~บรรทัด 2450)
    report_dialog.py         # UI สร้างรายงาน
    spin360_dialog.py        # UI โหมด 360 + แยกเฟรมวิดีโอ
  utils/
    __init__.py
    color_profile.py         # แปลง ICC/sRGB (_to_srgb)
    sanitize.py              # _sanitize_barcode และความปลอดภัย path
    viewer_generator.py      # สร้าง 360 HTML viewer
    constants.py             # Color dict C, MULTI_RES ฯลฯ
  config.json
  products.csv
  requirements.txt
```

### 2.2 ลำดับการแยก (เสี่ยงน้อยสุดก่อน)

1. **`core/config.py`** — แยก `DEFAULT_CONFIG`, โหลด/บันทึก/ตรวจสอบ config ข้อมูลล้วน ไม่ต้องพึ่ง UI
2. **`core/product_db.py`** — แยกคลาส `ProductDB` อยู่ตัวเองแล้ว
3. **`core/image_processor.py`** — แยก `ImageProcessor` พึ่งแค่ config + Pillow
4. **`core/photo_watcher.py`** — แยก `PhotoWatcher` พึ่งแค่ watchdog
5. **`utils/constants.py`** — แยก color dict `C`, `MULTI_RES`, `SUPPORTED_EXTENSIONS`
6. **`utils/sanitize.py`** — แยก `_sanitize_barcode()` เป็น pure function
7. **`utils/color_profile.py`** — แยก `_to_srgb()`, `save_multi_resolution()` เป็น pure functions
8. **`utils/viewer_generator.py`** — แยก `_generate_360_viewer()` ใหญ่แต่อยู่ตัวเอง
9. **`ui/settings_dialog.py`** — แยกหน้าต่างตั้งค่า บรรทัดเยอะ (~300 บรรทัด) ขอบเขตชัดเจน
10. **`ui/` panels ที่เหลือ** — แยกทีละ panel ทดสอบหลังแยกแต่ละครั้ง

### 2.3 กฎการ Refactor

- **ห้ามเปลี่ยนพฤติกรรม** ระหว่างแยก — ย้าย + ปรับ import เท่านั้น
- แต่ละการแยกเป็น **commit แยก** เพื่อ revert ง่าย
- `app.py` ยังเป็น controller หลัก import จากโมดูล
- ทดสอบแอปด้วยตนเองหลังแยกแต่ละครั้ง
- คง backward compatibility: `python app.py` ยังเปิดแอปได้

---

## เฟส 3: ความแข็งแกร่งและคุณภาพ

**ลำดับความสำคัญ**: ปานกลาง | **ความเสี่ยง**: ต่ำ | **ผลกระทบ**: ปานกลาง

### 3.1 ตรวจสอบ Schema ของ Config

**ปัญหา**: Config โหลดจาก JSON ไม่มีการตรวจสอบ schema key ที่หายไปจะ fallback เป็นค่า default ที่กระจายอยู่ทั่วโค้ด

**วิธีดำเนินการ**:
- กำหนด schema ของ config (JSON Schema หรือ dataclass พร้อมค่า default)
- ตรวจสอบตอนโหลด merge key ที่หายไปจาก defaults
- เพิ่มเลขเวอร์ชัน config สำหรับ migration ในอนาคต
- Log คำเตือนสำหรับ key ที่ไม่รู้จัก/เลิกใช้

```python
@dataclass
class AppConfig:
    watch_folder: str = ""
    output_folder: str = ""
    watermark_enabled: bool = True
    watermark_opacity: int = 50  # 10-100
    watermark_scale: int = 20   # 5-50
    bg_removal_enabled: bool = True
    # ... ฯลฯ
    
    def validate(self) -> list[str]:
        """คืนรายการ validation errors"""
        errors = []
        if not 10 <= self.watermark_opacity <= 100:
            errors.append(f"watermark_opacity ต้องอยู่ระหว่าง 10-100, ได้ {self.watermark_opacity}")
        return errors
```

### 3.2 เสริมความปลอดภัย Path

**ปัญหา**: `_sanitize_barcode()` บล็อก `..` แต่ไม่ครอบคลุม edge case ทั้งหมดบน Windows

**วิธีดำเนินการ**:
- ใช้ `os.path.normpath()` หลัง sanitize
- ตรวจสอบว่า path ผลลัพธ์อยู่ภายในไดเรกทอรี output (containment check)
- ตรวจสอบความยาว path (Windows MAX_PATH = 260)

### 3.3 ปรับปรุงการแจ้ง Error ให้ผู้ใช้

**ปัญหา**: หลายการดำเนินการล้มเหลวแบบเงียบ หรือ log เฉพาะที่ activity panel

**วิธีดำเนินการ**:
- เพิ่ม `_show_error(title, message)` helper ใช้ `tkinter.messagebox`
- ใช้สำหรับ: config เสียหาย, ดิสก์เต็ม, ไม่มีสิทธิ์, watermark path ไม่ถูกต้อง
- ใช้ activity log สำหรับข้อความแจ้งข่าว ใช้ dialog สำหรับ error ที่ต้องดำเนินการ

### 3.4 ทำความสะอาด Resource

**ปัญหา**: `observer.join()` อาจค้าง; `cv2.VideoCapture` release ไม่ได้ครอบด้วย finally เสมอ

**วิธีดำเนินการ**:
- เพิ่ม timeout ให้ `observer.join(timeout=5)`
- ครอบ `cv2.VideoCapture` ทุกจุดด้วย context manager หรือ try/finally
- เพิ่ม `__del__` หรือ `atexit` handler สำหรับ cleanup

### 3.5 ตรวจสอบ Path ลายน้ำ

**ปัญหา**: ถ้าไฟล์ลายน้ำถูกตั้งค่าแต่ถูกลบจากดิสก์ การประมวลผลจะข้ามลายน้ำแบบเงียบ

**วิธีดำเนินการ**: ตรวจสอบ path ลายน้ำตอนเปิดแอปและก่อนเข้า pipeline แสดงคำเตือนถ้าไฟล์หายไป

---

## เฟส 4: ฟีเจอร์และ UX/UI

**ลำดับความสำคัญ**: ปานกลาง | **ความเสี่ยง**: ต่ำ | **ผลกระทบ**: สูง (ประสบการณ์ผู้ใช้)

> **Design System**: ใช้ Metronic v9.4.6 (Tailwind CSS) เป็น design system หลัก
> อ้างอิง components จาก `c:\Users\Park\Downloads\APP NAIPARK\UI COMPONENT\metronic-v9.4.6\`

### 4.1 Undo หลายระดับ

**ปัจจุบัน**: Undo ได้เฉพาะรูปล่าสุดรูปเดียว

**วิธีดำเนินการ**:
- ใช้ undo stack (deque, สูงสุด 20 รายการ)
- แต่ละรายการ: `{action, source_path, trash_path, metadata}`
- Ctrl+Z ดึงจาก stack; แสดง "ไม่มีอะไรให้เลิกทำ" เมื่อว่าง
- แสดงจำนวน undo ที่เหลือใน status bar

### 4.2 Progress Bar สำหรับแยกเฟรมวิดีโอ

**ปัจจุบัน**: การแยกเฟรม log ความคืบหน้าที่ activity panel แต่ไม่มีตัวบ่งชี้ภาพ

**วิธีดำเนินการ** (อ้างอิง Metronic Progress Bar):
- เพิ่ม `ttk.Progressbar` ใน dialog โหมด 360
- อัปเดตผ่าน `self.after()` จาก worker thread
- แสดง: "กำลังแยกเฟรม 12/24..." พร้อมเปอร์เซ็นต์
- **UI Pattern**: ใช้สไตล์ progress bar จาก Metronic — แถบสีพร้อมข้อความเปอร์เซ็นต์ตรงกลาง, animation แบบ striped ขณะทำงาน

### 4.3 การดำเนินการแบบกลุ่ม (Batch Operations)

**วิธีดำเนินการ** (อ้างอิง Metronic DataTables + user-table):
- เพิ่ม multi-select ในรายการรูป session (Shift+Click, Ctrl+Click)
- ปุ่ม "ลบที่เลือก" / "ย้ายไปถังขยะ"
- ปุ่ม "ประมวลผลใหม่" เพื่อรัน pipeline ซ้ำกับรูปที่เลือก
- **UI Pattern**: ใช้สไตล์ตาราง DataTables จาก Metronic
  - Checkbox ซ้ายสุดของแต่ละแถว + checkbox "เลือกทั้งหมด" ที่ header
  - Toolbar ลอยด้านบนเมื่อเลือกรายการ แสดง: "เลือก 5 รายการ | ลบ | ประมวลผลใหม่ | ยกเลิก"
  - อ้างอิง: `demo1/user-table/app-roster.html`

### 4.4 ค้นหาและกรองรูป

**วิธีดำเนินการ** (อ้างอิง Metronic Search + Filter):
- เพิ่ม search bar เหนือรายการรูป session
- กรองตาม: บาร์โค้ด (substring), มุมถ่าย, ช่วงวันที่
- ไฮไลท์ผลลัพธ์ที่ตรงกัน แสดงจำนวนผลลัพธ์
- **UI Pattern**: ใช้สไตล์ search input จาก Metronic
  - ไอคอนแว่นขยายด้านซ้าย + ปุ่ม X ล้างค่า
  - Dropdown กรองแบบ pill/badge สำหรับ filter ที่ใช้งานอยู่
  - อ้างอิง: `demo1/store-client/search-results-grid.html`

### 4.5 ตัวอย่างลายน้ำแบบ Live Preview

**วิธีดำเนินการ** (อ้างอิง Metronic Image Input + Range Slider):
- ในหน้าตั้งค่า แสดง canvas ตัวอย่างขนาดเล็ก
- อัปเดตแบบ real-time เมื่อผู้ใช้เปลี่ยนความทึบ/ขนาด/ตำแหน่ง
- ใช้ภาพสินค้าตัวอย่างหรือ placeholder
- **UI Pattern**: ใช้สไตล์จาก Metronic
  - Range slider สำหรับความทึบ (10-100%) และขนาด (5-50%) — แสดงค่าปัจจุบันข้างตัวเลื่อน
  - กรอบ preview มีมุมโค้ง (`rounded-lg`) พร้อมเงา (`shadow-sm`)
  - ปุ่ม "รีเซ็ตค่าเริ่มต้น" ใต้ตัวเลื่อน

### 4.6 ตรวจสอบพื้นที่ดิสก์ล่วงหน้า

**วิธีดำเนินการ**:
- ก่อนประมวลผล ตรวจสอบพื้นที่ว่างในไดรฟ์ output
- เตือนถ้าเหลือน้อยกว่า 500 MB
- แสดงการใช้งานปัจจุบันใน status bar
- **UI Pattern**: ใช้ badge สีจาก Metronic
  - เขียว: > 2 GB ว่าง
  - เหลือง: 500 MB - 2 GB
  - แดง: < 500 MB พร้อม warning icon

### 4.7 ปรับปรุง 360 Viewer

**ปัจจุบัน**: Preload ทุกเฟรมตามลำดับ (อาจ 50-100 MB)

**วิธีดำเนินการ** (อ้างอิง Metronic Cards + Dark Theme):
- Lazy-load เฟรมตามต้องการ (เริ่มจากเฟรมปัจจุบัน preload เฟรมข้างเคียง)
- เพิ่ม loading spinner ต่อเฟรม
- คุณภาพแบบ progressive: โหลด S ก่อน อัพเกรดเป็นขนาดที่เลือกเมื่อ interact
- **UI Pattern**: ใช้สไตล์ dark card จาก Metronic สำหรับ viewer container
  - อ้างอิง: `demo1/dashboards/dark-sidebar.html`
  - Loading spinner ใช้ animate-spin ของ Tailwind
  - แถบเลือกขนาด (S/M/L/OG) ใช้ button group แบบ pill
  - ปุ่มควบคุม (เล่น/หยุด/ซ้าย/ขวา) จัดเรียงแบบ icon toolbar

### 4.8 หน้าตั้งค่าแบบ Tabs (ใหม่)

**ปัจจุบัน**: หน้าตั้งค่าเป็น dialog ยาวเลื่อนลง

**วิธีดำเนินการ** (อ้างอิง Metronic Tabs + Account Settings):
- แบ่งตั้งค่าเป็น tabs: **ทั่วไป** | **โฟลเดอร์** | **ลายน้ำ** | **การประมวลผล** | **ขั้นสูง**
- **UI Pattern**: ใช้สไตล์ tabs จาก Metronic
  - อ้างอิง: `demo1/account/appearance.html`, `demo1/account/notifications.html`
  - แท็บด้านบนพร้อมไอคอน + ข้อความ
  - แต่ละ tab เป็น card แยก มีหัวข้อย่อย + คำอธิบาย
  - ปุ่ม "บันทึก" และ "ยกเลิก" อยู่ด้านล่างตลอด (sticky footer)

### 4.9 Dashboard สรุปภาพรวม (ใหม่)

**วิธีดำเนินการ** (อ้างอิง Metronic Dashboard):
- เพิ่มหน้า dashboard แสดงสถิติภาพรวม
- **UI Pattern**: ใช้สไตล์ dashboard cards จาก Metronic
  - อ้างอิง: `demo1/index.html` (dashboard หลัก)
  - Card สถิติ 4 ใบ: จำนวนรูปวันนี้ | รูปทั้งหมด | บาร์โค้ดที่ถ่าย | พื้นที่ดิสก์
  - กราฟแนวโน้ม (ApexCharts) — จำนวนรูปต่อวัน/สัปดาห์
  - รายการ activity ล่าสุดแบบ timeline

### 4.10 Dropzone สำหรับนำเข้ารูป (ใหม่)

**วิธีดำเนินการ** (อ้างอิง Metronic Dropzone):
- เพิ่ม drag & drop zone สำหรับนำเข้ารูปเข้า pipeline ด้วยตนเอง
- **UI Pattern**: ใช้สไตล์ Dropzone จาก Metronic
  - กรอบเส้นประ + ไอคอนอัปโหลด + ข้อความ "ลากไฟล์มาวางที่นี่ หรือคลิกเพื่อเลือก"
  - แสดง thumbnail ของไฟล์ที่เลือกก่อนนำเข้า
  - Progress bar ขณะประมวลผลแต่ละไฟล์

### 4.11 รายงานแบบ HTML (ใหม่)

**ปัจจุบัน**: รายงานเป็นข้อความธรรมดา

**วิธีดำเนินการ** (อ้างอิง Metronic Tables + Cards):
- สร้างรายงาน HTML สวยงามพร้อมสไตล์ Metronic
- **UI Pattern**:
  - อ้างอิง: `demo1/store-client/my-orders.html`, `demo1/store-client/order-receipt.html`
  - ตารางสรุปยอดรูปตามบาร์โค้ด พร้อม thumbnail
  - สรุปสถิติด้านบน (cards) — จำนวนรูป, จำนวน SKU, ขนาดไฟล์รวม
  - ปุ่ม export เป็น PDF / พิมพ์
  - รองรับ dark/light theme ผ่าน CSS variables ของ Metronic

---

## เฟส 5: การทดสอบและ CI/CD

**ลำดับความสำคัญ**: สูง | **ความเสี่ยง**: ต่ำ | **ผลกระทบ**: สูง (ระยะยาว)

### 5.1 Unit Tests (เป้าหมายหลัก)

สร้างไดเรกทอรี `tests/` ด้วย pytest:

```
tests/
  __init__.py
  test_sanitize.py          # Edge case ของการ sanitize บาร์โค้ด
  test_product_db.py        # การดำเนินการ CRUD กับ CSV
  test_config.py            # ตรวจสอบ config, ค่า default, migration
  test_color_profile.py     # ความถูกต้องของการแปลง sRGB
  test_file_naming.py       # การสร้างชื่อไฟล์, จัดการ collision
  test_multi_resolution.py  # ลอจิก resize, ค่าคุณภาพ
  test_viewer_generator.py  # ตรวจสอบโครงสร้าง HTML output
```

**เป้าหมาย: 80%+ coverage สำหรับ `core/` และ `utils/`**

### 5.2 Integration Tests

```
tests/
  test_image_processor.py   # Pipeline ประมวลผลแบบ end-to-end
  test_photo_watcher.py     # ตรวจจับไฟล์ + trigger การประมวลผล
  test_session_manager.py   # บันทึก/กู้คืน round-trip
```

### 5.3 Test Fixtures

- สร้าง `tests/fixtures/` ประกอบด้วย:
  - ภาพทดสอบขนาดเล็ก (JPEG, PNG, หลาย ICC profiles)
  - `config.json` หลายรูปแบบ (ถูกต้อง, key หาย, เสียหาย)
  - `products.csv` ตัวอย่าง (ปกติ, ว่าง, ผิดรูปแบบ)
  - ไฟล์วิดีโอตัวอย่าง (สั้น, 2-3 วินาที, สำหรับแยกเฟรม 360)

### 5.4 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest  # แพลตฟอร์มเป้าหมายหลัก
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=core --cov=utils --cov-report=xml
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check .
```

### 5.5 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## เฟส 6: ประสิทธิภาพและความสมบูรณ์

**ลำดับความสำคัญ**: ต่ำ | **ความเสี่ยง**: ต่ำ | **ผลกระทบ**: ปานกลาง

### 6.1 เพิ่มประสิทธิภาพการบันทึกหลายขนาด

**ปัญหา**: `save_multi_resolution()` แปลงเป็น RGB เสมอแม้ไม่จำเป็น

**วิธีดำเนินการ**: ตรวจสอบก่อนว่าต้อง resize หรือไม่ ข้ามการแปลงสำหรับภาพที่อยู่ใน mode เป้าหมายแล้ว

### 6.2 เพิ่มประสิทธิภาพการอัปเดตปุ่มมุม

**ปัญหา**: ทุกครั้งที่เลือกมุมจะ scan ปุ่มทั้ง 8 ปุ่มแบบเชิงเส้น

**วิธีดำเนินการ**: สร้าง lookup dict `angle_id -> button_widget` ตอน init ได้ O(1) แทน O(n)

### 6.3 เพิ่มประสิทธิภาพการสร้างรายงาน

**ปัญหา**: `export_report()` scan ทั้งไดเรกทอรี output ต่อบาร์โค้ด

**วิธีดำเนินการ**: Scan ไดเรกทอรีรอบเดียวพร้อมสะสมใน dictionary ตามบาร์โค้ด

### 6.4 Lazy Loading เฟรม 360 ใน Viewer

**ปัญหา**: HTML viewer preload ทุกเฟรม (50-100 MB)

**วิธีดำเนินการ**: โหลดขนาด S ก่อน lazy-upgrade เป็นขนาดที่เลือก แสดง loading indicator

### 6.5 เพิ่ม Type Hints

**วิธีดำเนินการ**: เพิ่ม type hints ทีละส่วน เริ่มจาก:
1. Public APIs ของโมดูลที่แยกออกมา
2. Config dataclass
3. Core utility functions
4. UI callback signatures

ใช้ `mypy --strict` เป็นเป้าหมาย

### 6.6 Logging ลงไฟล์

**วิธีดำเนินการ**:
- เพิ่ม `logging.FileHandler` พร้อม rotation (5 MB, เก็บ 3 ไฟล์)
- ใส่ timestamps, ชื่อ thread, ระดับ log
- UI log panel อ่านจาก logger เดียวกัน
- ผู้ใช้สามารถแนบไฟล์ log เมื่อรายงาน bug

---

## แผนผังการพึ่งพาและความเสี่ยง

### การพึ่งพาระหว่างเฟส

```
เฟส 1 (แก้ไขเร่งด่วน) ─── ไม่มี dependency, เริ่มได้ทันที
     │
เฟส 2 (สถาปัตยกรรม) ───── ต้องเสร็จเฟส 1 ก่อน
     │
     ├── เฟส 3 (ความแข็งแกร่ง) ── เริ่มได้ระหว่างเฟส 2
     │
     ├── เฟส 4 (ฟีเจอร์/UX/UI) ── ต้องใช้โครงสร้างโมดูลจากเฟส 2
     │
     └── เฟส 5 (การทดสอบ) ─────── เริ่มได้ระหว่างเฟส 2 (test โมดูลที่แยกแล้ว)
              │
         เฟส 6 (ประสิทธิภาพ) ──── ต้องเสร็จเฟส 2 + เฟส 5
```

### การประเมินความเสี่ยง

| เฟส | ความเสี่ยง | การบรรเทา |
|-----|-----------|----------|
| เฟส 1 | ต่ำ - แก้เฉพาะจุด | แต่ละจุดแก้ไขอิสระ revert ง่าย |
| เฟส 2 | ปานกลาง - เปลี่ยนโครงสร้าง | แยกทีละโมดูล commit ต่อการแยก ทดสอบด้วยตนเอง |
| เฟส 3 | ต่ำ - เพิ่มเข้ามา | เพิ่มชั้นตรวจสอบใหม่ ไม่เปลี่ยนพฤติกรรมเดิม |
| เฟส 4 | ต่ำ - ฟีเจอร์ใหม่ | ใช้ feature flag ส่งมอบทีละส่วนได้ |
| เฟส 5 | ต่ำ - เพิ่มเข้ามา | test ไม่แก้ไขโค้ด production |
| เฟส 6 | ต่ำ - ปรับแต่ง | วัดผลก่อน/หลังได้ rollback ง่าย |

---

## รายการดำเนินการตามไฟล์

### `app.py` (2937 บรรทัด)

| บรรทัด | ส่วนประกอบ | เฟส | การดำเนินการ |
|--------|-----------|-----|-------------|
| 1-50 | Imports & globals | เฟส 2 | ย้ายไป `utils/constants.py` |
| 51-100 | Helper functions | เฟส 2 | ย้ายไป `utils/sanitize.py`, `utils/color_profile.py` |
| 100-170 | `save_multi_resolution()` | เฟส 2, 6 | ย้ายไป `core/file_manager.py`, ปรับแต่ง |
| 172-248 | `DEFAULT_CONFIG` | เฟส 2, 3 | ย้ายไป `core/config.py`, เพิ่ม schema validation |
| 250-300 | `ProductDB` | เฟส 2 | ย้ายไป `core/product_db.py` (เหมือนเดิม) |
| 306-466 | `ImageProcessor` | เฟส 1, 2 | แก้ thread safety (เฟส 1), ย้ายไป `core/image_processor.py` (เฟส 2) |
| 472-501 | `PhotoWatcher` | เฟส 1, 2 | จำกัด `_processed` set (เฟส 1), ย้ายไป `core/photo_watcher.py` (เฟส 2) |
| 507-900 | App init + UI layout | เฟส 2 | ย้ายสร้าง UI ไป `ui/main_window.py` |
| 900-1100 | ลอจิกบาร์โค้ด/มุม | เฟส 2 | ย้ายไป `ui/barcode_panel.py`, `ui/angle_panel.py` |
| 1100-1400 | แยกเฟรมวิดีโอ/360 | เฟส 1, 2, 4 | แก้ silent errors (เฟส 1), ย้ายไป `ui/spin360_dialog.py` (เฟส 2), เพิ่ม progress bar (เฟส 4) |
| 1400-1700 | สร้าง 360 viewer | เฟส 2 | ย้ายไป `utils/viewer_generator.py` |
| 1700-2000 | Pipeline ประมวลผลรูป | เฟส 1 | แก้ race conditions, เพิ่ม locks |
| 2000-2150 | จัดการ file watcher | เฟส 1 | เพิ่ม timeout ให้ observer.join |
| 2150-2450 | จัดการ session | เฟส 1, 2 | แก้ silent load errors (เฟส 1), ย้ายไป `core/session_manager.py` (เฟส 2) |
| 2450-2750 | Dialog ตั้งค่า | เฟส 2, 3 | ย้ายไป `ui/settings_dialog.py` (เฟส 2), เพิ่ม validation (เฟส 3) |
| 2750-2937 | รายงาน/นำเข้า/ส่งออก | เฟส 2 | ย้ายไป `ui/report_dialog.py` |

### `gen_viewer.py` (14770 bytes)

| การดำเนินการ | เฟส | รายละเอียด |
|-------------|-----|-----------|
| ลบ path ที่ hardcode | เฟส 1 | แทนที่ด้วย CLI args (`argparse`) |
| ลดความซ้ำซ้อนกับ app.py | เฟส 2 | ทั้งสองควรใช้ `utils/viewer_generator.py` |
| เพิ่ม `--help` | เฟส 1 | ทำให้เป็น CLI tool ที่สมบูรณ์ |

### `config.json` (1593 bytes)

| การดำเนินการ | เฟส | รายละเอียด |
|-------------|-----|-----------|
| เพิ่ม `config_version` | เฟส 3 | สำหรับ migration ในอนาคต |
| Document ทุก field | เฟส 3 | เพิ่ม `config.schema.json` |
| ตรวจสอบตอนโหลด | เฟส 3 | ปฏิเสธค่าไม่ถูกต้องพร้อมแจ้งผู้ใช้ |

### `requirements.txt` (97 bytes)

| การดำเนินการ | เฟส | รายละเอียด |
|-------------|-----|-----------|
| กำหนดขอบบนของ numpy | เฟส 1 | `numpy>=1.24,<2.0` แทน `numpy<2` |
| เพิ่มส่วน dev dependencies | เฟส 5 | `requirements-dev.txt` มี pytest, ruff, mypy |
| เพิ่ม markers สำหรับ deps ที่ไม่บังคับ | เฟส 3 | Document ว่าตัวไหนไม่บังคับ |

### `build.bat` / `installer.iss`

| การดำเนินการ | เฟส | รายละเอียด |
|-------------|-----|-----------|
| อัปเดตสำหรับโครงสร้างหลายไฟล์ | เฟส 2 | หลัง refactor สถาปัตยกรรม อัปเดต PyInstaller spec |
| เพิ่ม version stamping | เฟส 5 | ฝัง git tag/hash ลงใน build |

---

## ทำได้เลยวันนี้ (Quick Wins)

สิ่งเหล่านี้ใช้ความพยายามน้อยแต่ได้ผลทันที:

1. **แทนที่ `except Exception: pass`** ด้วย logged warnings (~30 นาที)
2. **เพิ่ม `threading.Lock()`** ที่จุดเข้าถึง shared state (~20 นาที)
3. **จำกัด log widget** ที่ 500 บรรทัด (~5 นาที)
4. **แก้ `gen_viewer.py`** ลบ path ที่ hardcode ใช้ `argparse` (~15 นาที)
5. **กำหนดขอบเขต numpy** ใน requirements.txt (~2 นาที)
6. **เพิ่ม `.editorconfig`** สำหรับการจัดรูปแบบที่สม่ำเสมอ (~5 นาที)

---

## ตัวชี้วัดความสำเร็จ

| ตัวชี้วัด | ปัจจุบัน | เป้าหมายเฟส 2 | เป้าหมายเฟส 6 |
|----------|---------|--------------|--------------|
| ไฟล์ใหญ่ที่สุด (บรรทัด) | 2937 | < 500 | < 300 |
| คลาสใหญ่ที่สุด (บรรทัด) | 2430 | < 400 | < 200 |
| Silent exception handlers | 10+ | 0 | 0 |
| Test coverage | 0% | 50% | 80%+ |
| Thread-safe shared objects | 0/4 | 4/4 | 4/4 |
| Type hint coverage | 0% | 30% | 70%+ |
| CI pipeline | ไม่มี | Lint + test | Lint + test + build |

---

## Metronic UI Components อ้างอิง

| Component | ใช้ในเฟส | ตัวอย่างจาก Metronic |
|-----------|---------|---------------------|
| DataTables + Checkbox | 4.3 Batch Operations | `demo1/user-table/app-roster.html` |
| Search + Filter | 4.4 ค้นหารูป | `demo1/store-client/search-results-grid.html` |
| Range Slider + Image Input | 4.5 Live Preview ลายน้ำ | Metronic Range Slider component |
| Progress Bar | 4.2 แยกเฟรมวิดีโอ | Metronic Progress component |
| Dashboard Cards + ApexCharts | 4.9 Dashboard สรุป | `demo1/index.html` |
| Dropzone | 4.10 นำเข้ารูป | Metronic Dropzone component |
| Tabs + Account Settings | 4.8 หน้าตั้งค่า | `demo1/account/appearance.html` |
| Cards + Tables | 4.11 รายงาน HTML | `demo1/store-client/my-orders.html` |
| Dark Sidebar Layout | 4.7 360 Viewer | `demo1/dashboards/dark-sidebar.html` |
| Badge / Pill | 4.6 สถานะดิสก์ | Metronic Badge component |

---

*สร้างจากการตรวจสอบโค้ดทั้งหมดเมื่อ 2026-04-09 | อัปเดต UX/UI ด้วย Metronic v9.4.6 เมื่อ 2026-04-10*
