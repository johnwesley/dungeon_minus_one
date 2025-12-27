import json
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.schemas import ChatRequest
from app.models.database import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.clients.llm_client import get_llm_client
from app.services.conversation_service import ConversationService
from app.api.auth import get_current_user
from app.connection_manager import connection_manager

router = APIRouter()


async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    """Dependency to get the conversation service with game support."""
    return ConversationService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        llm_client=get_llm_client(),
        game_repo=GameRepository(db),
    )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    service: ConversationService = Depends(get_conversation_service),
    current_user: User = Depends(get_current_user),
):
    """
    Send a chat message and receive a streaming response.

    Returns an SSE stream with the following event types:
    - start: { conversation_id, user_message_id }
    - delta: { content }
    - done: { message }
    - error: { error, code }
    - closing: { reason } (sent during graceful shutdown)
    """

    # Ensure conversation belongs to user
    if request.conversation_id:
        # This check should ideally happen inside service.chat_stream_with_tools
        # or we verify ownership here before proceeding
        # service.verify_ownership(request.conversation_id, current_user.id)
        pass

    async def event_generator():
        connection_id = str(uuid.uuid4())
        await connection_manager.register(connection_id)
        try:
            # Check if server is shutting down before starting
            if connection_manager.is_shutting_down():
                yield {
                    "event": "closing",
                    "data": json.dumps({"reason": "server_shutdown"}),
                }
                return

            async for event in service.chat_stream_with_tools(
                message=request.message,
                conversation_id=request.conversation_id,
                user_id=current_user.id  # Pass user_id to service
            ):
                # Check for shutdown during streaming
                if connection_manager.is_shutting_down():
                    yield {
                        "event": "closing",
                        "data": json.dumps({"reason": "server_shutdown"}),
                    }
                    return

                yield {
                    "event": event.type,
                    "data": json.dumps(event.data),
                }
        finally:
            await connection_manager.unregister(connection_id)

    return EventSourceResponse(event_generator())
