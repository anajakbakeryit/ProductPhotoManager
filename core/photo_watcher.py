"""
core/photo_watcher.py — ตรวจจับไฟล์ใหม่ในโฟลเดอร์ watch_folder
"""
import logging
import os
import threading
import time
from typing import Callable, List

from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

_MAX_PROCESSED_ENTRIES = 5000
_PROCESSED_TRIM_TO = 2500


class PhotoWatcher(FileSystemEventHandler):
    """ตรวจจับไฟล์ภาพใหม่ที่เกิดขึ้นในโฟลเดอร์ แล้ว callback ไปยัง app."""

    def __init__(self, on_new_photo: Callable[[str], None], extensions: List[str]) -> None:
        """
        Args:
            on_new_photo: callback(filepath) เมื่อมีไฟล์ใหม่เข้ามา (thread-safe via tkinter after)
            extensions: รายการนามสกุลที่สนใจ เช่น ['.jpg', '.cr3']
        """
        self.on_new_photo = on_new_photo
        self.extensions = [e.lower() for e in extensions]
        self._processed: set = set()

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        ext = os.path.splitext(event.src_path)[1].lower()
        if ext in self.extensions:
            self._wait_and_process(event.src_path)

    def _wait_and_process(self, filepath: str) -> None:
        """รอให้ไฟล์เขียนเสร็จแล้วค่อย callback."""
        def _do():
            prev_size = -1
            for _ in range(60):
                try:
                    curr_size = os.path.getsize(filepath)
                    if curr_size == prev_size and curr_size > 0:
                        break
                    prev_size = curr_size
                except OSError:
                    pass
                time.sleep(0.5)

            if filepath not in self._processed:
                # จำกัดขนาด set ป้องกัน memory leak
                if len(self._processed) > _MAX_PROCESSED_ENTRIES:
                    self._processed = set(list(self._processed)[_PROCESSED_TRIM_TO:])
                self._processed.add(filepath)
                self.on_new_photo(filepath)

        threading.Thread(target=_do, daemon=True).start()
