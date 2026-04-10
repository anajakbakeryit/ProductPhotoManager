"""
WebSocket manager for real-time pipeline status updates.
"""
import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts pipeline status."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict[str, Any]):
        """Send message to all connected clients."""
        text = json.dumps(message, ensure_ascii=False)
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_text(text)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)


# Singleton
ws_manager = ConnectionManager()
