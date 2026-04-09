"""
color_profile.py — ICC color profile conversion + multi-resolution save
"""
import io
import logging
import os

from PIL import Image, ImageCms

from utils.constants import MULTI_RES

logger = logging.getLogger(__name__)

# sRGB ICC profile bytes — embedded in every output JPEG/PNG for color accuracy
_SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def to_srgb(img: Image.Image) -> Image.Image:
    """Convert image to sRGB with proper color management.

    If image has an embedded ICC profile (e.g., AdobeRGB from Canon 5D),
    properly maps pixel values to sRGB so colors and contrast match.
    Returns RGB/RGBA image with sRGB ICC profile in .info['icc_profile'].
    """
    icc_data = img.info.get("icc_profile")

    if icc_data and icc_data != _SRGB_ICC:
        try:
            src_profile = io.BytesIO(icc_data)
            dst_profile = ImageCms.createProfile("sRGB")

            if img.mode == "RGBA":
                r, g, b, a = img.split()
                rgb = Image.merge("RGB", (r, g, b))
                rgb = ImageCms.profileToProfile(
                    rgb, src_profile, dst_profile,
                    renderingIntent=ImageCms.Intent.PERCEPTUAL,
                    outputMode="RGB",
                )
                r2, g2, b2 = rgb.split()
                img = Image.merge("RGBA", (r2, g2, b2, a))
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img = ImageCms.profileToProfile(
                    img, src_profile, dst_profile,
                    renderingIntent=ImageCms.Intent.PERCEPTUAL,
                    outputMode="RGB",
                )
        except Exception as e:
            logger.warning(f"[to_srgb] ICC แปลงสีล้มเหลว: {e} — ใช้โหมดสีดิบแทน")
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
    else:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

    img.info["icc_profile"] = _SRGB_ICC
    return img


def save_multi_resolution(
    img: Image.Image,
    folder: str,
    base_name: str,
    ext: str = ".jpg",
    is_png: bool = False,
) -> None:
    """Save image in S/M/L/OG sub-folders.

    Args:
        img: PIL Image (RGB or RGBA), should already be to_srgb() converted
        folder: e.g. output_root/original/barcode
        base_name: filename without extension, e.g. 'SKU001_front_01'
        ext: output extension (.jpg or .png)
        is_png: if True, save as PNG (for cutout with transparency)
    """
    icc = img.info.get("icc_profile", _SRGB_ICC)
    orig_w, orig_h = img.size

    # OG - original size
    og_dir = os.path.join(folder, "OG")
    os.makedirs(og_dir, exist_ok=True)
    og_path = os.path.join(og_dir, f"{base_name}_OG{ext}")
    if is_png:
        img.save(og_path, "PNG", icc_profile=icc)
    else:
        img_rgb = img.convert("RGB") if img.mode != "RGB" else img
        img_rgb.save(og_path, "JPEG", quality=95, subsampling=0, icc_profile=icc)

    # S / M / L
    for sz_key, cfg in MULTI_RES.items():
        sz_dir = os.path.join(folder, sz_key)
        os.makedirs(sz_dir, exist_ok=True)
        max_px = cfg["max_px"]

        # Skip resize if image is already smaller than target
        if orig_w <= max_px and orig_h <= max_px:
            resized = img
        else:
            ratio = min(max_px / orig_w, max_px / orig_h)
            new_w = int(orig_w * ratio)
            new_h = int(orig_h * ratio)
            resized = img.resize((new_w, new_h), Image.LANCZOS)

        sz_path = os.path.join(sz_dir, f"{base_name}_{sz_key}{ext}")
        if is_png:
            resized.save(sz_path, "PNG", icc_profile=icc)
        else:
            resized_rgb = resized.convert("RGB") if resized.mode != "RGB" else resized
            resized_rgb.save(sz_path, "JPEG", quality=cfg["quality"],
                             subsampling=0, icc_profile=icc)
