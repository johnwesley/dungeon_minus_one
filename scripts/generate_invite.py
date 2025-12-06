import asyncio
import sys
import os
import uuid

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory
from app.models.database import InviteCode

async def generate_invite():
    async with async_session_factory() as session:
        code = str(uuid.uuid4())[:8]
        invite = InviteCode(code=code)
        session.add(invite)
        await session.commit()
        print(f"Invite Code Generated: {code}")

if __name__ == "__main__":
    asyncio.run(generate_invite())

