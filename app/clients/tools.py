"""Tool definitions for the game narrator agent.

These tools allow Claude to fetch and update game state dynamically.
"""

GAME_TOOLS = [
    {
        "name": "get_location_data",
        "description": "Fetch the static description and available elements for a game location. Use this to get details about any location in the game world.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "string",
                    "description": "The unique identifier for the location"
                }
            },
            "required": ["location_id"]
        }
    },
    {
        "name": "get_game_state",
        "description": "Fetch the current player state including their location, inventory, stats, and progress. Use this at the start of interactions to understand where the player is and what they have.",
        "input_schema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The unique conversation/game session identifier"
                }
            },
            "required": ["conversation_id"]
        }
    },
    {
        "name": "update_game_state",
        "description": "Update the player's game state after they perform actions. Use this to persist changes like moving to a new location, picking up items, or updating stats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The unique conversation/game session identifier"
                },
                "changes": {
                    "type": "object",
                    "description": "Object containing state fields to update. Valid fields: current_location (string), inventory (array of strings), visited_locations (array of strings), player_stats (object), flags (object)"
                }
            },
            "required": ["conversation_id", "changes"]
        }
    },
    {
        "name": "restart_game",
        "description": "Restart the game from the beginning. Clears all progress including chat history, inventory, and location. Use when the player explicitly asks to restart or start over.",
        "input_schema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "The conversation/game session ID"
                }
            },
            "required": ["conversation_id"]
        }
    }
]
