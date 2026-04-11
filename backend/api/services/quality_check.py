"""
AI Quality Check — validates photo quality after upload.

Checks:
1. Blur detection (Laplacian variance)
2. Brightness (too dark / too bright)
3. Product presence (enough edges in center)
4. White balance (background should be white-ish)

Returns quality_score (1-5) and list of issues.
"""
import logging
from PIL import Image
from io import BytesIO

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logger = logging.getLogger(__name__)

BLUR_THRESHOLD = 100        # Laplacian variance below this = blurry
DARK_THRESHOLD = 60         # Average brightness below this = too dark
BRIGHT_THRESHOLD = 240      # Average brightness above this = too bright
EDGE_THRESHOLD = 0.05       # Center edge ratio below this = no product


def check_quality(image_bytes: bytes) -> dict:
    """
    Analyze image quality. Returns:
    {
        "score": 1-5,
        "issues": ["blurry", "too_dark", ...],
        "details": { "blur_score": 123.4, "brightness": 180, ... },
        "passed": True/False
    }
    """
    if not HAS_NUMPY:
        logger.warning("numpy not installed — skipping quality check")
        return {"score": 5, "issues": [], "details": {}, "passed": True}

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
    except Exception as e:
        logger.error(f"Quality check failed to open image: {e}")
        return {"score": 1, "issues": ["invalid_image"], "details": {}, "passed": False}

    issues = []
    details = {}

    # 1. Blur detection (Laplacian variance on grayscale)
    gray = np.mean(arr, axis=2)
    # Simple Laplacian: second derivative approximation
    laplacian = (
        gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
        - 4 * gray[1:-1, 1:-1]
    )
    blur_score = float(np.var(laplacian))
    details["blur_score"] = round(blur_score, 1)
    if blur_score < BLUR_THRESHOLD:
        issues.append("blurry")

    # 2. Brightness check
    brightness = float(np.mean(arr))
    details["brightness"] = round(brightness, 1)
    if brightness < DARK_THRESHOLD:
        issues.append("too_dark")
    elif brightness > BRIGHT_THRESHOLD:
        issues.append("too_bright")

    # 3. Product presence (check center has enough edges/detail)
    h, w = gray.shape
    center = gray[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
    center_edges = np.abs(np.diff(center, axis=0)).mean() + np.abs(np.diff(center, axis=1)).mean()
    edge_ratio = center_edges / 255.0
    details["center_edge_ratio"] = round(float(edge_ratio), 4)
    if edge_ratio < EDGE_THRESHOLD:
        issues.append("no_product")

    # 4. White balance (check corners — should be near white if white background)
    corner_size = min(h, w) // 8
    corners = [
        arr[:corner_size, :corner_size],
        arr[:corner_size, -corner_size:],
        arr[-corner_size:, :corner_size],
        arr[-corner_size:, -corner_size:],
    ]
    avg_corner = np.mean([np.mean(c, axis=(0, 1)) for c in corners], axis=0)
    details["corner_rgb"] = [round(float(x), 1) for x in avg_corner]
    # If corners are not white-ish (all channels > 200), flag it
    if any(c < 180 for c in avg_corner):
        issues.append("bad_white_balance")

    # Calculate score
    if len(issues) == 0:
        score = 5
    elif len(issues) == 1 and issues[0] == "bad_white_balance":
        score = 4  # White balance is minor
    elif len(issues) == 1:
        score = 3
    elif len(issues) == 2:
        score = 2
    else:
        score = 1

    passed = score >= 3

    return {
        "score": score,
        "issues": issues,
        "details": details,
        "passed": passed,
    }
