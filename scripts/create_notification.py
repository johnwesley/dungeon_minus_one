#!/usr/bin/env python3
"""Create a notification from the command line."""

import asyncio
import sys
import os
import argparse

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory, init_db
from app.repositories.notification_repository import NotificationRepository


async def create_notification(title: str, message: str, ttl_hours: int, notification_type: str):
    # Ensure tables exist
    await init_db()

    async with async_session_factory() as session:
        repo = NotificationRepository(session)
        notification = await repo.create(
            title=title,
            message=message,
            ttl_hours=ttl_hours,
            notification_type=notification_type,
        )
        await session.commit()
        print(f"Notification created:")
        print(f"  ID: {notification.id}")
        print(f"  Title: {notification.title}")
        print(f"  Type: {notification.notification_type}")
        print(f"  Expires: {notification.expires_at}")


def main():
    parser = argparse.ArgumentParser(description="Create a notification")
    parser.add_argument("title", help="Notification title")
    parser.add_argument("message", help="Notification message")
    parser.add_argument(
        "--ttl",
        type=int,
        default=168,
        help="Time to live in hours (default: 168 = 7 days)",
    )
    parser.add_argument(
        "--type",
        dest="notification_type",
        default="info",
        choices=["info", "warning", "success", "error"],
        help="Notification type (default: info)",
    )

    args = parser.parse_args()
    asyncio.run(
        create_notification(
            args.title,
            args.message,
            args.ttl,
            args.notification_type,
        )
    )


if __name__ == "__main__":
    main()
