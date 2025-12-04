"""Camera endpoints - Video feed and capture control."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID, uuid4
import logging
import asyncio
import json

from core.database import get_db
from schemas import CaptureRequest, CaptureResponse, CaptureType
from api.endpoints.system import set_camera_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/camera", tags=["Camera"])

# Store the latest frame and connected clients
_latest_frame: bytes = b""
_desktop_clients: list[WebSocket] = []
_phone_client: WebSocket = None
_pending_capture: asyncio.Event = None
_capture_result: dict = None


async def handle_phone_connection(websocket: WebSocket):
    """Handle phone camera connection - receives and broadcasts frames."""
    global _phone_client, _latest_frame
    
    _phone_client = websocket
    set_camera_status(True, datetime.utcnow())
    logger.info("Phone camera connected")
    
    # Notify desktops
    for client in _desktop_clients:
        try:
            await client.send_json({"event": "CAMERA_CONNECTED", "timestamp": datetime.utcnow().isoformat()})
        except Exception:
            pass
    
    try:
        while True:
            # Receive data from phone (can be binary frame or JSON message)
            message = await websocket.receive()
            
            if "bytes" in message:
                # Binary frame data
                data = message["bytes"]
                _latest_frame = data
                set_camera_status(True, datetime.utcnow())
                
                # Broadcast to all desktop clients
                for client in _desktop_clients:
                    try:
                        await client.send_bytes(data)
                    except Exception:
                        pass
                        
            elif "text" in message:
                # JSON message (ping, identify, etc.)
                try:
                    msg = json.loads(message["text"])
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": msg.get("timestamp")})
                except json.JSONDecodeError:
                    pass
                    
    except WebSocketDisconnect:
        logger.info("Phone camera disconnected")
        _phone_client = None
        set_camera_status(False)
        
        # Notify desktops
        for client in _desktop_clients:
            try:
                await client.send_json({"event": "CAMERA_DISCONNECTED", "timestamp": datetime.utcnow().isoformat()})
            except Exception:
                pass


async def handle_desktop_connection(websocket: WebSocket):
    """Handle desktop connection - receives frames from phone."""
    _desktop_clients.append(websocket)
    logger.info(f"Desktop client connected. Total: {len(_desktop_clients)}")
    
    # Send current camera status
    if _phone_client:
        await websocket.send_json({"event": "CAMERA_CONNECTED", "timestamp": datetime.utcnow().isoformat()})
    else:
        await websocket.send_json({"event": "CAMERA_DISCONNECTED", "timestamp": datetime.utcnow().isoformat()})
    
    try:
        while True:
            # Keep connection alive, handle any messages from desktop
            message = await websocket.receive_text()
            # Desktop might send commands (like capture trigger)
            try:
                msg = json.loads(message)
                if msg.get("type") == "capture":
                    # Handle capture request from desktop
                    logger.info("Desktop requested capture")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in _desktop_clients:
            _desktop_clients.remove(websocket)
        logger.info(f"Desktop client disconnected. Total: {len(_desktop_clients)}")


@router.websocket("/feed")
async def camera_feed(websocket: WebSocket):
    """
    WebSocket endpoint for live video streaming.
    
    Phone sends: Binary JPEG frames + JSON messages
    Desktop receives: Binary JPEG frames + JSON events
    
    Connection flow:
    1. Client connects
    2. Server accepts and waits for identification
    3. First message should be: {"type": "identify", "client": "phone"|"desktop"}
    4. If no identify message, falls back to header check or assumes desktop
    """
    global _phone_client
    
    await websocket.accept()
    logger.info("New WebSocket connection")
    
    # Check header for client type (for native apps that can set headers)
    client_type = websocket.headers.get("X-Client-Type", "").lower()
    
    if client_type == "phone":
        await handle_phone_connection(websocket)
        return
    elif client_type == "desktop":
        await handle_desktop_connection(websocket)
        return
    
    # No header - wait for identification message or first data
    try:
        # Wait for first message with short timeout
        message = await asyncio.wait_for(websocket.receive(), timeout=5.0)
        
        if "text" in message:
            try:
                msg = json.loads(message["text"])
                if msg.get("type") == "identify":
                    client_type = msg.get("client", "desktop").lower()
                    logger.info(f"Client identified as: {client_type}")
                    
                    if client_type == "phone":
                        await handle_phone_connection(websocket)
                    else:
                        await handle_desktop_connection(websocket)
                    return
            except json.JSONDecodeError:
                pass
        
        elif "bytes" in message:
            # First message is binary - this is a phone sending frames
            # Store this frame and continue as phone
            _latest_frame = message["bytes"]
            await handle_phone_connection(websocket)
            return
            
    except asyncio.TimeoutError:
        # No identification received - assume desktop
        logger.info("No identification received, assuming desktop")
    
    # Default to desktop
    await handle_desktop_connection(websocket)


@router.post("/capture", response_model=CaptureResponse)
async def capture_frame(
    request: CaptureRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger frame capture from the video feed.
    
    Desktop triggers capture, server grabs current frame and processes it.
    """
    global _latest_frame
    
    if not _phone_client or not _latest_frame:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CAMERA_NOT_CONNECTED",
                "message": "No camera feed available. Please connect the AOI device.",
            }
        )
    
    # Generate scan ID
    scan_id = uuid4()
    
    if request.capture_type == CaptureType.BOTTOM:
        if not request.scan_id:
            raise HTTPException(
                status_code=400,
                detail="scan_id is required for bottom capture"
            )
        scan_id = request.scan_id
    
    # The actual processing will be done by the scan endpoint
    # Here we just confirm capture was successful
    # In a real implementation, you might:
    # 1. Save the frame temporarily
    # 2. Pass it to the scan processing pipeline
    # 3. Return the scan_id for the client to poll
    
    logger.info(f"Frame captured for {request.capture_type.value} scan, scan_id: {scan_id}")
    
    return CaptureResponse(
        success=True,
        message=f"Frame captured successfully. Processing {request.capture_type.value.lower()} scan...",
        scan_id=scan_id,
    )

