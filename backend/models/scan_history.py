"""Scan History model - Audit trail of all scans."""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from models.base import Base


class ScanHistory(Base):
    """
    Audit trail table for all IC scans performed by the system.
    Each scan gets a unique scan_id for tracking.
    """
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

    ocr_text_raw = Column(Text)  
    part_number_detected = Column(String(100), index=True)  
    part_number_candidates = Column(JSONB)  
    part_number_verified = Column(String(100), index=True)  
    
    status = Column(String(20), nullable=False, index=True)  
    confidence_score = Column(Float)  
    detected_pins = Column(Integer)
    expected_pins = Column(Integer)  
    manufacturer_detected = Column(String(100))
    batch_id = Column(String(100), index=True)
    batch_vender = Column(String(100), index=True)
    
    action_required = Column(String(20), default="NONE")  # NONE, SCAN_BOTTOM
    has_bottom_scan = Column(Boolean, default=False)
    
    match_details = Column(JSONB)  # {part_number_match, pin_count_match, manufacturer_match}
    verification_checks = Column(JSONB)  
    failure_reasons = Column(JSONB)  
    message = Column(Text)  
    
    was_manual_override = Column(Boolean, default=False)
    operator_note = Column(Text)
    
    # Timestamps
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<ScanHistory(scan_id='{self.scan_id}', status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "scan_id": str(self.scan_id),
            "ocr_text_raw": self.ocr_text_raw,
            "part_number_detected": self.part_number_detected,
            "part_number_candidates": self.part_number_candidates,
            "part_number_verified": self.part_number_verified,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "detected_pins": self.detected_pins,
            "expected_pins": self.expected_pins,
            "manufacturer_detected": self.manufacturer_detected,
            "batch_id": self.batch_id,
            "batch_vender": self.batch_vender,
            "action_required": self.action_required,
            "has_bottom_scan": self.has_bottom_scan,
            "match_details": self.match_details,
            "verification_checks": self.verification_checks,
            "failure_reasons": self.failure_reasons,
            "message": self.message,
            "was_manual_override": self.was_manual_override,
            "operator_note": self.operator_note,
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_list_item(self):
        """Convert to abbreviated format for list responses."""
        return {
            "scan_id": str(self.scan_id),
            "part_number": self.part_number_verified or self.part_number_detected,
            "part_number_detected": self.part_number_detected,
            "part_number_verified": self.part_number_verified,
            "status": self.status,
            "action_required": self.action_required,
            "confidence_score": self.confidence_score,
            "detected_pins": self.detected_pins,
            "has_bottom_scan": self.has_bottom_scan,
            "was_manual_override": self.was_manual_override,
            "manufacturer_detected": self.manufacturer_detected,
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "batch_id": self.batch_id,
            "batch_vender": self.batch_vender,
        }

