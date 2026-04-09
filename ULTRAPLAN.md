# ULTRAPLAN: ProductPhotoManager Development Roadmap

> Comprehensive improvement plan based on full codebase audit of `app.py` (~2937 lines), supporting scripts, and configuration.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Phase 1: Critical Fixes](#phase-1-critical-fixes--stability)
4. [Phase 2: Architecture Refactor](#phase-2-architecture-refactor)
5. [Phase 3: Robustness & Quality](#phase-3-robustness--quality)
6. [Phase 4: Features & UX](#phase-4-features--ux)
7. [Phase 5: Testing & CI/CD](#phase-5-testing--cicd)
8. [Phase 6: Performance & Polish](#phase-6-performance--polish)
9. [Dependency & Risk Matrix](#dependency--risk-matrix)
10. [File-by-File Action Items](#file-by-file-action-items)

---

## Executive Summary

ProductPhotoManager is a **feature-rich, functional desktop app** with solid UI/UX, proper ICC color management, and a powerful 360-degree viewer. However, the entire application lives in a single 2937-line file with a god-class pattern, silent error handling, thread-safety gaps, and zero test coverage.

**Goal**: Transform from a working prototype into a production-grade, maintainable application without disrupting existing functionality.

**Estimated scope**: 6 phases, ordered by impact and risk.

---

## Current State Assessment

### Strengths
- Comprehensive feature set (barcode scan, angle management, 360 spin, watermark, background removal)
- Proper sRGB ICC profile management for color accuracy
- Graceful degradation when optional deps (rembg, opencv) are missing
- Dark-themed UI with keyboard shortcuts (F1-F8, Ctrl+Z)
- Session auto-save/restore for crash recovery
- Multi-resolution output (S/M/L/OG) with quality-per-tier JPEG encoding

### Weaknesses

| Category | Severity | Count |
|----------|----------|-------|
| Silent `except Exception: pass` | HIGH | 10+ locations |
| Thread safety (shared state without locks) | HIGH | 4 shared objects |
| God class (`ProductPhotoApp` = 2430 lines) | HIGH | 1 class, mixed concerns |
| Unbounded memory growth | MEDIUM | 3 sources (log widget, `_processed` set, session cache) |
| Missing input validation | MEDIUM | Config values, RGB, extensions |
| Hardcoded dev paths (`gen_viewer.py`) | MEDIUM | 2 hardcoded paths |
| Zero test coverage | HIGH | 0 test files |
| No type hints | LOW | Entire codebase |

---

## Phase 1: Critical Fixes & Stability

**Priority**: Immediate | **Risk**: Low | **Impact**: High

These are targeted fixes that improve reliability without changing architecture.

### 1.1 Replace Silent Exception Handlers

**Problem**: 10+ locations swallow exceptions with `except Exception: pass`, hiding bugs and data loss.

**Locations to fix**:
| Line(s) | Context | Fix |
|---------|---------|-----|
| ~106 | Helper function fallback | Log warning + return safe default |
| ~292-293 | CSV append fallback to full rewrite | Log warning, notify user |
| ~1173-1174 | Video pixel format detection | Log + use safe default (full range) |
| ~1993 | Pipeline pending counter | Log error, reset counter |
| ~2354-2355 | Session state load | Log corruption warning, offer reset |
| ~2401-2402 | Session restore iteration | Log + skip corrupt entry |
| ~2698 | Settings RGB validation | Show validation error in UI |
| ~2862 | File operation in import | Log + show error count to user |

**Action**: Replace each `except Exception: pass` with:
```python
except Exception as e:
    logging.warning(f"[context]: {e}")
    # appropriate fallback
```

### 1.2 Add Thread Safety for Shared State

**Problem**: Multiple objects accessed from both main thread and `ImageProcessor` thread without synchronization.

**Shared objects needing locks**:
- `self.config` dict - read by processor (line ~318), written by settings (line ~2318)
- `self.session_photos` list - modified from processor callback and main thread
- `self.pipeline_pending` counter - updated from both threads
- `self.angle_counters` dict - race condition if two photos arrive simultaneously

**Action**: Add `threading.Lock()` for each shared resource:
```python
self._config_lock = threading.Lock()
self._session_lock = threading.Lock()
self._counter_lock = threading.Lock()
```

### 1.3 Fix Barcode Counter Race Condition

**Problem** (lines ~2223-2241): If two photos arrive for the same angle before the counter updates, duplicate filenames are possible.

**Action**: Wrap counter read-increment-write in `self._counter_lock` and verify filename uniqueness before writing.

### 1.4 Remove Hardcoded Dev Paths

**Problem**: `gen_viewer.py` contains:
```python
base_dir = r"C:\Users\ParkBakery\Desktop\TestOutputFolder\360\box3"
barcode = "box3"
```

**Action**: Convert `gen_viewer.py` to accept CLI arguments or interactive prompts. Remove all hardcoded user paths.

### 1.5 Cap Unbounded Growth

**Problem**: Three memory leak sources in long-running sessions.

| Source | Location | Fix |
|--------|----------|-----|
| `self.log_text` (Tkinter Text widget) | Activity log | Trim to last 500 lines when exceeding 1000 |
| `PhotoWatcher._processed` set | File watcher | Clear entries older than 1 hour, or cap at 5000 |
| `self.session_photos` | Session tracking | Already capped at 500 (good), verify enforcement |

---

## Phase 2: Architecture Refactor

**Priority**: High | **Risk**: Medium | **Impact**: High (maintainability)

Break the god class into focused modules without changing external behavior.

### 2.1 Extract Module Structure

**Target layout**:
```
ProductPhotoManager/
  app.py                    # Entry point + ProductPhotoApp controller (slim)
  core/
    __init__.py
    config.py               # Config loading, validation, defaults, migration
    product_db.py            # ProductDB class (extracted as-is)
    image_processor.py       # ImageProcessor thread (extracted as-is)
    photo_watcher.py         # PhotoWatcher (extracted as-is)
    session_manager.py       # Session save/restore logic
    file_manager.py          # File naming, multi-res saving, path utilities
  ui/
    __init__.py
    main_window.py           # Main window layout and frame construction
    barcode_panel.py         # Barcode input + product lookup UI
    angle_panel.py           # Angle selection buttons + state
    log_panel.py             # Activity log widget
    preview_panel.py         # Photo preview area
    settings_dialog.py       # Settings window (extracted from ~line 2450)
    report_dialog.py         # Report generation UI
    spin360_dialog.py        # 360 mode UI + video extraction
  utils/
    __init__.py
    color_profile.py         # ICC/sRGB conversion (_to_srgb)
    sanitize.py              # _sanitize_barcode and path safety
    viewer_generator.py      # 360 HTML viewer generation
    constants.py             # Color dict C, MULTI_RES, etc.
  config.json
  products.csv
  requirements.txt
```

### 2.2 Extraction Order (Lowest Risk First)

1. **`core/config.py`** - Extract `DEFAULT_CONFIG`, config load/save, validation. Pure data, no UI deps.
2. **`core/product_db.py`** - Extract `ProductDB` class. Already self-contained.
3. **`core/image_processor.py`** - Extract `ImageProcessor`. Only depends on config + Pillow.
4. **`core/photo_watcher.py`** - Extract `PhotoWatcher`. Only depends on watchdog.
5. **`utils/constants.py`** - Extract color dict `C`, `MULTI_RES`, `SUPPORTED_EXTENSIONS`.
6. **`utils/sanitize.py`** - Extract `_sanitize_barcode()`. Pure function.
7. **`utils/color_profile.py`** - Extract `_to_srgb()`, `save_multi_resolution()`. Pure functions.
8. **`utils/viewer_generator.py`** - Extract `_generate_360_viewer()`. Large but self-contained.
9. **`ui/settings_dialog.py`** - Extract settings window. High line count (~300 lines), clear boundary.
10. **`ui/` remaining panels** - Extract one panel at a time, testing after each.

### 2.3 Refactoring Rules

- **No behavior changes** during extraction - pure move + import rewiring
- Each extraction is a **separate commit** for easy revert
- `app.py` stays as the controller, importing from modules
- Run the app manually after each extraction to verify nothing broke
- Keep backward compatibility: `python app.py` still launches the app

---

## Phase 3: Robustness & Quality

**Priority**: Medium | **Risk**: Low | **Impact**: Medium

### 3.1 Config Schema Validation

**Problem**: Config loaded from JSON with no schema validation. Missing keys silently fall back to defaults scattered across the code.

**Action**:
- Define a config schema (JSON Schema or dataclass with defaults)
- Validate on load, merge missing keys from defaults
- Add config version field for future migration support
- Log warnings for unknown/deprecated keys

```python
@dataclass
class AppConfig:
    watch_folder: str = ""
    output_folder: str = ""
    watermark_enabled: bool = True
    watermark_opacity: int = 50  # 10-100
    watermark_scale: int = 20   # 5-50
    bg_removal_enabled: bool = True
    # ... etc
    
    def validate(self) -> list[str]:
        """Return list of validation errors."""
        errors = []
        if not 10 <= self.watermark_opacity <= 100:
            errors.append(f"watermark_opacity must be 10-100, got {self.watermark_opacity}")
        return errors
```

### 3.2 Path Safety Hardening

**Problem**: `_sanitize_barcode()` blocks `..` but doesn't handle all edge cases on Windows.

**Action**:
- Apply `os.path.normpath()` after sanitization
- Verify result path is within the output directory (containment check)
- Add path length validation (Windows MAX_PATH = 260)

### 3.3 Improve Error Feedback to User

**Problem**: Many operations fail silently or only log to the activity panel.

**Action**:
- Add `_show_error(title, message)` helper using `tkinter.messagebox`
- Use for: config corruption, disk full, permission denied, invalid watermark path
- Keep activity log for informational messages, use dialogs for errors requiring action

### 3.4 Resource Cleanup

**Problem**: `observer.join()` may hang; `cv2.VideoCapture` release not always wrapped in finally.

**Action**:
- Add timeout to `observer.join(timeout=5)`
- Wrap all `cv2.VideoCapture` usage in context manager or try/finally
- Add `__del__` or `atexit` handler for cleanup

### 3.5 Watermark Path Validation

**Problem**: If watermark file is configured but deleted from disk, processing silently skips watermarking.

**Action**: Check watermark path on app start and when entering processing pipeline. Show warning if file is missing.

---

## Phase 4: Features & UX

**Priority**: Medium | **Risk**: Low | **Impact**: High (user experience)

### 4.1 Multi-Level Undo

**Current**: Only the last photo can be undone.

**Action**:
- Maintain an undo stack (deque, max 20 items)
- Each entry: `{action, source_path, trash_path, metadata}`
- Ctrl+Z pops from stack; show "Nothing to undo" when empty
- Display undo count in status bar

### 4.2 Progress Bar for Video Extraction

**Current**: Frame extraction logs progress to activity panel but has no visual indicator.

**Action**:
- Add `ttk.Progressbar` to 360 mode dialog
- Update via `self.after()` from worker thread
- Show: "Extracting frame 12/24..." with percentage

### 4.3 Batch Operations

**Action**:
- Add multi-select to session photo list (Shift+Click, Ctrl+Click)
- "Delete Selected" / "Move Selected to Trash" buttons
- "Re-process Selected" to re-run pipeline on existing photos

### 4.4 Photo Search & Filter

**Action**:
- Add search bar above session photo list
- Filter by: barcode (substring), angle, date range
- Highlight matches, show result count

### 4.5 Watermark Live Preview

**Action**:
- In settings dialog, show a small preview canvas
- Update in real-time as user changes opacity/scale/position
- Use a sample product image or placeholder

### 4.6 Disk Space Pre-Check

**Action**:
- Before processing, check available disk space on output drive
- Warn if < 500 MB remaining
- Show current usage in status bar

### 4.7 Improved 360 Viewer

**Current**: Preloads all frames sequentially (can be 50-100 MB).

**Action**:
- Lazy-load frames on demand (start with current frame, preload adjacent)
- Add loading spinner per frame
- Progressive quality: load S first, upgrade to selected resolution on interaction

---

## Phase 5: Testing & CI/CD

**Priority**: High | **Risk**: Low | **Impact**: High (long-term)

### 5.1 Unit Tests (Priority Targets)

Create `tests/` directory with pytest:

```
tests/
  __init__.py
  test_sanitize.py          # Barcode sanitization edge cases
  test_product_db.py        # CSV CRUD operations
  test_config.py            # Config validation, defaults, migration
  test_color_profile.py     # sRGB conversion correctness
  test_file_naming.py       # Filename generation, collision handling
  test_multi_resolution.py  # Resize logic, quality settings
  test_viewer_generator.py  # HTML output structure validation
```

**Target: 80%+ coverage on `core/` and `utils/`**

### 5.2 Integration Tests

```
tests/
  test_image_processor.py   # End-to-end processing pipeline
  test_photo_watcher.py     # File detection + processing trigger
  test_session_manager.py   # Save/restore round-trip
```

### 5.3 Test Fixtures

- Create `tests/fixtures/` with:
  - Small test images (JPEG, PNG, various ICC profiles)
  - Sample `config.json` variants (valid, missing keys, corrupted)
  - Sample `products.csv` (normal, empty, malformed)
  - Sample video file (short, 2-3 seconds, for 360 extraction)

### 5.4 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest  # Primary target platform
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

## Phase 6: Performance & Polish

**Priority**: Low | **Risk**: Low | **Impact**: Medium

### 6.1 Optimize Multi-Resolution Saving

**Problem**: `save_multi_resolution()` always converts to RGB even when not needed.

**Action**: Check if resize is needed before copying; skip conversion for images already in target mode.

### 6.2 Optimize Angle Button Updates

**Problem**: Every angle selection linearly scans all 8 buttons.

**Action**: Create `angle_id -> button_widget` lookup dict at init time. O(1) instead of O(n).

### 6.3 Optimize Report Generation

**Problem**: `export_report()` scans entire output directory per barcode.

**Action**: Single-pass directory scan with dictionary accumulation by barcode.

### 6.4 Lazy 360 Frame Loading in Viewer

**Problem**: HTML viewer preloads all frames (50-100 MB).

**Action**: Load S-resolution first, lazy-upgrade to selected resolution. Show loading indicator.

### 6.5 Add Type Hints

**Action**: Incrementally add type hints, starting with:
1. Public APIs of extracted modules
2. Config dataclass
3. Core utility functions
4. UI callback signatures

Use `mypy --strict` as the target.

### 6.6 Logging to File

**Action**:
- Add `logging.FileHandler` with rotation (5 MB, keep 3 files)
- Include timestamps, thread names, log levels
- UI log panel reads from same logger
- Users can attach log files when reporting bugs

---

## Dependency & Risk Matrix

### Phase Dependencies

```
Phase 1 (Critical Fixes) ─── no dependencies, start immediately
     │
Phase 2 (Architecture) ───── depends on Phase 1 completion
     │
     ├── Phase 3 (Robustness) ── can start during Phase 2
     │
     ├── Phase 4 (Features) ──── depends on Phase 2 module structure
     │
     └── Phase 5 (Testing) ───── can start during Phase 2 (test extracted modules)
              │
         Phase 6 (Performance) ── depends on Phase 2 + Phase 5
```

### Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|------------|
| Phase 1 | Low - targeted fixes | Each fix is independent, easy to revert |
| Phase 2 | Medium - structural changes | Extract one module at a time, commit per extraction, manual smoke test |
| Phase 3 | Low - additive changes | New validation layers, no existing behavior changes |
| Phase 4 | Low - new features | Feature-flagged, can ship incrementally |
| Phase 5 | Low - additive | Tests don't modify production code |
| Phase 6 | Low - optimization | Measurable before/after, easy rollback |

---

## File-by-File Action Items

### `app.py` (2937 lines)

| Lines | Component | Phase | Action |
|-------|-----------|-------|--------|
| 1-50 | Imports & globals | P2 | Move to `utils/constants.py` |
| 51-100 | Helper functions | P2 | Move to `utils/sanitize.py`, `utils/color_profile.py` |
| 100-170 | `save_multi_resolution()` | P2, P6 | Move to `core/file_manager.py`, optimize |
| 172-248 | `DEFAULT_CONFIG` | P2, P3 | Move to `core/config.py`, add schema validation |
| 250-300 | `ProductDB` | P2 | Move to `core/product_db.py` (as-is) |
| 306-466 | `ImageProcessor` | P1, P2 | Fix thread safety (P1), move to `core/image_processor.py` (P2) |
| 472-501 | `PhotoWatcher` | P1, P2 | Cap `_processed` set (P1), move to `core/photo_watcher.py` (P2) |
| 507-900 | App init + UI layout | P2 | Move UI building to `ui/main_window.py` |
| 900-1100 | Barcode/angle logic | P2 | Move to `ui/barcode_panel.py`, `ui/angle_panel.py` |
| 1100-1400 | Video/360 extraction | P1, P2, P4 | Fix silent errors (P1), move to `ui/spin360_dialog.py` (P2), add progress bar (P4) |
| 1400-1700 | 360 viewer generation | P2 | Move to `utils/viewer_generator.py` |
| 1700-2000 | Photo processing pipeline | P1 | Fix race conditions, add locks |
| 2000-2150 | File watcher management | P1 | Add observer.join timeout |
| 2150-2450 | Session management | P1, P2 | Fix silent load errors (P1), move to `core/session_manager.py` (P2) |
| 2450-2750 | Settings dialog | P2, P3 | Move to `ui/settings_dialog.py` (P2), add validation (P3) |
| 2750-2937 | Report/import/export | P2 | Move to `ui/report_dialog.py` |

### `gen_viewer.py` (14770 bytes)

| Action | Phase | Detail |
|--------|-------|--------|
| Remove hardcoded paths | P1 | Replace with CLI args (`argparse`) |
| Deduplicate with app.py | P2 | Both should use `utils/viewer_generator.py` |
| Add `--help` usage | P1 | Make it a proper CLI tool |

### `config.json` (1593 bytes)

| Action | Phase | Detail |
|--------|-------|--------|
| Add `config_version` field | P3 | For future migration support |
| Document all fields | P3 | Add `config.schema.json` |
| Validate on load | P3 | Reject invalid values with user feedback |

### `requirements.txt` (97 bytes)

| Action | Phase | Detail |
|--------|-------|--------|
| Pin numpy upper bound | P1 | `numpy>=1.24,<2.0` instead of `numpy<2` |
| Add dev dependencies section | P5 | `requirements-dev.txt` with pytest, ruff, mypy |
| Add optional deps markers | P3 | Document which are optional |

### `build.bat` / `installer.iss`

| Action | Phase | Detail |
|--------|-------|--------|
| Update for multi-file layout | P2 | After architecture refactor, update PyInstaller spec |
| Add version stamping | P5 | Inject git tag/hash into build |

---

## Quick Wins (Can Do Today)

These require minimal effort and have immediate benefit:

1. **Replace `except Exception: pass`** with logged warnings (~30 min)
2. **Add `threading.Lock()`** to shared state access points (~20 min)
3. **Cap log widget** to 500 lines (~5 min)
4. **Fix `gen_viewer.py`** hardcoded paths with `argparse` (~15 min)
5. **Pin numpy** version range in requirements.txt (~2 min)
6. **Add `.editorconfig`** for consistent formatting (~5 min)

---

## Success Metrics

| Metric | Current | Phase 2 Target | Phase 6 Target |
|--------|---------|----------------|----------------|
| Largest file (lines) | 2937 | < 500 | < 300 |
| Largest class (lines) | 2430 | < 400 | < 200 |
| Silent exception handlers | 10+ | 0 | 0 |
| Test coverage | 0% | 50% | 80%+ |
| Thread-safe shared objects | 0/4 | 4/4 | 4/4 |
| Type hint coverage | 0% | 30% | 70%+ |
| CI pipeline | None | Lint + test | Lint + test + build |

---

*Generated from full codebase audit on 2026-04-09.*
