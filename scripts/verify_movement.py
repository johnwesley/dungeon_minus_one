import asyncio
import sys
import os
import uuid
from sqlalchemy import select

# Add project root to Python path
sys.path.append(os.getcwd())

from app.database import async_session_factory
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.services.conversation_service import ConversationService
from app.clients.llm_client import get_llm_client
from app.models.database import GameState, User

async def run_verification():
    print("Starting movement verification...")
    
    # Get target username from env or default to 'admin'
    target_username = os.environ.get("TARGET_USER", "admin")
    
    async with async_session_factory() as session:
        # Initialize dependencies
        game_repo = GameRepository(session)
        conversation_repo = ConversationRepository(session)
        message_repo = MessageRepository(session)
        llm_client = get_llm_client()
        
        service = ConversationService(
            conversation_repo=conversation_repo,
            message_repo=message_repo,
            llm_client=llm_client,
            game_repo=game_repo
        )

        # Find user
        print(f"Looking for user: {target_username}")
        result = await session.execute(select(User).where(User.username == target_username))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User '{target_username}' not found. Falling back to first available user.")
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
        if not user:
            print("No users found in database. Creating test user...")
            user = User(
                id=str(uuid.uuid4()),
                username="test_runner",
                hashed_password="dummy_password_hash",
                is_active=True
            )
            session.add(user)
            await session.commit()
            
        print(f"Using user: {user.username} (ID: {user.id})")
        user_id = user.id

        # Sequence from Walkthrough Phase 1
        steps = [
            ("Wake up", "start"),
            ("north", "north_of_house"),
            ("east", "behind_house"),
            ("inside", "kitchen"),
            ("take brown sack", "kitchen"), 
            ("look in sack", "kitchen"),
            ("take garlic", "kitchen"),
            ("take lunch", "kitchen"),
            ("up", "attic"),
            ("take rope", "attic"),
            ("take nasty knife", "attic"),
            ("down", "kitchen"),
            ("west", "living_room"),
            ("take brass lantern", "living_room"),
            ("turn on lantern", "living_room"),
            ("take elvish sword", "living_room"),
        ]

        print(f"Running {len(steps)} steps...")
        
        conversation_id = None
        failures = []
        
        for i, (command, expected_loc) in enumerate(steps):
            print(f"\nStep {i+1}: User says '{command}'")
            print(f"  Expect location: {expected_loc}")
            
            full_response = ""
            async for event in service.chat_stream_with_tools(
                message=command,
                conversation_id=conversation_id,
                user_id=user_id
            ):
                if event.type == "start":
                    if conversation_id is None:
                        conversation_id = event.data["conversation_id"]
                        print(f"  --> Conversation Created: {conversation_id}")
                        print(f"  --> Refresh your browser to see this chat under user '{user.username}'")
                elif event.type == "delta":
                    full_response += event.data["content"]
                elif event.type == "progress":
                     print(f"  [Tool Use] {event.data}")
                elif event.type == "error":
                     print(f"  [Error] {event.data}")

            print(f"  Narrator: {full_response[:100]}..." if len(full_response) > 100 else f"  Narrator: {full_response}")
            
            # Commit session to ensure all changes are flushed and visible
            await session.commit()
            
            # Check state
            state = await game_repo.get_state(conversation_id)
            if state:
                print(f"  Actual location: {state.current_location}")
                if state.current_location == expected_loc:
                    print("  ✅ Location matches")
                else:
                    error_msg = f"Step {i+1} ('{command}'): Expected {expected_loc}, got {state.current_location}"
                    print(f"  ❌ LOCATION MISMATCH! {error_msg}")
                    failures.append(error_msg)
            else:
                error_msg = f"Step {i+1} ('{command}'): No game state found!"
                print(f"  ❌ {error_msg}")
                failures.append(error_msg)
        
        print("\n" + "="*50)
        if failures:
            print(f"❌ Verification FAILED with {len(failures)} errors:")
            for failure in failures:
                print(f"  - {failure}")
            sys.exit(1)
        else:
            print("✅ Verification PASSED: All steps matched expected locations.")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_verification())
