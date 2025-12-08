from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.database import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.game_repository import GameRepository
from app.api.auth import get_current_user

router = APIRouter()

# Treasure IDs required for victory (from narrator.md)
TREASURE_IDS = {
    "platinum_bar", "gold_coffin", "ivory_torch", "crystal_trident",
    "trunk_of_jewels", "bag_of_coins", "pot_of_gold", "jade_figurine",
    "chalice", "jeweled_egg", "sapphire_bracelet", "crystal_skull", "scarab"
}
TOTAL_TREASURES = 13


class GameStateResponse(BaseModel):
    current_location: str
    inventory: list[str]
    treasures_found: list[str]
    total_treasures: int = TOTAL_TREASURES


@router.get("/conversations/{conversation_id}/game-state", response_model=GameStateResponse)
async def get_game_state(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get game state for a conversation."""
    # Verify ownership
    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get(conversation_id)

    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get game state
    game_repo = GameRepository(db)
    state = await game_repo.get_state(conversation_id)

    if not state:
        return GameStateResponse(
            current_location="Unknown",
            inventory=[],
            treasures_found=[],
        )

    # Get inventory and separate treasures from regular items
    inventory = state.inventory or []
    treasures_in_inventory = [item for item in inventory if item in TREASURE_IDS]
    regular_inventory = [item for item in inventory if item not in TREASURE_IDS]

    # Get treasures deposited in living room (trophy case)
    living_room = await game_repo.get_location("living_room")
    treasures_in_living_room = []
    if living_room and living_room.get("interactables"):
        treasures_in_living_room = [
            item for item in living_room["interactables"] if item in TREASURE_IDS
        ]

    # Combine all found treasures (no duplicates)
    treasures_found = list(set(treasures_in_inventory + treasures_in_living_room))

    return GameStateResponse(
        current_location=state.current_location or "Unknown",
        inventory=regular_inventory,
        treasures_found=treasures_found,
    )
