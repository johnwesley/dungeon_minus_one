import asyncio
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory
from app.models.database import User
from app.services.auth_service import get_password_hash
from sqlalchemy import select

async def create_admin(username, password):
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            print(f"User '{username}' already exists.")
            return

        admin_user = User(
            username=username,
            hashed_password=get_password_hash(password),
            is_admin=True
        )
        session.add(admin_user)
        await session.commit()
        print(f"Admin user '{username}' created successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <username> <password>")
        sys.exit(1)
        
    username = sys.argv[1]
    password = sys.argv[2]
    
    asyncio.run(create_admin(username, password))

