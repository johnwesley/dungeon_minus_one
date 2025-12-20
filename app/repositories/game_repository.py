"""Repository for game state operations."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GameState
from app.repositories.location_repository import LocationRepository


class GameRepository:
    """Repository for game state CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_state(self, conversation_id: str) -> Optional[GameState]:
        """Get game state for a conversation."""
        result = await self.session.execute(
            select(GameState).where(GameState.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_state(self, conversation_id: str) -> GameState:
        """Get existing game state or create a new one."""
        state = await self.get_state(conversation_id)
        if state:
            return state

        state = GameState(
            conversation_id=conversation_id,
            current_location="start",
            inventory=[],
            visited_locations=[],
            player_stats={},
            flags={},
        )
        self.session.add(state)
        await self.session.flush()
        return state

    async def update_state(
        self, conversation_id: str, changes: dict
    ) -> Optional[GameState]:
        """Update game state with the provided changes.

        Args:
            conversation_id: The conversation/game session ID
            changes: Dict of fields to update. Valid keys:
                - current_location (str)
                - inventory (list)
                - visited_locations (list)
                - player_stats (dict)
                - flags (dict)

        Returns:
            Updated GameState or None if not found
        """
        state = await self.get_state(conversation_id)
        if not state:
            return None

        # Update allowed fields
        allowed_fields = {
            "current_location",
            "inventory",
            "visited_locations",
            "player_stats",
            "flags",
        }

        for field, value in changes.items():
            if field in allowed_fields:
                if field == "flags":
                    # Merge flags instead of replacing to preserve existing flags
                    # This prevents bugs like troll_incapacitated being wiped out
                    # when lantern_lit is updated
                    existing_flags = state.flags or {}
                    existing_flags.update(value)
                    setattr(state, field, existing_flags)
                else:
                    setattr(state, field, value)

        await self.session.flush()
        return state

    async def get_location(self, location_id: str) -> Optional[dict]:
        """Get location data by ID from DB.
        
        Returns:
            Dict with location data or None if not found
        """
        loc_repo = LocationRepository(self.session)
        location = await loc_repo.get(location_id)
        
        if not location:
            return None
            
        # Format as dict to match previous interface
        exits = {e.direction: e.target_id for e in location.exits}
        
        return {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "interactables": location.interactables,
            "npcs": location.npcs,
            "exits": exits,
            "requires_light": location.requires_light,
        }
