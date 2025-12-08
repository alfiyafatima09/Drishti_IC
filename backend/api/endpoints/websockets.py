"""WebSocket endpoints."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/scans")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time scan updates.
    Clients connect here to receive 'scan_created', 'scan_updated' events.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen (though we mostly push from server)
            # We can implement ping/pong or client commands here if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
