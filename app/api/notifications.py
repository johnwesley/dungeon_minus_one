from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import User
from app.models.schemas import NotificationCreate, NotificationResponse
from app.repositories.notification_repository import NotificationRepository
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/notifications", response_model=list[NotificationResponse])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all active notifications for the current user."""
    repo = NotificationRepository(db)
    notifications = await repo.get_active_for_user(current_user.id)
    return notifications


@router.post("/notifications/{notification_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a notification for the current user."""
    repo = NotificationRepository(db)

    # Check notification exists
    notification = await repo.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await repo.dismiss(notification_id, current_user.id)
    await db.commit()


@router.post("/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new notification (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    repo = NotificationRepository(db)
    notification = await repo.create(
        title=data.title,
        message=data.message,
        ttl_hours=data.ttl_hours,
        notification_type=data.notification_type,
    )
    await db.commit()
    return notification
