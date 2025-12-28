"""Feedback API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.database import User
from app.models.schemas import (
    FeedbackEnabledResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.email_service import EmailService
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/feedback/enabled", response_model=FeedbackEnabledResponse)
async def check_feedback_enabled():
    """Check if feedback feature is enabled.

    This endpoint does not require authentication so the frontend
    can check before showing the feedback form.
    """
    settings = get_settings()
    return FeedbackEnabledResponse(enabled=settings.feedback_enabled)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    data: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit user feedback.

    Requires authentication. The logged-in user's username is included
    in the feedback email. Returns 404 if feedback is disabled.
    """
    settings = get_settings()

    # Check if feedback is enabled
    if not settings.feedback_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not available",
        )

    # Send email
    email_service = EmailService()

    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback service is not configured",
        )

    success = await email_service.send_feedback_email(
        username=current_user.username,
        rating=data.rating,
        message=data.message,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send feedback",
        )

    return FeedbackResponse(
        success=True,
        message="Thank you for your feedback!",
    )
