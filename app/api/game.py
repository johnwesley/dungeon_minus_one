from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.database import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.game_repository import GameRepository
from app.api.auth import get_current_user

router = APIRouter()


class GameStateResponse(BaseModel):
    current_location: str
    inventory: list[str]


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
        return GameStateResponse(current_location="Unknown", inventory=[])

    return GameStateResponse(
        current_location=state.current_location or "Unknown",
        inventory=state.inventory or [],
    )
