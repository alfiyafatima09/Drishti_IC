"""Service for IC specification operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import Optional
import logging

from backend.models import ICSpecification
from backend.schemas import ICSpecificationCreate, ICSpecificationResponse

logger = logging.getLogger(__name__)


class ICService:
    """Service for managing IC specifications (Golden Record)."""

    @staticmethod
    async def get_by_part_number(
        db: AsyncSession, part_number: str
    ) -> Optional[ICSpecification]:
        """Get IC specification by part number."""
        # Normalize part number (uppercase, strip whitespace)
        normalized = part_number.strip().upper()
        
        result = await db.execute(
            select(ICSpecification).where(
                func.upper(ICSpecification.part_number) == normalized
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, ic_id: int) -> Optional[ICSpecification]:
        """Get IC specification by ID."""
        result = await db.execute(
            select(ICSpecification).where(ICSpecification.id == ic_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def search(
        db: AsyncSession,
        query: str,
        manufacturer: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ICSpecification], int]:
        """Search IC specifications."""
        # Build base query
        base_query = select(ICSpecification)
        count_query = select(func.count()).select_from(ICSpecification)
        
        # Apply search filter
        if query:
            search_pattern = f"%{query}%"
            base_query = base_query.where(
                ICSpecification.part_number.ilike(search_pattern) |
                ICSpecification.description.ilike(search_pattern)
            )
            count_query = count_query.where(
                ICSpecification.part_number.ilike(search_pattern) |
                ICSpecification.description.ilike(search_pattern)
            )
        
        # Apply manufacturer filter
        if manufacturer:
            base_query = base_query.where(
                ICSpecification.manufacturer.ilike(f"%{manufacturer}%")
            )
            count_query = count_query.where(
                ICSpecification.manufacturer.ilike(f"%{manufacturer}%")
            )
        
        # Get total count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Get paginated results
        base_query = base_query.order_by(ICSpecification.part_number)
        base_query = base_query.limit(limit).offset(offset)
        
        result = await db.execute(base_query)
        ics = result.scalars().all()
        
        return list(ics), total_count

    @staticmethod
    async def create(
        db: AsyncSession, ic_data: ICSpecificationCreate
    ) -> ICSpecification:
        """Create a new IC specification."""
        ic = ICSpecification(
            part_number=ic_data.part_number.strip().upper(),
            manufacturer=ic_data.manufacturer,
            pin_count=ic_data.pin_count,
            package_type=ic_data.package_type,
            description=ic_data.description,
            datasheet_url=ic_data.datasheet_url,
            datasheet_path=ic_data.datasheet_path,
            voltage_min=ic_data.voltage_min,
            voltage_max=ic_data.voltage_max,
            operating_temp_min=ic_data.operating_temp_min,
            operating_temp_max=ic_data.operating_temp_max,
            electrical_specs=ic_data.electrical_specs,
            source=ic_data.source,
        )
        
        db.add(ic)
        try:
            await db.flush()
            await db.refresh(ic)
            return ic
        except IntegrityError:
            await db.rollback()
            raise ValueError(f"IC with part number '{ic_data.part_number}' already exists")

    @staticmethod
    async def update(
        db: AsyncSession,
        part_number: str,
        update_data: dict,
    ) -> Optional[ICSpecification]:
        """Update an existing IC specification."""
        ic = await ICService.get_by_part_number(db, part_number)
        if not ic:
            return None
        
        for key, value in update_data.items():
            if hasattr(ic, key) and value is not None:
                setattr(ic, key, value)
        
        await db.flush()
        await db.refresh(ic)
        return ic

    @staticmethod
    async def get_count(db: AsyncSession) -> int:
        """Get total count of IC specifications."""
        result = await db.execute(
            select(func.count()).select_from(ICSpecification)
        )
        return result.scalar() or 0

    @staticmethod
    async def get_datasheet_path(
        db: AsyncSession, part_number: str
    ) -> Optional[str]:
        """Get the local datasheet path for an IC."""
        ic = await ICService.get_by_part_number(db, part_number)
        if ic and ic.datasheet_path:
            return ic.datasheet_path
        return None

