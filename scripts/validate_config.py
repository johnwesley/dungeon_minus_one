import argparse
import asyncio
import os
import sys
from typing import Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from sqlalchemy import text

from app.config import get_settings, validate_settings
from app.database import async_session_factory


def describe_database_url(url: Optional[str]) -> str:
    if not url:
        return "unset"
    scheme = url.split(":", 1)[0]
    if scheme.startswith("sqlite"):
        return f"{scheme} (local file)"
    return f"{scheme} (set)"


async def check_db() -> None:
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate app configuration.")
    parser.add_argument(
        "--db-check",
        action="store_true",
        help="Run a lightweight DB connectivity check.",
    )
    args = parser.parse_args()

    settings = get_settings()
    errors: list[str] = []

    try:
        validate_settings(settings)
    except Exception as exc:
        errors.append(str(exc))

    print(f"Environment: {settings.environment}")
    print(f"Database URL: {describe_database_url(settings.database_url)}")
    print(f"DB auto-create: {settings.db_auto_create}")

    if args.db_check:
        try:
            asyncio.run(check_db())
            print("DB check: ok")
        except Exception as exc:
            errors.append(f"Database check failed: {exc}")
            print("DB check: failed")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Config validation: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
