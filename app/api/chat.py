import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.schemas import ChatRequest
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.clients.llm_client import get_llm_client
from app.services.conversation_service import ConversationService

router = APIRouter()


async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    """Dependency to get the conversation service."""
    return ConversationService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
        llm_client=get_llm_client(),
    )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Send a chat message and receive a streaming response.

    Returns an SSE stream with the following event types:
    - start: { conversation_id, user_message_id }
    - delta: { content }
    - done: { message }
    - error: { error, code }
    """

    async def event_generator():
        async for event in service.chat_stream(
            message=request.message,
            conversation_id=request.conversation_id,
        ):
            yield {
                "event": event.type,
                "data": json.dumps(event.data),
            }

    return EventSourceResponse(event_generator())
