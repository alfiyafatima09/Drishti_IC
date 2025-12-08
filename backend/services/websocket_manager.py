"""WebSocket Manager for handling real-time connections."""
from fastapi import WebSocket
from typing import List, Any
import logging
import json
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class WebSocketManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept connection and add to list."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection from list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: Any):
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        # Ensure message is JSON serializable (handle UUIDs/Datetimes)
        if not isinstance(message, str):
            try:
                message = json.dumps(message, cls=UUIDEncoder)
            except Exception as e:
                logger.error(f"Failed to serialize message for broadcast: {e}")
                return

        logger.debug(f"Broadcasting message to {len(self.active_connections)} clients")
        
        # Broadcast to all
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client, removing: {e}")
                disconnected.append(connection)

        # Cleanup disconnected
        for conn in disconnected:
            self.disconnect(conn)


# Global instance
manager = WebSocketManager()
