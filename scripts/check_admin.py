import asyncio
import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import select
from app.database import async_session_factory
from app.models.database import User

async def main():
    print(f"Connecting to DB...")
    try:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.username == "admin"))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"User found:")
                print(f"  ID: {user.id}")
                print(f"  Username: {user.username}")
                print(f"  Email: {user.email}")
                print(f"  Is Admin: {user.is_admin}")
                print(f"  Is Active: {user.is_active}")
                print(f"  Password Hash: {user.hashed_password[:10]}...")
            else:
                print("User 'admin' NOT found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
