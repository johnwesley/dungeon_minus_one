import asyncio
import sys
import os
import uuid
import json
import time
from sqlalchemy import select

# Add project root to Python path
sys.path.append(os.getcwd())

# Debug flag - set DEBUG_MESSAGES=true to log full context at each step
DEBUG_MESSAGES = os.environ.get("DEBUG_MESSAGES", "").lower() == "true"
DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), "movement_debug.log")

from app.database import async_session_factory
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.services.conversation_service import ConversationService
from app.clients.llm_client import get_llm_client
from app.models.database import GameState, User, Message


def log_debug(data: dict):
    """Write debug data to log file as JSON line."""
    if not DEBUG_MESSAGES:
        return
    try:
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception as e:
        print(f"  [Debug Log Error] {e}")

async def run_verification():
    print("Starting FULL movement verification...")

    # Clear debug log at start
    if DEBUG_MESSAGES:
        print(f"DEBUG MODE ENABLED - Logging to {DEBUG_LOG_PATH}")
        with open(DEBUG_LOG_PATH, "w") as f:
            f.write("")  # Clear file

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
            print(f"User '{target_username}' not found. Creating dedicated test user...")
            user = User(
                id=str(uuid.uuid4()),
                username=target_username,
                hashed_password="dummy_password_hash",
                is_active=True
            )
            session.add(user)
            await session.commit()
            
        print(f"Using user: {user.username} (ID: {user.id})")
        user_id = user.id

        # FULL Sequence from Walkthrough.md
        steps = [
            # 1) House Entry + Key Items
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

            # 2) Visit South Side of House
            ("east", "kitchen"),
            ("out", "behind_house"),
            ("west", "south_of_house"),
            ("north", "start"),

            # 3) Forest Loop (Egg)
            ("north", "north_of_house"),
            ("north", "forest_path"),
            ("up", "up_a_tree"),
            ("take jeweled egg", "up_a_tree"),
            ("down", "forest_path"),
            ("east", "forest"),
            ("north", "clearing"),

            # 4) Canyon + Rainbow + River
            ("east", "canyon_view"),
            ("down", "rocky_ledge"),
            ("down", "canyon_bottom"),
            ("north", "end_of_rainbow"),
            ("take pot of gold", "end_of_rainbow"),
            ("east", "aragain_falls"),
            ("north", "shore"),
            ("north", "sandy_beach"),
            ("take shovel", "sandy_beach"),
            ("northeast", "sandy_cave"),
            ("dig sand with shovel", "sandy_cave"),
            ("take scarab", "sandy_cave"),
            ("southwest", "sandy_beach"),

            # 5) Dam Loop + Loud Room
            ("north", "dam_base"),
            ("take plastic boat", "dam_base"), # Optional/extra but in walkthrough
            ("up", "dam"),
            ("north", "dam_lobby"),
            ("north", "maintenance_room"),
            ("take wrench", "maintenance_room"),
            ("take screwdriver", "maintenance_room"),
            ("south", "dam_lobby"),
            ("south", "dam"),
            ("use wrench on bolt", "dam"), # Drains reservoir
            ("south", "deep_canyon"),
            ("down", "loud_room"),
            ("take platinum bar", "loud_room"),
            ("west", "round_room"),
            ("west", "east_west_passage"),
            ("north", "chasm"),
            ("northeast", "reservoir_south"),

            # 6) Reservoir + Atlantis
            ("north", "reservoir"),
            ("take trunk of jewels", "reservoir"),
            ("north", "reservoir_north"),
            ("take air pump", "reservoir_north"),
            ("north", "atlantis_room"),
            ("take crystal trident", "atlantis_room"),
            ("south", "reservoir_north"),
            ("south", "reservoir"),
            ("south", "reservoir_south"),

            # 7) Troll Room + Deposit (troll_incapacitated flag pre-set)
            ("southwest", "chasm"),
            ("south", "east_west_passage"),
            ("west", "troll_room"),
            ("south", "cellar"),
            ("up", "living_room"),
            ("put jeweled egg in trophy case", "living_room"),
            ("put pot of gold in trophy case", "living_room"),
            ("put scarab in trophy case", "living_room"),
            ("put platinum bar in trophy case", "living_room"),
            ("put trunk of jewels in trophy case", "living_room"),
            ("put crystal trident in trophy case", "living_room"),

            # 8) House Lower Rooms
            ("east", "kitchen"),
            ("down", "studio"),
            ("south", "gallery"),
            ("west", "east_of_chasm"),
            ("east", "gallery"),
            ("north", "studio"),
            ("up", "kitchen"),
            ("west", "living_room"),

            # 9) Maze + Grating + Treasure Room
            ("down", "cellar"),
            ("north", "troll_room"),
            ("west", "maze_entrance"),
            ("west", "maze_dead_end"),
            ("east", "maze_entrance"),
            ("south", "maze_twist"),
            ("up", "maze_skeleton"),
            ("take bag of coins", "maze_skeleton"),
            ("take skeleton key", "maze_skeleton"),
            ("northeast", "grating_room"),
            ("unlock grating with skeleton key", "grating_room"),
            ("up", "clearing"),
            ("down", "grating_room"),
            ("southwest", "maze_skeleton"),
            ("down", "maze_twist"),
            ("east", "maze_bones"),
            ("southeast", "cyclops_room"),
            ("up", "treasure_room"),  # cyclops_defeated flag pre-set
            ("take chalice", "treasure_room"),  # thief_defeated flag pre-set
            ("down", "cyclops_room"),
            ("east", "strange_passage"),
            ("east", "living_room"),
            ("put bag of coins in trophy case", "living_room"),
            ("put chalice in trophy case", "living_room"),

            # 10) Temple + Hades
            ("down", "cellar"),
            ("north", "troll_room"),
            ("east", "east_west_passage"),
            ("east", "round_room"),
            ("southeast", "engravings_cave"),
            ("east", "dome_room"),
            ("down", "torch_room"),
            ("take ivory torch", "torch_room"),
            ("south", "temple"),
            ("take brass bell", "temple"),
            ("east", "egyptian_room"),
            ("take gold coffin", "egyptian_room"),
            ("west", "temple"),
            ("south", "altar"),
            ("take candles", "altar"),
            ("take black book", "altar"),
            ("down", "cave"),
            ("down", "entrance_to_hades"),
            ("south", "land_of_the_dead"),  # spirits_banished flag pre-set
            ("take crystal skull", "land_of_the_dead"),
            ("north", "entrance_to_hades"),
            ("up", "cave"),

            # 11) Mine Loop
            # NOTE: Gas room contains coal gas - any open flame causes explosion!
            # Must: drop ivory torch, turn off lantern, flip switch for electric light
            ("north", "mirror_room"),
            ("north", "cold_passage"),
            ("east", "mine_entrance"),
            ("west", "squeaky_room"),
            ("north", "bat_room"),
            ("take jade figurine", "bat_room"),  # bat_pacified flag pre-set
            ("east", "shaft_room"),
            ("north", "smelly_room"),
            ("drop ivory torch", "smelly_room"),  # Leave torch before gas room
            ("turn off lantern", "smelly_room"),  # No flame in gas room!
            ("flip switch", "smelly_room"),       # Turn on gas room electric light
            ("down", "gas_room"),                 # Safe: electric light, no flame
            ("take sapphire bracelet", "gas_room"),
            ("east", "coal_mine"),
            ("turn on lantern", "coal_mine"),     # Safe to light outside gas room
            ("down", "ladder_top"),
            ("down", "ladder_bottom"),
            ("south", "dead_end"),
            ("north", "ladder_bottom"),
            ("west", "timber_room"),
            ("west", "drafty_room"),
            ("south", "machine_room"),
            ("north", "drafty_room"),
            ("east", "timber_room"),
            ("east", "ladder_bottom"),
            ("up", "ladder_top"),
            ("up", "coal_mine"),
            ("turn off lantern", "coal_mine"),    # Prepare to re-enter gas room
            ("west", "gas_room"),                 # Safe: electric light still on
            ("up", "smelly_room"),
            ("turn on lantern", "smelly_room"),   # Safe outside gas room
            ("take ivory torch", "smelly_room"),  # Recover torch
            ("south", "shaft_room"),
            ("west", "bat_room"),
            ("south", "squeaky_room"),
            ("east", "mine_entrance"),
            ("south", "slide_room"),
            ("down", "cellar"),
            ("up", "living_room"),

            # 12) Final Deposits + Victory
            ("put ivory torch in trophy case", "living_room"),
            ("put gold coffin in trophy case", "living_room"),
            ("put crystal skull in trophy case", "living_room"),
            ("put jade figurine in trophy case", "living_room"),
            ("put sapphire bracelet in trophy case", "living_room"),
            ("enter vault", "victory"),
        ]

        print(f"Running {len(steps)} steps...")

        conversation_id = None
        failures = []
        retries_succeeded = 0
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3

        async def send_command(cmd):
            """Send a command and return (full_response, tool_calls_observed)."""
            nonlocal conversation_id
            resp = ""
            tools = []
            async for event in service.chat_stream_with_tools(
                message=cmd,
                conversation_id=conversation_id,
                user_id=user_id
            ):
                if event.type == "start":
                    if conversation_id is None:
                        conversation_id = event.data["conversation_id"]
                        print(f"  --> Conversation Created: {conversation_id}")
                elif event.type == "delta":
                    resp += event.data["content"]
                elif event.type == "progress":
                    print(f"  [Tool Use] {event.data}")
                    if event.data.get("step") == "using_tool":
                        tools.append(event.data.get("tool"))
                elif event.type == "error":
                    print(f"  [Error] {event.data}")
            return resp, tools

        for i, (command, expected_loc) in enumerate(steps):
            print(f"\nStep {i+1}: User says '{command}'")
            print(f"  Expect location: {expected_loc}")

            # DEBUG: Log state BEFORE the action
            state_before = None
            messages_before = []
            if DEBUG_MESSAGES and conversation_id:
                state_before = await game_repo.get_state(conversation_id)
                # Fetch message history that will be sent
                result = await session.execute(
                    select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
                )
                all_messages = result.scalars().all()
                # Apply same sliding window as conversation_service (last 20)
                if len(all_messages) > 20:
                    all_messages = all_messages[-20:]
                messages_before = [{"role": m.role, "content": m.content[:200] + "..." if len(m.content) > 200 else m.content} for m in all_messages]

            full_response, tool_calls_observed = await send_command(command)

            print(f"  Narrator: {full_response[:100]}..." if len(full_response) > 100 else f"  Narrator: {full_response}")

            # Commit session to ensure all changes are flushed and visible
            await session.commit()

            # After first step completes, set NPC bypass flags
            if i == 0 and conversation_id:
                print(f"  --> Setting NPC bypass flags for movement testing...")
                await game_repo.update_state(conversation_id, {
                    "flags": {
                        # Troll Room - allows passage south/east/west
                        "troll_incapacitated": True,
                        # Cyclops Room - allows access to staircase (up)
                        "cyclops_defeated": True,
                        # Treasure Room (Thief) - allows taking chalice
                        "thief_defeated": True,
                        # Entrance to Hades (Spirits) - allows passage south to land_of_the_dead
                        "spirits_banished": True,
                        # Bat Room - allows taking jade figurine
                        "bat_pacified": True,
                        # Lantern already lit for dark locations
                        "lantern_lit": True,
                    }
                })
                await session.commit()
                # Verify flags were set
                verify_state = await game_repo.get_state(conversation_id)
                if verify_state and verify_state.flags:
                    print(f"  --> NPC bypass flags confirmed: {list(verify_state.flags.keys())}")
                else:
                    print(f"  --> WARNING: Flags may not have been set correctly")

            # Check state
            state = await game_repo.get_state(conversation_id)
            location_match = False
            if state:
                print(f"  Actual location: {state.current_location}")
                # Debug: Show flags if in DEBUG mode
                if DEBUG_MESSAGES and state.flags:
                    print(f"  DEBUG Flags: {state.flags}")
                if state.current_location == expected_loc:
                    print("  ✅ Location matches")
                    location_match = True
                    consecutive_failures = 0  # Reset on success
                else:
                    # Retry once before counting as failure
                    print(f"  ⚠️  Location mismatch (got {state.current_location}), retrying...")
                    retry_response, retry_tools = await send_command(command)
                    await session.commit()
                    print(f"  Narrator (retry): {retry_response[:100]}..." if len(retry_response) > 100 else f"  Narrator (retry): {retry_response}")
                    state = await game_repo.get_state(conversation_id)
                    if state and state.current_location == expected_loc:
                        print("  ✅ Location matches after retry")
                        location_match = True
                        retries_succeeded += 1
                        consecutive_failures = 0
                        tool_calls_observed = retry_tools
                        full_response = retry_response
                    else:
                        actual = state.current_location if state else "unknown"
                        error_msg = f"Step {i+1} ('{command}'): Expected {expected_loc}, got {actual}"
                        print(f"  ❌ LOCATION MISMATCH! {error_msg}")
                        if state and state.flags:
                            print(f"  Current flags: {state.flags}")
                        failures.append(error_msg)
                        consecutive_failures += 1
            else:
                error_msg = f"Step {i+1} ('{command}'): No game state found!"
                print(f"  ❌ {error_msg}")
                failures.append(error_msg)
                consecutive_failures += 1

            # Stop after MAX_CONSECUTIVE_FAILURES consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"\n⛔ Stopping after {MAX_CONSECUTIVE_FAILURES} consecutive failures")
                break

            # DEBUG: Log comprehensive step data
            if DEBUG_MESSAGES:
                log_debug({
                    "timestamp": int(time.time() * 1000),
                    "step": i + 1,
                    "command": command,
                    "expected_location": expected_loc,
                    "state_before": {
                        "location": state_before.current_location if state_before else None,
                        "inventory_count": len(state_before.inventory) if state_before and state_before.inventory else 0,
                        "flags": state_before.flags if state_before else None,
                    } if state_before else None,
                    "messages_in_context": len(messages_before),
                    "messages_preview": messages_before[-3:] if messages_before else [],  # Last 3 messages
                    "tool_calls_observed": tool_calls_observed,
                    "response_preview": full_response[:300] if full_response else "",
                    "state_after": {
                        "location": state.current_location if state else None,
                        "inventory_count": len(state.inventory) if state and state.inventory else 0,
                        "flags": state.flags if state else None,
                    } if state else None,
                    "location_match": location_match,
                    "has_update_game_state_call": "update_game_state" in tool_calls_observed,
                })
        
        print("\n" + "="*50)
        if retries_succeeded:
            print(f"🔄 {retries_succeeded} step(s) succeeded after retry")
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
