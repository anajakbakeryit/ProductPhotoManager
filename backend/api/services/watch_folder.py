"""
Watch folder service — auto-upload photos from a local directory.

Expected folder structure:
  watch_folder/
    {barcode}/
      front_01.jpg
      back_01.jpg
      ...

Files are auto-detected by barcode (folder name) and angle (filename keyword).
"""
import os
import re
import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)

ANGLE_KEYWORDS = ['front', 'back', 'left', 'right', 'top', 'bottom', 'detail', 'package']
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.cr2', '.cr3', '.arw', '.nef'}


def detect_angle(filename: str) -> str:
    lower = filename.lower()
    for kw in ANGLE_KEYWORDS:
        if re.search(rf'(?:^|[_\-./\s]){kw}(?:[_\-./\s]|$)', lower):
            return kw
    return 'front'


class PhotoWatchHandler(FileSystemEventHandler):
    """Handles new image files in watch folder."""

    def __init__(self, upload_callback):
        self.upload_callback = upload_callback

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            path = Path(event.src_path)
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                # Barcode = parent folder name
                barcode = path.parent.name
                angle = detect_angle(path.name)
                logger.info(f"Watch folder: new file {path.name} → barcode={barcode}, angle={angle}")
                # Call the async upload callback
                try:
                    self.upload_callback(str(path), barcode, angle)
                except Exception as e:
                    logger.error(f"Watch folder upload error: {e}")


_observer = None


def start_watch_folder(folder_path: str, upload_callback) -> bool:
    """Start watching a folder for new images."""
    global _observer

    if _observer is not None:
        stop_watch_folder()

    folder = Path(folder_path)
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)

    handler = PhotoWatchHandler(upload_callback)
    _observer = Observer()
    _observer.schedule(handler, str(folder), recursive=True)
    _observer.start()
    logger.info(f"Watch folder started: {folder}")
    return True


def stop_watch_folder():
    """Stop watching."""
    global _observer
    if _observer is not None:
        _observer.stop()
        _observer.join()
        _observer = None
        logger.info("Watch folder stopped")


def is_watching() -> bool:
    return _observer is not None and _observer.is_alive()
