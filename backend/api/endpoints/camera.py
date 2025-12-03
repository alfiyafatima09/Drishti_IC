"""Camera endpoints - Video feed and capture control."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID, uuid4
import logging
import asyncio

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


@router.websocket("/feed")
async def camera_feed(websocket: WebSocket):
    """
    WebSocket endpoint for live video streaming.
    
    Phone sends: Binary JPEG frames
    Desktop receives: Binary JPEG frames
    Server sends JSON events: CAMERA_CONNECTED, CAMERA_DISCONNECTED
    """
    global _phone_client, _latest_frame
    
    await websocket.accept()
    
    # Determine if this is a phone (sender) or desktop (receiver)
    # For simplicity, first connection without existing phone is the phone
    # Subsequent connections are desktops
    
    client_type = websocket.headers.get("X-Client-Type", "desktop").lower()
    
    if client_type == "phone" or _phone_client is None:
        # This is the phone (AOI simulator)
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
                # Receive frame from phone
                data = await websocket.receive_bytes()
                _latest_frame = data
                set_camera_status(True, datetime.utcnow())
                
                # Broadcast to all desktop clients
                for client in _desktop_clients:
                    try:
                        await client.send_bytes(data)
                    except Exception:
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
    else:
        # This is a desktop client
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
                # Desktop might send commands, but for now just keep alive
        except WebSocketDisconnect:
            _desktop_clients.remove(websocket)
            logger.info(f"Desktop client disconnected. Total: {len(_desktop_clients)}")


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

