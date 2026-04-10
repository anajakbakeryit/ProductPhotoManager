"""
Angle detection heuristic — detects photo angle from filename and image metadata.

Rules:
1. Filename keyword match (word-boundary): front, back, left, right, top, bottom, detail, package
2. Filename number patterns: 01→front, 02→back, 03→left, 04→right, 05→top, 06→bottom, 07→detail, 08→package
3. Fallback: 'front'
"""
import re
from typing import Optional

ANGLE_KEYWORDS = ['front', 'back', 'left', 'right', 'top', 'bottom', 'detail', 'package']

# Common numbering convention for product photography
NUMBER_TO_ANGLE = {
    1: 'front', 2: 'back', 3: 'left', 4: 'right',
    5: 'top', 6: 'bottom', 7: 'detail', 8: 'package',
}

# Thai keywords
THAI_KEYWORDS = {
    'หน้า': 'front', 'หลัง': 'back', 'ซ้าย': 'left', 'ขวา': 'right',
    'บน': 'top', 'ล่าง': 'bottom', 'รายละเอียด': 'detail', 'แพ็ค': 'package',
}


def detect_angle_from_filename(filename: str) -> str:
    """Detect angle from filename using multiple strategies."""
    lower = filename.lower()
    stem = re.sub(r'\.[^.]+$', '', lower)  # Remove extension

    # Strategy 1: English keyword (word-boundary)
    for kw in ANGLE_KEYWORDS:
        if re.search(rf'(?:^|[_\-./\s]){kw}(?:[_\-./\s]|$)', lower):
            return kw

    # Strategy 2: Thai keyword
    for thai, eng in THAI_KEYWORDS.items():
        if thai in filename:
            return eng

    # Strategy 3: Number at end of stem (e.g., "IMG_01", "photo_3")
    match = re.search(r'[_\-]?(\d{1,2})$', stem)
    if match:
        num = int(match.group(1))
        if num in NUMBER_TO_ANGLE:
            return NUMBER_TO_ANGLE[num]

    # Strategy 4: Sequential number in middle (e.g., "barcode_01_shot")
    match = re.search(r'[_\-](\d{1,2})[_\-]', stem)
    if match:
        num = int(match.group(1))
        if num in NUMBER_TO_ANGLE:
            return NUMBER_TO_ANGLE[num]

    return 'front'


def detect_angles_batch(filenames: list[str]) -> dict[str, str]:
    """Detect angles for a batch of filenames. Returns {filename: angle}."""
    return {f: detect_angle_from_filename(f) for f in filenames}
