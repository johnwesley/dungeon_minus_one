from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Location, LocationExit


class LocationRepository:
    """Repository for location data operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, location_id: str) -> Optional[Location]:
        """Get a location by ID with exits loaded."""
        result = await self.session.execute(
            select(Location)
            .options(selectinload(Location.exits))
            .where(Location.id == location_id)
        )
        return result.scalar_one_or_none()

    async def create(self, location_data: dict) -> Location:
        """Create a new location."""
        # Remove exits if present, handled separately
        data = location_data.copy()
        data.pop("exits", None)
        
        location = Location(**data)
        self.session.add(location)
        await self.session.flush()
        return location

    async def add_exit(self, source_id: str, target_id: str, direction: str) -> LocationExit:
        """Add an exit between locations."""
        exit_obj = LocationExit(
            source_id=source_id,
            target_id=target_id,
            direction=direction
        )
        self.session.add(exit_obj)
        await self.session.flush()
        return exit_obj

