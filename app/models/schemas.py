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


# Notification schemas
class NotificationCreate(BaseModel):
    """Request body for creating a notification."""

    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=2000)
    notification_type: str = Field(default="info")
    ttl_hours: int = Field(default=168, ge=1, le=8760)  # Default 7 days, max 1 year


class NotificationResponse(BaseModel):
    """Response schema for a notification."""

    id: str
    title: str
    message: str
    notification_type: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# Feedback schemas
class FeedbackEnabledResponse(BaseModel):
    """Response for GET /api/feedback/enabled."""

    enabled: bool


class FeedbackRequest(BaseModel):
    """Request body for POST /api/feedback."""

    message: str = Field(..., min_length=1, max_length=5000)
    rating: int = Field(..., ge=1, le=5)


class FeedbackResponse(BaseModel):
    """Response for successful feedback submission."""

    success: bool
    message: str
