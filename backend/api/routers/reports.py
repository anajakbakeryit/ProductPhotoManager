"""
Reports router — export HTML/CSV summaries.
"""
import csv
import html
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, get_current_user
from backend.api.models.db import Photo, Product, User

router = APIRouter()


async def _get_summary(db: AsyncSession):
    """Per-barcode photo summary."""
    result = await db.execute(
        select(
            Photo.barcode,
            func.count(Photo.id).label("total_photos"),
            func.count(func.distinct(Photo.angle)).label("total_angles"),
        )
        .where(Photo.is_deleted == False)
        .group_by(Photo.barcode)
        .order_by(func.count(Photo.id).desc())
    )
    rows = result.all()

    summary = []
    for barcode, total, angles in rows:
        # Get product info
        prod = (await db.execute(
            select(Product).where(Product.barcode == barcode)
        )).scalar_one_or_none()

        # Count by angle
        angle_counts = (await db.execute(
            select(Photo.angle, func.count(Photo.id))
            .where(Photo.barcode == barcode, Photo.is_deleted == False)
            .group_by(Photo.angle)
        )).all()

        summary.append({
            "barcode": barcode,
            "name": prod.name if prod else "",
            "category": prod.category if prod else "",
            "total_photos": total,
            "total_angles": angles,
            "angles": {a: c for a, c in angle_counts},
        })
    return summary


@router.get("/summary")
async def report_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await _get_summary(db)


@router.get("/export/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    summary = await _get_summary(db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["barcode", "name", "category", "total_photos", "angles"])
    for row in summary:
        angles_str = ", ".join(f"{a}:{c}" for a, c in row["angles"].items())
        writer.writerow([row["barcode"], row["name"], row["category"],
                         row["total_photos"], angles_str])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


@router.get("/export/html")
async def export_html(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    summary = await _get_summary(db)
    total_photos = sum(r["total_photos"] for r in summary)
    total_barcodes = len(summary)

    rows_html = ""
    for r in summary:
        angles = " ".join(
            f'<span class="badge">{html.escape(a)}: {c}</span>' for a, c in r["angles"].items()
        )
        rows_html += f"""<tr>
            <td>{html.escape(r["barcode"])}</td>
            <td>{html.escape(r["name"])}</td>
            <td>{html.escape(r["category"])}</td>
            <td>{r["total_photos"]}</td>
            <td>{angles}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="th"><head><meta charset="UTF-8">
<title>รายงานภาพสินค้า</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e2e4ed; padding: 32px; }}
h1 {{ color: #6c8cff; }}
.stats {{ display: flex; gap: 16px; margin: 16px 0; }}
.stat {{ background: #1a1d27; padding: 16px 24px; border-radius: 8px; }}
.stat .num {{ font-size: 24px; font-weight: bold; color: #4ade80; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ padding: 10px 12px; border: 1px solid #2e3348; text-align: left; }}
th {{ background: #1a1d27; color: #6b7394; }}
.badge {{ display: inline-block; background: #2a2f42; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 12px; }}
</style></head><body>
<h1>รายงานภาพสินค้า</h1>
<div class="stats">
  <div class="stat"><div class="num">{total_barcodes}</div>บาร์โค้ด</div>
  <div class="stat"><div class="num">{total_photos}</div>รูปทั้งหมด</div>
</div>
<table><thead><tr>
  <th>บาร์โค้ด</th><th>ชื่อ</th><th>หมวดหมู่</th><th>จำนวนรูป</th><th>มุมถ่าย</th>
</tr></thead><tbody>{rows_html}</tbody></table>
</body></html>"""

    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=report.html"},
    )
