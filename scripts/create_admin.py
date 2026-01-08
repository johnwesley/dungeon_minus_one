import argparse
import asyncio
import os
import sys

# Add project root to Python path
sys.path.append(os.getcwd())

from sqlalchemy import select

from app.database import async_session_factory
from app.models.database import User
from app.services.auth_service import get_password_hash


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def create_admin(username: str, password: str, email: str | None) -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"User '{username}' already exists.")
            return

        email_normalized = _normalize_email(email) if email else None
        admin_user = User(
            username=username,
            email=email,
            email_normalized=email_normalized,
            hashed_password=get_password_hash(password),
            is_admin=True,
        )
        session.add(admin_user)
        await session.commit()
        print(f"Admin user '{username}' created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--email", help="Optional email for the admin account")
    args = parser.parse_args()

    asyncio.run(create_admin(args.username, args.password, args.email))
