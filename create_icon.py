"""Generate app icon (camera + barcode design)."""
from PIL import Image, ImageDraw, ImageFont

sizes = [256]
for sz in sizes:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = sz // 16  # margin

    # Background circle
    d.ellipse([m, m, sz - m, sz - m], fill="#1a1d27", outline="#6c8cff", width=max(2, sz // 40))

    # Camera body
    cx, cy = sz // 2, sz // 2 - sz // 16
    bw, bh = sz // 3, sz // 4
    d.rounded_rectangle(
        [cx - bw, cy - bh, cx + bw, cy + bh],
        radius=sz // 20, fill="#2e3348", outline="#6c8cff", width=max(1, sz // 64)
    )

    # Lens circle
    lr = sz // 7
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill="#0f1117", outline="#6c8cff",
              width=max(1, sz // 64))
    lr2 = sz // 10
    d.ellipse([cx - lr2, cy - lr2, cx + lr2, cy + lr2], fill="#1a1d27", outline="#4a5170",
              width=max(1, sz // 80))

    # Flash bump
    fw = sz // 8
    fh = sz // 14
    d.rounded_rectangle(
        [cx - fw, cy - bh - fh + 2, cx + fw // 3, cy - bh + 2],
        radius=sz // 40, fill="#2e3348", outline="#6c8cff", width=max(1, sz // 80)
    )

    # Barcode lines at bottom
    by = cy + bh + sz // 16
    bar_h = sz // 10
    bar_widths = [3, 1, 2, 1, 3, 2, 1, 2, 3, 1, 2, 1, 3]
    total_w = sum(bar_widths) * (sz // 80 + 1) + len(bar_widths) * (sz // 100)
    bx = cx - total_w // 2
    unit = max(1, sz // 80)
    gap = max(1, sz // 100)
    for w in bar_widths:
        pw = w * unit
        d.rectangle([bx, by, bx + pw, by + bar_h], fill="#6c8cff")
        bx += pw + gap

    img.save("app_icon.png", "PNG")

    # Convert to ICO
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for isz in icon_sizes:
        icons.append(img.resize(isz, Image.LANCZOS))
    icons[0].save("app_icon.ico", format="ICO", sizes=icon_sizes, append_images=icons[1:])

print("Created: app_icon.png + app_icon.ico")
