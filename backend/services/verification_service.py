"""Service for IC verification against database."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple, List
from datetime import datetime
from uuid import UUID
import logging

from models import ScanHistory, ICSpecification
from core.constants import get_manufacturer_name
from services.ic_service import ICService
from services.queue_service import QueueService
from schemas.common import ScanStatus
from schemas.scan_verify import (
    VerificationStatus,
    VerificationCheck,
    ScanVerifyResult,
    ActionRequired,
)

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for verifying ICs against database."""

    @staticmethod
    async def verify_scan(
        db: AsyncSession,
        scan_id: UUID,
        part_number_override: Optional[str] = None,
        detected_pins_override: Optional[int] = None,
    ) -> Tuple[ScanVerifyResult, Optional[str]]:
        """
        Verify a scan against the database.
        
        Returns:
            - ScanVerifyResult with verification outcome
            - Error message if verification fails (None if successful)
        """
        scan = await VerificationService._get_scan(db, scan_id)
        if not scan:
            error_msg = f"Scan with ID {scan_id} not found"
            logger.error(error_msg)
            return None, error_msg

        part_number = part_number_override or scan.part_number_detected
        detected_pins = detected_pins_override if detected_pins_override is not None else scan.detected_pins

        if not part_number:
            error_msg = "No part number available for verification"
            logger.error(error_msg)
            return None, error_msg

        logger.info(f"Starting verification for part_number={part_number}, pins={detected_pins}")

        verification_result = await VerificationService._perform_verification(
            db=db,
            part_number=part_number,
            detected_pins=detected_pins,
            scan_id=scan_id,
        )

        verification_checks = verification_result.verification_checks or {}
        verification_checks_dict = {
            key: value.model_dump() if hasattr(value, "model_dump") else None
            for key, value in verification_checks.items()
        }

        failure_reasons = [
            v.reason for v in verification_checks.values() if v and v.reason
        ]

        status_map = {
            VerificationStatus.MATCH_FOUND: ScanStatus.PASS.value,
            VerificationStatus.PIN_MISMATCH: ScanStatus.FAIL.value,
            VerificationStatus.NOT_IN_DATABASE: ScanStatus.UNKNOWN.value,
        }

        scan.part_number_verified = verification_result.part_number
        if detected_pins_override is not None:
            scan.detected_pins = detected_pins_override
        scan.expected_pins = (
            verification_result.matched_ic.get("pin_count")
            if verification_result.matched_ic
            else None
        )
        scan.match_details = {
            "part_number_match": verification_checks.get("part_number_match").status
            if verification_checks.get("part_number_match")
            else None,
            "pin_count_match": verification_checks.get("pin_count_match").status
            if verification_checks.get("pin_count_match")
            else None,
            "manufacturer_match": verification_checks.get("manufacturer_match").status
            if verification_checks.get("manufacturer_match")
            else None,
        }
        scan.failure_reasons = failure_reasons or None
        scan.verification_checks = verification_checks_dict
        scan.status = status_map.get(verification_result.verification_status, scan.status)
        scan.action_required = verification_result.action_required.value
        scan.message = verification_result.message
        scan.completed_at = verification_result.completed_at or datetime.utcnow()

        await db.flush()
        await db.refresh(scan)

        return verification_result, None

    @staticmethod
    async def _get_scan(db: AsyncSession, scan_id: UUID) -> Optional[ScanHistory]:
        """Get scan by ID."""
        from sqlalchemy import select
        result = await db.execute(
            select(ScanHistory).where(ScanHistory.scan_id == scan_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _perform_verification(
        db: AsyncSession,
        part_number: str,
        detected_pins: int,
        scan_id: UUID,
    ) -> ScanVerifyResult:
        """
        Perform verification checks and return detailed result with reasons.
        """
        ic_spec = await ICService.get_by_part_number(db, part_number)

        if not ic_spec:
            logger.info(f"Part number '{part_number}' not found in database")
            
            await QueueService.add_to_queue(db, part_number)
            queued_candidates = [part_number]

            result = ScanVerifyResult(
                scan_id=scan_id,
                verification_status=VerificationStatus.NOT_IN_DATABASE,
                action_required=ActionRequired.NONE,
                part_number=part_number,
                matched_ic=None,
                verification_checks={
                    "part_number_match": VerificationCheck(
                        status=False,
                        expected=None,
                        actual=part_number,
                        reason=f"Part number '{part_number}' not found in database. Added to sync queue for online lookup."
                    ),
                },
                confidence_score=0.0,
                queued_for_sync=True,
                queued_candidates=queued_candidates,
                message=f"IC not found in database. Added '{part_number}' to sync queue for online scraping.",
                completed_at=datetime.utcnow(),
            )
            return result

        logger.info(f"Found IC in database: {ic_spec.part_number} ({ic_spec.manufacturer}), {ic_spec.pin_count} pins")

        part_number_match = True  
        
        pin_match = detected_pins == ic_spec.pin_count
        pin_reason = None
        
        if not pin_match:
            pin_reason = (
                f"Pin count mismatch. Database specifies {ic_spec.pin_count} pins "
                f"for {part_number}, but detected {detected_pins} pins. "
                f"This may indicate a relabeled or counterfeit component."
            )
            logger.warning(pin_reason)

        if pin_match:
            verification_status = VerificationStatus.MATCH_FOUND
            action_required = ActionRequired.NONE
            overall_message = f"IC verified successfully. Part number and pin count match."
            confidence_score = 98.5
        else:
            verification_status = VerificationStatus.PIN_MISMATCH
            action_required = ActionRequired.MANUAL_REVIEW
            overall_message = (
                f"Verification FAILED. Part number '{part_number}' found in database "
                f"but pin count doesn't match. Expected {ic_spec.pin_count} pins, "
                f"detected {detected_pins} pins."
            )
            confidence_score = 60.0
    
        matched_ic_data = {
            "part_number": ic_spec.part_number,
            "manufacturer": ic_spec.manufacturer,
            "manufacturer_name": get_manufacturer_name(ic_spec.manufacturer),
            "pin_count": ic_spec.pin_count,
            "package_type": ic_spec.package_type,
            "description": ic_spec.description,
            "has_datasheet": ic_spec.has_datasheet if ic_spec.has_datasheet is not None else bool(ic_spec.datasheet_path),
            "datasheet_path": ic_spec.datasheet_path,
            "datasheet_url": ic_spec.datasheet_url,
        }

        result = ScanVerifyResult(
            scan_id=scan_id,
            verification_status=verification_status,
            action_required=action_required,
            part_number=part_number,
            matched_ic=matched_ic_data,
            verification_checks={
                "part_number_match": VerificationCheck(
                    status=True,
                    expected=ic_spec.part_number,
                    actual=part_number,
                    reason=None,
                ),
                "pin_count_match": VerificationCheck(
                    status=pin_match,
                    expected=ic_spec.pin_count,
                    actual=detected_pins,
                    reason=pin_reason,
                ),
            },
            confidence_score=confidence_score,
            queued_for_sync=False,
            queued_candidates=None,
            message=overall_message,
            completed_at=datetime.utcnow(),
        )

        return result
