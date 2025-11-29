"""Tool handlers for game-related Claude tool calls."""

import json
from typing import Any, Callable

from app.repositories.game_repository import GameRepository


class GameToolHandlers:
    """Handlers for game-related tool calls from Claude."""

    def __init__(self, game_repo: GameRepository):
        self.game_repo = game_repo

    async def get_location_data(self, input_data: dict[str, Any]) -> str:
        """Fetch static location data.

        Args:
            input_data: {"location_id": "..."}

        Returns:
            JSON string with location data or error
        """
        location_id = input_data.get("location_id")
        if not location_id:
            return json.dumps({"error": "location_id is required"})

        location = self.game_repo.get_location(location_id)
        if not location:
            return json.dumps({"error": f"Location '{location_id}' not found"})

        return json.dumps(location)

    async def get_game_state(self, input_data: dict[str, Any]) -> str:
        """Fetch current player game state.

        Args:
            input_data: {"conversation_id": "..."}

        Returns:
            JSON string with game state or error
        """
        conversation_id = input_data.get("conversation_id")
        if not conversation_id:
            return json.dumps({"error": "conversation_id is required"})

        state = await self.game_repo.get_or_create_state(conversation_id)

        return json.dumps({
            "current_location": state.current_location,
            "inventory": state.inventory or [],
            "visited_locations": state.visited_locations or [],
            "player_stats": state.player_stats or {},
            "flags": state.flags or {},
        })

    async def update_game_state(self, input_data: dict[str, Any]) -> str:
        """Update player game state.

        Args:
            input_data: {"conversation_id": "...", "changes": {...}}

        Returns:
            JSON string with updated state or error
        """
        conversation_id = input_data.get("conversation_id")
        changes = input_data.get("changes", {})

        if not conversation_id:
            return json.dumps({"error": "conversation_id is required"})

        if not changes:
            return json.dumps({"error": "changes object is required"})

        # Ensure state exists
        await self.game_repo.get_or_create_state(conversation_id)

        # Apply updates
        state = await self.game_repo.update_state(conversation_id, changes)

        if not state:
            return json.dumps({"error": "Failed to update game state"})

        return json.dumps({
            "success": True,
            "current_location": state.current_location,
            "inventory": state.inventory or [],
            "visited_locations": state.visited_locations or [],
            "player_stats": state.player_stats or {},
            "flags": state.flags or {},
        })

    def get_handlers(self) -> dict[str, Callable]:
        """Return mapping of tool names to handler methods."""
        return {
            "get_location_data": self.get_location_data,
            "get_game_state": self.get_game_state,
            "update_game_state": self.update_game_state,
        }
