import argparse
import asyncio
import os
import sys

# Add project root to Python path
sys.path.append(os.getcwd())

from sqlalchemy import delete

from app.database import async_session_factory
from app.models.database import (
    Conversation,
    GameState,
    InviteCode,
    InviteRequest,
    Message,
    NotificationDismissal,
    RateLimitEntry,
    User,
    UserSession,
)


async def reset_auth(force: bool) -> None:
    if not force:
        raise SystemExit("Refusing to reset without --force")

    async with async_session_factory() as session:
        # Delete in dependency order
        await session.execute(delete(NotificationDismissal))
        await session.execute(delete(Message))
        await session.execute(delete(GameState))
        await session.execute(delete(Conversation))
        await session.execute(delete(UserSession))
        await session.execute(delete(InviteRequest))
        await session.execute(delete(InviteCode))
        await session.execute(delete(User))
        await session.execute(delete(RateLimitEntry))
        await session.commit()
        print("Auth-related data wiped (users, invites, sessions, requests).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset auth-related tables (dangerous).")
    parser.add_argument("--force", action="store_true", help="Confirm destructive reset")
    args = parser.parse_args()

    asyncio.run(reset_auth(args.force))
