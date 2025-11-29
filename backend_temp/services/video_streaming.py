"""
Video streaming service for handling mobile camera input
"""
import asyncio
import os
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class VideoStreamingService:
    """Service for handling video streaming from mobile devices"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.frame_buffers: Dict[str, List[np.ndarray]] = {}
        self.processed_frames: Dict[str, List[Dict[str, Any]]] = {}

    async def process_video_chunk(
        self,
        session_id: str,
        chunk_data: bytes
    ) -> Dict[str, Any]:
        """Process incoming video chunk from mobile device"""

        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(chunk_data, np.uint8)

            # Decode image/frame
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                raise ValueError("Failed to decode video frame")

            # Initialize session if not exists
            if session_id not in self.frame_buffers:
                self.frame_buffers[session_id] = []
                self.processed_frames[session_id] = []

            # Store frame
            self.frame_buffers[session_id].append(frame)

            # Process frame for IC detection
            processed_result = await self._process_frame(frame, session_id)

            # Keep buffer size manageable (last 30 frames)
            if len(self.frame_buffers[session_id]) > 30:
                self.frame_buffers[session_id].pop(0)

            return {
                "session_id": session_id,
                "frame_processed": True,
                "frame_number": len(self.frame_buffers[session_id]),
                "detection_results": processed_result,
                "is_last_chunk": False  # Mobile app will indicate when stream ends
            }

        except Exception as e:
            logger.error(f"Error processing video chunk for session {session_id}: {e}")
            raise

    async def _process_frame(
        self,
        frame: np.ndarray,
        session_id: str
    ) -> Dict[str, Any]:
        """Process individual frame for IC detection"""

        try:
            # Basic preprocessing
            processed_frame = self._preprocess_frame(frame)

            # Detect potential IC markings
            detection_result = await self._detect_ic_markings(processed_frame)

            # Store processed result
            frame_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "frame_shape": frame.shape,
                "detection_result": detection_result
            }

            self.processed_frames[session_id].append(frame_result)

            return detection_result

        except Exception as e:
            logger.error(f"Error processing frame for session {session_id}: {e}")
            return {"error": str(e)}

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess video frame for better IC detection"""

        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

        return blurred

    async def _detect_ic_markings(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect IC markings in the frame"""

        # This is a placeholder for the actual detection logic
        # In a real implementation, this would use the OCR and logo detection services

        # Simple edge detection to find potential IC chips
        edges = cv2.Canny(frame, 50, 150)

        # Find contours (potential IC outlines)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter contours by size (typical IC chip size)
        min_area = 1000  # Minimum area in pixels
        max_area = 50000  # Maximum area in pixels

        potential_ics = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)

                # Check aspect ratio (ICs are usually rectangular)
                aspect_ratio = w / h if h > 0 else 0
                if 0.5 < aspect_ratio < 2.0:
                    potential_ics.append({
                        "bbox": [x, y, w, h],
                        "area": area,
                        "aspect_ratio": aspect_ratio,
                        "confidence": min(1.0, area / 10000)  # Simple confidence score
                    })

        return {
            "potential_ic_count": len(potential_ics),
            "potential_ics": potential_ics[:5],  # Return top 5 detections
            "frame_quality": self._assess_frame_quality(frame)
        }

    def _assess_frame_quality(self, frame: np.ndarray) -> Dict[str, float]:
        """Assess the quality of the video frame"""

        # Brightness assessment
        brightness = np.mean(frame)

        # Sharpness assessment (using Laplacian variance)
        laplacian_var = cv2.Laplacian(frame, cv2.CV_64F).var()

        # Contrast assessment
        contrast = frame.std()

        return {
            "brightness": float(brightness),
            "sharpness": float(laplacian_var),
            "contrast": float(contrast),
            "overall_quality": float((brightness / 128) * (laplacian_var / 500) * (contrast / 50))
        }

    async def get_processed_frames(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all processed frames for a session"""

        return self.processed_frames.get(session_id, [])

    def end_session(self, session_id: str):
        """Clean up session data"""

        if session_id in self.frame_buffers:
            del self.frame_buffers[session_id]

        if session_id in self.processed_frames:
            del self.processed_frames[session_id]

        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of video session processing"""

        processed_frames = self.processed_frames.get(session_id, [])

        if not processed_frames:
            return {"error": "No frames processed for session"}

        # Calculate statistics
        total_frames = len(processed_frames)
        avg_ic_detections = np.mean([
            f["detection_result"].get("potential_ic_count", 0)
            for f in processed_frames
        ])

        frame_qualities = [
            f["detection_result"].get("frame_quality", {}).get("overall_quality", 0)
            for f in processed_frames
        ]

        return {
            "session_id": session_id,
            "total_frames_processed": total_frames,
            "average_ic_detections_per_frame": float(avg_ic_detections),
            "average_frame_quality": float(np.mean(frame_qualities)),
            "best_frame_quality": float(max(frame_qualities)),
            "processing_summary": {
                "frames_with_potential_ics": sum(
                    1 for f in processed_frames
                    if f["detection_result"].get("potential_ic_count", 0) > 0
                )
            }
        }
