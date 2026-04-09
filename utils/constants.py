"""
constants.py — ค่าคงที่ของแอป (สี, ขนาดภาพ, นามสกุลไฟล์)
"""

# Dark-theme color palette
C = {
    "bg":           "#0f1117",
    "surface":      "#1a1d27",
    "surface2":     "#232734",
    "border":       "#2e3348",
    "text":         "#e2e4ed",
    "text_dim":     "#6b7394",
    "text_muted":   "#4a5170",
    "accent":       "#6c8cff",
    "accent_hover": "#8ba4ff",
    "green":        "#4ade80",
    "green_dim":    "#1a3a2a",
    "red":          "#f87171",
    "red_dim":      "#3a1a1a",
    "yellow":       "#fbbf24",
    "yellow_dim":   "#3a321a",
    "orange":       "#fb923c",
    "purple":       "#a78bfa",
    "barcode_bg":   "#141720",
    "btn_idle":     "#282d3e",
    "btn_active":   "#6c8cff",
    "btn_hover":    "#323850",
    "log_bg":       "#0c0e14",
    "tag_bg":       "#2a2f42",
}

# Multi-resolution presets (long edge in px)
MULTI_RES = {
    "S": {"max_px": 480, "quality": 85},
    "M": {"max_px": 800, "quality": 90},
    "L": {"max_px": 1200, "quality": 93},
}

# Default supported image extensions
SUPPORTED_EXTENSIONS = [
    ".jpg", ".jpeg", ".cr2", ".cr3", ".arw", ".nef",
    ".tif", ".tiff", ".png",
]
