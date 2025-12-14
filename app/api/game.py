from typing import Union, Any
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
    inventory: list[Union[str, dict[str, Any]]]  # All items including treasures (strings or objects)
    trophy_case: list[str]         # Deposited treasures from flags.trophy_case
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
            trophy_case=[],
        )

    # Get full inventory (including treasures player is carrying)
    inventory = state.inventory or []

    # Get trophy case contents from flags
    flags = state.flags or {}
    trophy_case = flags.get("trophy_case", [])

    return GameStateResponse(
        current_location=state.current_location or "Unknown",
        inventory=inventory,
        trophy_case=trophy_case,
    )
