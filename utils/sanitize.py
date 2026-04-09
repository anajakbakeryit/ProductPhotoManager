"""
sanitize.py — ทำความสะอาด barcode input สำหรับใช้เป็นชื่อไฟล์/โฟลเดอร์บน Windows
"""
import os
import re

_BARCODE_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Windows MAX_PATH (260) minus space for nested folder structure (~100 chars)
_MAX_BARCODE_LEN = 128


def sanitize_barcode(raw: str) -> str:
    """Sanitize barcode string for safe use as filename / folder name.

    - Removes path separators, traversal sequences, control chars
    - Removes characters illegal in Windows filenames
    - Caps length at 128 chars
    """
    s = raw.strip()
    s = _BARCODE_UNSAFE.sub("_", s)   # replace unsafe chars first
    s = s.replace("..", "")           # block traversal
    s = s.strip("._ ")               # no leading/trailing dots, underscores, spaces
    if not s:
        s = "UNKNOWN"
    return s[:_MAX_BARCODE_LEN]


def is_path_within(child: str, parent: str) -> bool:
    """Return True if `child` is strictly inside `parent` directory.

    Uses os.path.realpath to resolve symlinks and normpath to handle
    Windows edge cases (UNC paths, trailing slashes, mixed separators).
    """
    try:
        parent_real = os.path.realpath(os.path.normpath(parent)) + os.sep
        child_real = os.path.realpath(os.path.normpath(child))
        return child_real.startswith(parent_real)
    except Exception:
        return False
