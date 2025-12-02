"""Service for scan operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging

from backend.models import ScanHistory, ICSpecification, FakeRegistry, DatasheetQueue
from backend.schemas import ScanStatus, ActionRequired, MatchDetails
from backend.services.ic_service import ICService
from backend.services.queue_service import QueueService
from backend.services.fake_service import FakeService

logger = logging.getLogger(__name__)


class ScanService:
    """Service for managing IC scans."""

    @staticmethod
    async def create_scan(
        db: AsyncSession,
        ocr_text: str,
        part_number: str,
        detected_pins: int,
        confidence_score: float,
        manufacturer_detected: Optional[str] = None,
    ) -> ScanHistory:
        """
        Create a new scan and perform verification.
        This is the main scan logic.
        """
        # 1. Check if part number is in fake registry
        fake_entry = await FakeService.get_by_part_number(db, part_number)
        if fake_entry:
            scan = ScanHistory(
                ocr_text_raw=ocr_text,
                part_number_detected=part_number,
                part_number_verified=part_number,
                status=ScanStatus.COUNTERFEIT.value,
                confidence_score=confidence_score,
                detected_pins=detected_pins,
                manufacturer_detected=manufacturer_detected,
                action_required=ActionRequired.NONE.value,
                message=f"ALERT: IC '{part_number}' is in the fake registry. {fake_entry.reason or ''}",
            )
            db.add(scan)
            await db.flush()
            await db.refresh(scan)
            return scan

        # 2. Look up IC in golden record
        ic_spec = await ICService.get_by_part_number(db, part_number)
        
        if not ic_spec:
            # IC not in database - add to queue and return UNKNOWN
            await QueueService.add_to_queue(db, part_number)
            
            scan = ScanHistory(
                ocr_text_raw=ocr_text,
                part_number_detected=part_number,
                part_number_verified=part_number,
                status=ScanStatus.UNKNOWN.value,
                confidence_score=confidence_score,
                detected_pins=detected_pins,
                manufacturer_detected=manufacturer_detected,
                action_required=ActionRequired.NONE.value,
                message=f"IC '{part_number}' not found in database. Added to sync queue.",
                completed_at=datetime.utcnow(),
            )
            db.add(scan)
            await db.flush()
            await db.refresh(scan)
            return scan

        # 3. IC found - verify against golden record
        # Check if pins were detected (might need bottom scan for BTC components)
        if detected_pins == 0 and ic_spec.package_type in ["QFN", "BGA", "LGA"]:
            # Bottom-terminated component - need to flip
            scan = ScanHistory(
                ocr_text_raw=ocr_text,
                part_number_detected=part_number,
                part_number_verified=part_number,
                status=ScanStatus.PARTIAL.value,
                confidence_score=confidence_score,
                detected_pins=detected_pins,
                expected_pins=ic_spec.pin_count,
                manufacturer_detected=manufacturer_detected,
                action_required=ActionRequired.SCAN_BOTTOM.value,
                match_details={"part_number_match": True, "pin_count_match": None, "manufacturer_match": None},
                message=f"Pins not visible. This appears to be a {ic_spec.package_type} package. Please flip and scan the bottom.",
            )
            db.add(scan)
            await db.flush()
            await db.refresh(scan)
            return scan

        # 4. Perform verification
        pin_match = detected_pins == ic_spec.pin_count
        manufacturer_match = None
        if manufacturer_detected and ic_spec.manufacturer:
            manufacturer_match = manufacturer_detected.lower() in ic_spec.manufacturer.lower()

        match_details = {
            "part_number_match": True,
            "pin_count_match": pin_match,
            "manufacturer_match": manufacturer_match,
        }

        if pin_match:
            status = ScanStatus.PASS.value
            message = "IC verified successfully. All parameters match."
        else:
            status = ScanStatus.FAIL.value
            message = f"VERIFICATION FAILED: Pin count mismatch. Expected {ic_spec.pin_count} pins, detected {detected_pins}."

        scan = ScanHistory(
            ocr_text_raw=ocr_text,
            part_number_detected=part_number,
            part_number_verified=part_number,
            status=status,
            confidence_score=confidence_score,
            detected_pins=detected_pins,
            expected_pins=ic_spec.pin_count,
            manufacturer_detected=manufacturer_detected,
            action_required=ActionRequired.NONE.value,
            match_details=match_details,
            message=message,
            completed_at=datetime.utcnow(),
        )
        db.add(scan)
        await db.flush()
        await db.refresh(scan)
        return scan

    @staticmethod
    async def process_bottom_scan(
        db: AsyncSession,
        scan_id: UUID,
        detected_pins: int,
    ) -> Optional[ScanHistory]:
        """Process a bottom scan for BTC components."""
        # Get existing scan
        scan = await ScanService.get_by_scan_id(db, scan_id)
        if not scan:
            return None
        
        if scan.status != ScanStatus.PARTIAL.value:
            raise ValueError("This scan does not require a bottom scan")

        # Get IC spec
        ic_spec = await ICService.get_by_part_number(db, scan.part_number_verified)
        if not ic_spec:
            return None

        # Update scan with bottom scan results
        scan.detected_pins = detected_pins
        scan.has_bottom_scan = True
        
        pin_match = detected_pins == ic_spec.pin_count
        scan.match_details = {
            "part_number_match": True,
            "pin_count_match": pin_match,
            "manufacturer_match": scan.match_details.get("manufacturer_match") if scan.match_details else None,
        }

        if pin_match:
            scan.status = ScanStatus.PASS.value
            scan.message = f"Bottom scan complete. Pin count verified ({detected_pins} pins). IC is authentic."
        else:
            scan.status = ScanStatus.FAIL.value
            scan.message = f"VERIFICATION FAILED: Pin count mismatch. Expected {ic_spec.pin_count}, detected {detected_pins}."

        scan.action_required = ActionRequired.NONE.value
        scan.completed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(scan)
        return scan

    @staticmethod
    async def manual_override(
        db: AsyncSession,
        scan_id: UUID,
        manual_part_number: str,
        operator_note: Optional[str] = None,
    ) -> Optional[ScanHistory]:
        """Apply manual override to a scan."""
        scan = await ScanService.get_by_scan_id(db, scan_id)
        if not scan:
            return None

        # Check if new part number is in fake registry
        fake_entry = await FakeService.get_by_part_number(db, manual_part_number)
        if fake_entry:
            scan.part_number_verified = manual_part_number
            scan.was_manual_override = True
            scan.operator_note = operator_note
            scan.status = ScanStatus.COUNTERFEIT.value
            scan.message = f"Manual override: IC '{manual_part_number}' is in the fake registry."
            scan.completed_at = datetime.utcnow()
            await db.flush()
            await db.refresh(scan)
            return scan

        # Look up new part number
        ic_spec = await ICService.get_by_part_number(db, manual_part_number)
        
        scan.part_number_verified = manual_part_number
        scan.was_manual_override = True
        scan.operator_note = operator_note

        if not ic_spec:
            # Still unknown
            await QueueService.add_to_queue(db, manual_part_number)
            scan.status = ScanStatus.UNKNOWN.value
            scan.message = f"Manual override accepted. IC '{manual_part_number}' not in database. Added to sync queue."
        else:
            # Verify against new spec
            pin_match = scan.detected_pins == ic_spec.pin_count if scan.detected_pins else None
            scan.expected_pins = ic_spec.pin_count
            scan.match_details = {
                "part_number_match": True,
                "pin_count_match": pin_match,
                "manufacturer_match": None,
            }
            
            if pin_match:
                scan.status = ScanStatus.PASS.value
                scan.message = f"Manual override accepted. Pin count matches {manual_part_number} specification."
            elif pin_match is False:
                scan.status = ScanStatus.FAIL.value
                scan.message = f"Manual override accepted but FAILED: Expected {ic_spec.pin_count} pins, detected {scan.detected_pins}."
            else:
                scan.status = ScanStatus.PASS.value
                scan.message = f"Manual override accepted. Unable to verify pin count."

        scan.action_required = ActionRequired.NONE.value
        scan.completed_at = datetime.utcnow()

        await db.flush()
        await db.refresh(scan)
        return scan

    @staticmethod
    async def get_by_scan_id(db: AsyncSession, scan_id: UUID) -> Optional[ScanHistory]:
        """Get scan by scan_id."""
        result = await db.execute(
            select(ScanHistory).where(ScanHistory.scan_id == scan_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_scans(
        db: AsyncSession,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ScanHistory], int]:
        """List scans with optional filters."""
        base_query = select(ScanHistory)
        count_query = select(func.count()).select_from(ScanHistory)

        # Apply filters
        filters = []
        if status:
            filters.append(ScanHistory.status == status)
        if date_from:
            filters.append(ScanHistory.scanned_at >= date_from)
        if date_to:
            filters.append(ScanHistory.scanned_at <= date_to)

        if filters:
            base_query = base_query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get results
        base_query = base_query.order_by(ScanHistory.scanned_at.desc())
        base_query = base_query.limit(limit).offset(offset)

        result = await db.execute(base_query)
        scans = result.scalars().all()

        return list(scans), total_count

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        """Get scan statistics for dashboard."""
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)

        # Total scans
        total_result = await db.execute(select(func.count()).select_from(ScanHistory))
        total_scans = total_result.scalar() or 0

        # Scans today
        today_result = await db.execute(
            select(func.count()).select_from(ScanHistory).where(
                func.date(ScanHistory.scanned_at) == today
            )
        )
        scans_today = today_result.scalar() or 0

        # Scans this week
        week_result = await db.execute(
            select(func.count()).select_from(ScanHistory).where(
                ScanHistory.scanned_at >= datetime.combine(week_ago, datetime.min.time())
            )
        )
        scans_this_week = week_result.scalar() or 0

        # Status counts
        status_counts = {}
        for status in ["PASS", "FAIL", "UNKNOWN", "COUNTERFEIT"]:
            result = await db.execute(
                select(func.count()).select_from(ScanHistory).where(
                    ScanHistory.status == status
                )
            )
            status_counts[status.lower()] = result.scalar() or 0

        # Pass rate
        pass_rate = 0.0
        if total_scans > 0:
            pass_rate = (status_counts["pass"] / total_scans) * 100

        # Recent counterfeits
        counterfeit_result = await db.execute(
            select(ScanHistory).where(
                ScanHistory.status == "COUNTERFEIT"
            ).order_by(ScanHistory.scanned_at.desc()).limit(5)
        )
        recent_counterfeits = [
            {
                "part_number": s.part_number_verified or s.part_number_detected,
                "scanned_at": s.scanned_at.isoformat() if s.scanned_at else None,
            }
            for s in counterfeit_result.scalars().all()
        ]

        return {
            "total_scans": total_scans,
            "scans_today": scans_today,
            "scans_this_week": scans_this_week,
            "pass_count": status_counts["pass"],
            "fail_count": status_counts["fail"],
            "unknown_count": status_counts["unknown"],
            "counterfeit_count": status_counts["counterfeit"],
            "pass_rate_percentage": round(pass_rate, 1),
            "recent_counterfeits": recent_counterfeits,
        }

