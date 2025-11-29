"""
Video streaming routes for mobile camera input
"""
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    status
)
from sqlalchemy.orm import Session
from typing import Optional, Dict, Set
from collections import defaultdict
import uuid
import base64
import logging
from datetime import datetime
from starlette.websockets import WebSocketState

from models.database import get_db, VideoSession
from services.video_streaming import VideoStreamingService
from config.settings import settings

router = APIRouter()
video_service = VideoStreamingService()
logger = logging.getLogger(__name__)
session_viewers: Dict[str, Set[WebSocket]] = defaultdict(set)
session_producers: Dict[str, WebSocket] = {}
current_active_session_id: Optional[str] = None


async def broadcast_to_viewers(session_id: str, message: Dict):
    """Send message to all connected viewers for a session."""
    viewers = session_viewers.get(session_id)
    if not viewers:
        return

    disconnected = []
    for ws in list(viewers):
        try:
            await ws.send_json(message)
        except Exception as exc:
            logger.error(f"Failed to send message to viewer: {exc}")
            disconnected.append(ws)

    for ws in disconnected:
        try:
            viewers.discard(ws)
            await ws.close()
        except Exception:
            pass


def mark_session_completed(session: VideoSession):
    """Mark session as completed with timestamps."""
    if session.status != "completed":
        session.status = "completed"
        session.end_time = datetime.utcnow()
        if session.start_time:
            session.duration_seconds = (session.end_time - session.start_time).total_seconds()


