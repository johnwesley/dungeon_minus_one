from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Notification, NotificationDismissal


class NotificationRepository:
    """Repository for notification operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        title: str,
        message: str,
        ttl_hours: int = 168,
        notification_type: str = "info",
    ) -> Notification:
        """Create a new notification with TTL."""
        notification = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_active_for_user(self, user_id: str) -> list[Notification]:
        """Get all active (non-expired, non-dismissed) notifications for a user."""
        # Get IDs of notifications this user has dismissed
        dismissed_result = await self.session.execute(
            select(NotificationDismissal.notification_id).where(
                NotificationDismissal.user_id == user_id
            )
        )
        dismissed_ids = [row[0] for row in dismissed_result.fetchall()]

        # Get active notifications not in dismissed list
        query = select(Notification).where(
            Notification.expires_at > datetime.utcnow()
        )
        if dismissed_ids:
            query = query.where(Notification.id.notin_(dismissed_ids))

        query = query.order_by(Notification.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def dismiss(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as dismissed for a user."""
        # Check if already dismissed
        existing = await self.session.execute(
            select(NotificationDismissal).where(
                NotificationDismissal.notification_id == notification_id,
                NotificationDismissal.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            return True  # Already dismissed

        dismissal = NotificationDismissal(
            notification_id=notification_id,
            user_id=user_id,
        )
        self.session.add(dismissal)
        await self.session.flush()
        return True

    async def delete(self, notification_id: str) -> bool:
        """Delete a notification (admin only)."""
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            await self.session.delete(notification)
            return True
        return False
