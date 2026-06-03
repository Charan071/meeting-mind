"""WebSocket connection manager for real-time dashboard updates."""
import json
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import logger


class ConnectionManager:
    def __init__(self) -> None:
        # meeting_id → set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, meeting_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[meeting_id].add(ws)
        logger.info("ws_connected", meeting_id=meeting_id, total=len(self._connections[meeting_id]))

    def disconnect(self, meeting_id: str, ws: WebSocket) -> None:
        self._connections[meeting_id].discard(ws)
        if not self._connections[meeting_id]:
            del self._connections[meeting_id]
        logger.info("ws_disconnected", meeting_id=meeting_id)

    async def broadcast(self, meeting_id: str, data: dict) -> None:
        """Send a JSON event to all subscribers of a meeting."""
        dead: set[WebSocket] = set()
        for ws in self._connections.get(meeting_id, set()):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(meeting_id, ws)

    async def send_global(self, data: dict) -> None:
        """Broadcast to all connected clients (e.g. for user-level events)."""
        for conns in self._connections.values():
            for ws in list(conns):
                try:
                    await ws.send_text(json.dumps(data))
                except Exception:
                    pass


manager = ConnectionManager()
