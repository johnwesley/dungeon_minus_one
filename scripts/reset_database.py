import argparse
import asyncio
import os
import sys

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import Base, engine


async def reset_database() -> None:
    from app.models import database as _models  # noqa: F401

    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Drop and recreate all database tables.")
    parser.add_argument("--force", action="store_true", help="Confirm destructive reset")
    args = parser.parse_args()

    if not args.force:
        print("Refusing to reset without --force", file=sys.stderr)
        return 1

    asyncio.run(reset_database())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
