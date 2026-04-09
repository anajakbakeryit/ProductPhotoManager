"""
core/session_manager.py — บันทึก/กู้คืน session state สำหรับ crash recovery
"""
import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_FILE = "session_state.json"
_MAX_SESSION_PHOTOS = 500


class SessionManager:
    """จัดการ session state: บันทึกลงดิสก์ และกู้คืนเมื่อแอปเปิดใหม่."""

    def __init__(self, path: str = SESSION_FILE) -> None:
        self.path = path

    def save(
        self,
        current_barcode: str,
        current_angle: str,
        angle_counters: dict,
        spin360_counter: int,
        session_photos: list,
    ) -> None:
        """บันทึก session ลงไฟล์ (cap ที่ 500 รูปล่าสุด)."""
        state = {
            "current_barcode": current_barcode,
            "current_angle": current_angle,
            "angle_counters": angle_counters,
            "spin360_counter": spin360_counter,
            "session_photos": session_photos[-_MAX_SESSION_PHOTOS:],
            "saved_at": datetime.now().isoformat(),
        }
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning(f"[session] บันทึกไม่สำเร็จ: {e}")

    def load(self) -> Optional[dict]:
        """โหลด session จากไฟล์ คืน None ถ้าไม่มีหรือเสียหาย."""
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if not state.get("session_photos"):
                return None
            return state
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning(f"[session] กู้คืนไม่สำเร็จ: {e} — ลบไฟล์ session เสียหาย")
            self._delete()
            return None

    def delete(self) -> None:
        """ลบไฟล์ session."""
        self._delete()

    def _delete(self) -> None:
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError as e:
            logger.warning(f"[session] ลบไฟล์ไม่สำเร็จ: {e}")