@router.post("/video/sessions/start")
async def start_video_session(
    device_id: Optional[str] = None,
    resolution: Optional[str] = "1920x1080",
    fps: Optional[float] = 30.0,
    db: Session = Depends(get_db)
):
    """Start a new video streaming session"""

    global current_active_session_id

    # Ensure only one active session at a time  
    active_sessions = db.query(VideoSession).filter_by(status="active").all()
    for active in active_sessions:
        mark_session_completed(active)
    if active_sessions:
        db.commit()

    session_id = str(uuid.uuid4())
    session = VideoSession(
        session_id=session_id,
        device_id=device_id,
        resolution=resolution,
        fps=fps,
        status="active"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    current_active_session_id = session_id

    return {
        "session_id": session_id,
        "status": "started",
        "upload_url": f"/api/v1/video/sessions/{session_id}/stream",
        "ingest_ws_path": f"/api/v1/video/ws/{session_id}/ingest",
        "viewer_ws_path": f"/api/v1/video/ws/{session_id}/view"
    }


@router.get("/video/sessions/active")
async def get_active_video_session(db: Session = Depends(get_db)):
    """Return the currently active video session, if any."""

    session = (
        db.query(VideoSession)
        .filter_by(status="active")
        .order_by(VideoSession.start_time.desc())
        .first()
    )

    if not session:
        return {"active": False}

    return {
        "active": True,
        "session_id": session.session_id,
        "started_at": session.start_time.isoformat() if session.start_time else None,
        "ingest_ws_path": f"/api/v1/video/ws/{session.session_id}/ingest",
        "viewer_ws_path": f"/api/v1/video/ws/{session.session_id}/view",
    }


@router.post("/video/sessions/{session_id}/stream")
async def stream_video_chunk(
    session_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Receive video chunks from mobile device"""

    
    session = db.query(VideoSession).filter_by(session_id=session_id, status="active").first()
    if not session:
        raise HTTPException(status_code=404, detail="Video session not found or not active")

    try:
        
        chunk_data = await file.read()
        result = await video_service.process_video_chunk(session_id, chunk_data)

        
        session.frame_count += 1

        
        if result.get("is_last_chunk", False):
            session.status = "completed"
            session.end_time = datetime.utcnow()
            session.duration_seconds = (session.end_time - session.start_time).total_seconds()

        db.commit()

        return result

    except Exception as e:
        session.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")


@router.websocket("/video/ws/{session_id}/ingest")
async def video_stream_ingest(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """Receive frames from the mobile device and broadcast to viewers."""

    global current_active_session_id

    await websocket.accept()

    session = db.query(VideoSession).filter_by(session_id=session_id).first()
    if not session or session.status != "active":
        await websocket.send_json({
            "type": "error",
            "message": "Video session not found or not active"
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    existing_producer = session_producers.get(session_id)
    if existing_producer:
        await websocket.send_json({
            "type": "error",
            "message": "A producer is already connected for this session"
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    session_producers[session_id] = websocket
    await websocket.send_json({"type": "ready"})

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")

            if message_type == "frame":
                frame_data = payload.get("data")
                if not frame_data:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Frame data missing"
                    })
                    continue

                try:
                    chunk_bytes = base64.b64decode(frame_data)
                except Exception as exc:
                    logger.error(f"Invalid base64 frame for session {session_id}: {exc}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid frame encoding"
                    })
                    continue

                
                await broadcast_to_viewers(session_id, {
                    "type": "frame",
                    "data": frame_data
                })

                result = await video_service.process_video_chunk(session_id, chunk_bytes)
                session.frame_count = (session.frame_count or 0) + 1
                db.commit()

                await websocket.send_json({
                    "type": "frame_processed",
                    "data": {
                        "session_id": session_id,
                        "frame_number": result.get("frame_number"),
                        "detection_results": result.get("detection_results"),
                    }
                })

                await broadcast_to_viewers(session_id, {
                    "type": "analysis",
                    "data": {
                        "frame_number": result.get("frame_number"),
                        "detection_results": result.get("detection_results"),
                    }
                })

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif message_type == "stop":
                mark_session_completed(session)
                db.commit()
                await websocket.send_json({"type": "session_completed"})
                await broadcast_to_viewers(session_id, {"type": "session_completed"})
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                break

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unsupported message type: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"Producer disconnected for session {session_id}")

    except Exception as exc:
        logger.error(f"WebSocket error for session {session_id}: {exc}", exc_info=True)
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_json({"type": "error", "message": "Internal server error"})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        stored = session_producers.get(session_id)
        if stored is websocket:
            session_producers.pop(session_id, None)

        current_session = db.query(VideoSession).filter_by(session_id=session_id).first()
        if current_session and current_session.status == "active":
            mark_session_completed(current_session)
            db.commit()
            await broadcast_to_viewers(session_id, {"type": "session_completed"})

        viewers = session_viewers.pop(session_id, None)
        if viewers:
            for viewer in list(viewers):
                try:
                    await viewer.close(code=status.WS_1000_NORMAL_CLOSURE)
                except Exception:
                    pass
        video_service.end_session(session_id)
        if current_active_session_id == session_id:
            current_active_session_id = None


@router.websocket("/video/ws/{session_id}/view")
async def video_stream_view(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """Viewer WebSocket to receive frames and analysis."""

    await websocket.accept()

    session = db.query(VideoSession).filter_by(session_id=session_id).first()
    if not session or session.status != "active":
        await websocket.send_json({
            "type": "error",
            "message": "No active stream to view"
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    viewers = session_viewers[session_id]
    viewers.add(websocket)
    await websocket.send_json({"type": "viewer_connected", "session_id": session_id})

    try:
        while True:
            # Keep the connection alive; viewers don't need to send data
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Viewer disconnected from session {session_id}")
    except Exception as exc:
        logger.error(f"Viewer websocket error: {exc}")
    finally:
        viewers.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/video/sessions/{session_id}/status")
async def get_session_status(session_id: str, db: Session = Depends(get_db)):
    """Get video session status"""

    session = db.query(VideoSession).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    return {
        "session_id": session.session_id,
        "status": session.status,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "duration_seconds": session.duration_seconds,
        "frame_count": session.frame_count,
        "device_id": session.device_id,
        "resolution": session.resolution,
        "fps": session.fps
    }


@router.delete("/video/sessions/{session_id}")
async def end_video_session(session_id: str, db: Session = Depends(get_db)):
    """End a video streaming session"""

    session = db.query(VideoSession).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    if session.status == "active":
        session.status = "completed"
        session.end_time = datetime.utcnow()
        session.duration_seconds = (session.end_time - session.start_time).total_seconds()

    db.commit()

    return {"message": "Video session ended successfully"}


@router.get("/video/sessions/{session_id}/frames")
async def get_processed_frames(session_id: str, db: Session = Depends(get_db)):
    """Get processed frames from a video session"""

    session = db.query(VideoSession).filter_by(session_id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    frames = await video_service.get_processed_frames(session_id)
    return {"frames": frames}
