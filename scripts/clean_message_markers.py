import argparse
import asyncio
import os
from typing import Optional

from sqlalchemy import or_, select

from app.database import async_session_factory
from app.models.database import Message
from app.utils.message_sanitizer import strip_internal_markers


MARKERS = (
    "\n\n---\n[State:",
    "\n\n---\n[Tools used:",
)


async def clean_messages(dry_run: bool, limit: Optional[int]) -> int:
    async with async_session_factory() as session:
        query = select(Message).where(
            Message.role == "assistant",
            or_(
                Message.content.contains(MARKERS[0]),
                Message.content.contains(MARKERS[1]),
            ),
        ).order_by(Message.created_at)
        if limit:
            query = query.limit(limit)
        result = await session.execute(query)
        messages = result.scalars().all()

        updated = 0
        for message in messages:
            cleaned = strip_internal_markers(message.content)
            if cleaned != message.content:
                updated += 1
                if not dry_run:
                    message.content = cleaned

        if not dry_run:
            await session.commit()

        total = len(messages)
        action = "Would update" if dry_run else "Updated"
        print(f"Found {total} candidate messages. {action} {updated}.")
        return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove internal [State] / [Tools used] markers from assistant messages."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of messages scanned.")
    args = parser.parse_args()

    # Ensure .env is honored for DATABASE_URL (app.config handles loading)
    os.environ.setdefault("PYTHONASYNCIODEBUG", "0")

    asyncio.run(clean_messages(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
