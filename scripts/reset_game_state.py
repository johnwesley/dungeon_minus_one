import asyncio
import sys
import os
from sqlalchemy import delete

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory
from app.models.database import GameState, Message, Conversation

async def reset_game_state():
    print("Resetting game state (keeping locations)...")
    async with async_session_factory() as session:
        # Delete in order of dependency (though CASCADE might handle it, explicit is safer)
        
        # Delete GameStates
        print("Deleting GameStates...")
        await session.execute(delete(GameState))
        
        # Delete Messages
        print("Deleting Messages...")
        await session.execute(delete(Message))
        
        # Delete Conversations
        print("Deleting Conversations...")
        await session.execute(delete(Conversation))
        
        await session.commit()
        print("Game state reset complete. Locations preserved.")

if __name__ == "__main__":
    asyncio.run(reset_game_state())

