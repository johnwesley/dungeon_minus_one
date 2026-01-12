import asyncio
import os
import sys

sys.path.append(os.getcwd())

from sqlalchemy import select, or_
from app.database import async_session_factory
from app.models.database import User
from app.services.auth_service import verify_password

async def main():
    identifier = "admin"
    password = "password"
    
    print(f"Verifying credentials for '{identifier}' with password '{password}'...")
    
    async with async_session_factory() as session:
        # 1. Fetch User
        stmt = select(User).where(
            or_(User.username == identifier, User.email_normalized == identifier.lower())
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User NOT FOUND in database.")
            return

        print(f"✅ User found: {user.username} (ID: {user.id})")
        print(f"   Hash in DB: {user.hashed_password}")

        # 2. Verify Password
        is_valid = verify_password(password, user.hashed_password)
        
        if is_valid:
            print("✅ Password verification PASSED.")
        else:
            print("❌ Password verification FAILED.")
            
            # Debug: Try generating a new hash and seeing if it matches logic
            from app.services.auth_service import get_password_hash
            new_hash = get_password_hash(password)
            print(f"   New hash for '{password}' would be: {new_hash}")
            print("   (If this verify fails, the stored hash might be corrupted or from a different context)")

if __name__ == "__main__":
    asyncio.run(main())
