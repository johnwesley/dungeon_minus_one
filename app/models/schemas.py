from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Request schemas
class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None


class CreateConversationRequest(BaseModel):
    """Request body for POST /api/conversations."""

    title: Optional[str] = None


# Response schemas
class MessageResponse(BaseModel):
    """Response schema for a message."""

    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response schema for a conversation (list view)."""

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Response schema for a conversation with messages."""

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response for non-streaming chat (not used with SSE)."""

    conversation_id: str
    user_message: MessageResponse
    message: MessageResponse


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    code: str
