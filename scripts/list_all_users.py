import asyncio
import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import select
from app.database import async_session_factory
from app.models.database import User
from app.config import get_settings

async def main():
    settings = get_settings()
    print(f"Script DB URL: {settings.database_url}")
    
    print("Listing all users in DB...")
    async with async_session_factory() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f" - User: {u.username} (ID: {u.id})")
            
        if not users:
            print(" - No users found.")

if __name__ == "__main__":
    asyncio.run(main())
