"""WebSocket connection manager for broadcasting download progress."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket, WebSocketException

logger = logging.getLogger(__name__)

MAX_CONNECTIONS = 50


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        if len(self._connections) >= MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Too many connections")
            return
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            try:
                self._connections.remove(ws)
            except ValueError:
                pass


manager = ConnectionManager()
