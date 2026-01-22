from typing import AsyncIterator, Optional
from dataclasses import dataclass
import os
import json
import time
from app.repositories.conversation_repository import ConversationRepository

# Debug flag for state injection logging
DEBUG_SERVICE = os.environ.get("DEBUG_SERVICE", "").lower() == "true"
DEBUG_SERVICE_LOG_PATH = os.path.join(os.path.dirname(__file__), "../../.cursor/service_debug.log")


def log_service_debug(data: dict):
    """Write service debug data to log file as JSON line."""
    if not DEBUG_SERVICE:
        return
    try:
        os.makedirs(os.path.dirname(DEBUG_SERVICE_LOG_PATH), exist_ok=True)
        with open(DEBUG_SERVICE_LOG_PATH, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception:
        pass
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.clients.llm_client import LLMClient
from app.models.database import Conversation, Message, GameState
from app.services.game_tools import GameToolHandlers
from app.config import get_settings
from app.metrics import (
    LLM_SESSIONS_TOTAL,
    GAME_SESSION_DURATION_SECONDS,
    GAME_VICTORIES_TOTAL,
    GAME_RESTARTS_TOTAL,
    GAME_DEATHS_TOTAL,
)
from app.utils.message_sanitizer import strip_internal_markers
from app.utils.input_guard import evaluate_player_input


ENDING_ASCII = "[ PROCESS COMPLETE ]\n[ NO FURTHER INPUT ]\n\n>"
TREASURE_IDS = {
    "platinum_bar",
    "gold_coffin",
    "ivory_torch",
    "crystal_trident",
    "trunk_of_jewels",
    "bag_of_coins",
    "pot_of_gold",
    "jade_figurine",
    "chalice",
    "jeweled_egg",
    "sapphire_bracelet",
    "crystal_skull",
    "scarab",
}

NPC_TURN_DEFAULTS = {
    "max_turns": 5,
    "kill_player": True,
}

# Bypass flags that indicate an NPC has been dealt with
NPC_BYPASS_FLAGS = {
    "troll": ["troll_incapacitated", "troll_defeated", "troll_persuaded"],
    "cyclops": ["cyclops_defeated", "cyclops_confused", "cyclops_distracted"],
    "thief": ["thief_defeated", "thief_distracted"],
    "bat": ["bat_pacified", "bat_persuaded"],
    "spirits": ["spirits_banished"],
}


def _normalize_command(message: str) -> str:
    return " ".join(message.strip().lower().split())


def _npc_state_key(npc: dict) -> str:
    npc_id = str(npc.get("id") or "").strip().lower()
    if npc_id:
        return npc_id
    return str(npc.get("name") or "npc").strip().lower()


def _npc_has_bypass(npc_id: str, flags: dict) -> bool:
    """Check if an NPC has been bypassed (defeated, persuaded, etc.)."""
    bypass_flags = NPC_BYPASS_FLAGS.get(npc_id, [])
    return any(flags.get(flag) for flag in bypass_flags)


def _int_or_default(value: Optional[object], default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _resolve_turn_config(npc: dict) -> dict:
    """Resolve turn limit config for an NPC, falling back to defaults."""
    config = npc.get("turn_limits") or {}
    if config.get("enabled") is False:
        return {}

    max_turns = _int_or_default(config.get("max_turns"), NPC_TURN_DEFAULTS["max_turns"])
    if max_turns <= 0:
        return {}

    return {
        "max_turns": max_turns,
        "kill_player": config.get("kill_player", NPC_TURN_DEFAULTS["kill_player"]),
    }


def _is_restart_request(message: str) -> bool:
    cmd = _normalize_command(message)
    return cmd in {
        "restart",
        "[restart]",
        "start over",
        "start again",
        "begin again",
        "new game",
    }


def _mentions_trophy_case(cmd: str, location: Optional[str]) -> bool:
    if "trophy case" in cmd or "trophycase" in cmd or "trophy-case" in cmd:
        return True
    # Treat "case" as the trophy case when in the living room.
    if location == "living_room" and "case" in cmd:
        return True
    return False


def _is_trophy_case_removal(message: str, location: Optional[str]) -> bool:
    cmd = _normalize_command(message)
    if not _mentions_trophy_case(cmd, location):
        return False
    removal_verbs = ("take", "remove", "get", "pull", "withdraw")
    return any(cmd.startswith(v + " ") or f" {v} " in cmd for v in removal_verbs)


def _has_all_treasures(trophy_case: set[str]) -> bool:
    return TREASURE_IDS.issubset(trophy_case)


def _build_base_system_prompt(include_skills: bool = True) -> tuple[str, bool]:
    from prompts import load_prompt, load_all_skills, NARRATOR_PROMPT

    narrator_prompt = load_prompt(NARRATOR_PROMPT)
    try:
        premise_prompt = load_prompt("premise")
        base_system_text = f"{narrator_prompt}\n\n## Game Premise\n{premise_prompt}"
    except FileNotFoundError:
        base_system_text = narrator_prompt

    skills_content = ""
    if include_skills:
        skills_content = load_all_skills()
        if skills_content:
            base_system_text = (
                f"{base_system_text}\n\n## Game Mechanics (Skills)\n\n{skills_content}"
            )

    return base_system_text, bool(skills_content)


class ConversationNotFoundError(Exception):
    """Raised when a conversation is not found."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__(f"Conversation not found: {conversation_id}")


@dataclass
class ChatResult:
    """Result of a chat operation."""

    conversation: Conversation
    user_message: Message
    assistant_message: Message


@dataclass
class StreamEvent:
    """Event emitted during streaming."""

    type: str  # "start", "delta", "done", "error"
    data: dict


@dataclass
class NpcDialogueLimitResult:
    response: Optional[str] = None
    kill_player: bool = False
    note: Optional[str] = None


class ConversationService:
    """Service for handling chat conversations."""

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        llm_client: LLMClient,
        game_repo: Optional[GameRepository] = None,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.llm_client = llm_client
        self.game_repo = game_repo
        self._tool_handlers: Optional[GameToolHandlers] = None

    @property
    def tool_handlers(self) -> Optional[GameToolHandlers]:
        """Lazily initialize tool handlers when game_repo is available."""
        if self._tool_handlers is None and self.game_repo is not None:
            self._tool_handlers = GameToolHandlers(self.game_repo)
        return self._tool_handlers

    def _generate_title(self, first_message: str) -> str:
        """Generate a conversation title from the first message."""
        title = first_message[:50].strip()
        if len(first_message) > 50:
            title += "..."
        return title

    async def _apply_npc_turn_limits(
        self,
        *,
        conversation_id: str,
        state: GameState,
        location_data: Optional[dict],
    ) -> Optional[NpcDialogueLimitResult]:
        """Check and apply NPC turn limits. Counts ALL LLM calls while in NPC location.

        Returns a result if player should be killed, None otherwise.
        """
        if not self.game_repo or not location_data:
            return None

        npcs = location_data.get("npcs") or []
        if not npcs:
            return None

        flags = state.flags or {}
        npc_turns = flags.get("npc_turns")
        if not isinstance(npc_turns, dict):
            npc_turns = {}

        result = None
        updated = False

        for npc in npcs:
            npc_id = _npc_state_key(npc)
            if not npc_id:
                continue

            # Skip if NPC has been bypassed (defeated, persuaded, etc.)
            if _npc_has_bypass(npc_id, flags):
                continue

            config = _resolve_turn_config(npc)
            if not config:
                continue

            # Increment turn count for this NPC
            count = _int_or_default(npc_turns.get(npc_id), 0) + 1
            npc_turns[npc_id] = count
            updated = True

            # Check if limit exceeded
            if count >= config["max_turns"] and config.get("kill_player"):
                name = npc.get("name") or npc.get("id") or "The figure"
                note = (
                    f"{name} has lost patience after {count} turns. "
                    f"{name} kills the player. Narrate the death clearly and end the scene."
                )
                result = NpcDialogueLimitResult(
                    kill_player=True,
                    note=note,
                )
                # Don't break - continue to update all NPC counts

        if updated:
            new_flags = dict(flags)
            new_flags["npc_turns"] = npc_turns
            await self.game_repo.update_state(conversation_id, {"flags": new_flags})

        return result

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        tenant_id: str = "default",
        user_id: str = "default",
    ) -> ChatResult:
        """Process a chat message (non-streaming)."""
        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_repo.get(conversation_id)
            if not conversation:
                raise ConversationNotFoundError(conversation_id)
        else:
            conversation = await self.conversation_repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                title=self._generate_title(message),
            )

        # Save user message
        user_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )

        # Load history and call LLM
        history = await self.message_repo.list_by_conversation(conversation.id)
        llm_messages = [
            {
                "role": m.role,
                "content": strip_internal_markers(m.content) if m.role == "assistant" else m.content,
            }
            for m in history
        ]

        assistant_content = await self.llm_client.chat(llm_messages)

        # Save assistant response
        assistant_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
        )

        # Update conversation timestamp
        await self.conversation_repo.touch(conversation.id)

        return ChatResult(
            conversation=conversation,
            user_message=user_msg,
            assistant_message=assistant_msg,
        )

    async def chat_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        tenant_id: str = "default",
        user_id: str = "default",
    ) -> AsyncIterator[StreamEvent]:
        """Process a chat message with streaming response."""
        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_repo.get(conversation_id)
            if not conversation:
                yield StreamEvent(
                    type="error",
                    data={
                        "error": f"Conversation not found: {conversation_id}",
                        "code": "CONVERSATION_NOT_FOUND",
                    },
                )
                return
        else:
            conversation = await self.conversation_repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                title=self._generate_title(message),
            )

        # Save user message
        user_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )

        # Emit start event
        yield StreamEvent(
            type="start",
            data={
                "conversation_id": conversation.id,
                "user_message_id": user_msg.id,
            },
        )

        # Load history and call LLM
        history = await self.message_repo.list_by_conversation(conversation.id)
        llm_messages = [
            {
                "role": m.role,
                "content": strip_internal_markers(m.content) if m.role == "assistant" else m.content,
            }
            for m in history
        ]

        # Stream response
        full_content = ""
        try:
            async for chunk in self.llm_client.chat_stream(llm_messages):
                full_content += chunk
                yield StreamEvent(type="delta", data={"content": chunk})
        except Exception as e:
            yield StreamEvent(
                type="error",
                data={"error": str(e), "code": "LLM_ERROR"},
            )
            return

        # Save assistant response
        assistant_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="assistant",
            content=full_content,
        )

        # Update conversation timestamp
        await self.conversation_repo.touch(conversation.id)

        # Emit done event
        yield StreamEvent(
            type="done",
            data={
                "message": {
                    "id": assistant_msg.id,
                    "role": assistant_msg.role,
                    "content": assistant_msg.content,
                    "created_at": assistant_msg.created_at.isoformat(),
                }
            },
        )

    async def handle_dev_commands(self, message: str, conversation_id: str, user_id: str) -> Optional[str]:
        """Handle dev-only slash commands like /teleport, /save, /load."""
        # Simple dev check: requires user to be an admin or specific environment logic
        # For now, we'll check if the user is_admin.
        # This requires fetching the user, which we might not have handy here without a DB call.
        # However, conversation ownership check implies we have access.
        
        if not message.startswith("/"):
            return None

        parts = message.split()
        command = parts[0].lower()
        args = parts[1:]

        # TODO: Ideally check user.is_admin or settings.environment == "development"
        # Since this service doesn't have the user object, we rely on the repo or just assume caller checked.
        # Let's verify admin status via DB.
        from app.models.database import User
        from sqlalchemy import select
        
        # Check admin status
        result = await self.conversation_repo.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_admin:
            return None

        if command == "/teleport" and args and self.game_repo:
            target_id = args[0]
            # Verify location exists
            loc = await self.game_repo.get_location(target_id)
            if not loc:
                return f"Error: Location '{target_id}' not found."
            
            await self.game_repo.update_state(conversation_id, {"current_location": target_id})
            return f"WARP SPEED: Teleported to {loc['name']} ({target_id})."

        elif command == "/save" and self.game_repo:
            state = await self.game_repo.get_state(conversation_id)
            if not state:
                return "Error: No game state found."
            
            # Get latest message ID to handle chat history rewind
            from app.models.database import Message
            from sqlalchemy import select, desc
            result = await self.conversation_repo.session.execute(
                select(Message.id).where(Message.conversation_id == conversation_id).order_by(desc(Message.created_at)).limit(1)
            )
            last_message_id = result.scalar_one_or_none()

            snapshot = {
                "current_location": state.current_location,
                "inventory": state.inventory,
                "visited_locations": state.visited_locations,
                "player_stats": state.player_stats,
                "flags": state.flags,
                "last_message_id": last_message_id
            }
            # Save to DB column
            state.dev_snapshot = snapshot
            await self.game_repo.session.flush()
            return "CHECKPOINT SAVED."

        elif command == "/load" and self.game_repo:
            state = await self.game_repo.get_state(conversation_id)
            if not state or not state.dev_snapshot:
                return "Error: No checkpoint found. Use /save first."
            
            snapshot = state.dev_snapshot
            
            # Restore Game State
            await self.game_repo.update_state(conversation_id, snapshot)
            
            # Rewind Chat History
            last_message_id = snapshot.get("last_message_id")
            if last_message_id:
                from app.models.database import Message
                from sqlalchemy import delete
                
                # Get timestamp of the snapshot message
                msg_result = await self.conversation_repo.session.execute(
                    select(Message.created_at).where(Message.id == last_message_id)
                )
                cutoff_time = msg_result.scalar_one_or_none()
                
                if cutoff_time:
                    # Delete all messages created AFTER the snapshot message
                    await self.conversation_repo.session.execute(
                        delete(Message).where(
                            Message.conversation_id == conversation_id,
                            Message.created_at > cutoff_time
                        )
                    )
                    await self.conversation_repo.session.flush()

            return "TIME REWIND: Checkpoint restored. Chat history truncated."
            
        elif command == "/reset" and self.game_repo:
             # Reset state to initial
             await self.game_repo.update_state(conversation_id, {
                 "current_location": "start",
                 "inventory": [],
                 "visited_locations": [],
                 "player_stats": {},
                 "flags": {},
             })
             return "SYSTEM RESET: Game restarted."

        return None

    async def chat_stream_with_tools(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        tenant_id: str = "default",
        user_id: str = "default",
    ) -> AsyncIterator[StreamEvent]:
        """Process a chat message with tool use support.

        Uses real-time streaming with tool use events.
        """
        # ... (rest of method)
        if self.tool_handlers is None:
            # Fall back to regular streaming if no game repo configured
            async for event in self.chat_stream(
                message, conversation_id, tenant_id, user_id
            ):
                yield event
            return

        # Get or create conversation
        if conversation_id:
            conversation = await self.conversation_repo.get(conversation_id)
            if not conversation:
                yield StreamEvent(
                    type="error",
                    data={
                        "error": f"Conversation not found: {conversation_id}",
                        "code": "CONVERSATION_NOT_FOUND",
                    },
                )
                return
            # Additional security check: ensure conversation belongs to user_id
            if conversation.user_id != user_id:
                 yield StreamEvent(
                    type="error",
                    data={
                        "error": "Unauthorized access to conversation",
                        "code": "UNAUTHORIZED",
                    },
                )
                 return
        else:
            conversation = await self.conversation_repo.create(
                tenant_id=tenant_id,
                user_id=user_id,
                title=self._generate_title(message),
            )
            # Track new game session
            settings = get_settings()
            LLM_SESSIONS_TOTAL.labels(model=settings.model_name).inc()

        # App-enforced victory/game-over handling (hard stop).
        # This guarantees deterministic output and prevents the LLM from mutating state post-victory.
        assert self.game_repo is not None
        state = await self.game_repo.get_state(conversation.id)

        # Capture state BEFORE streaming for diff generation
        location_before = state.current_location if state else None
        inventory_before = set(i['id'] for i in (state.inventory or []) if isinstance(i, dict) and 'id' in i) if state else set()

        # Inject current game state into system prompt for context refreshment
        state_summary = ""
        location_data = None
        if state:
            location_name = state.current_location
            # Fetch location details for richer context
            loc_data = await self.game_repo.get_location(state.current_location)
            location_data = loc_data
            exits_map = dict(loc_data.get("exits", {})) if loc_data else {}
            interactables = loc_data.get("interactables", []) if loc_data else []
            interactables_display = json.dumps(interactables, ensure_ascii=False) if interactables else "None"
            inventory_items = [i['name'] for i in (state.inventory or []) if isinstance(i, dict) and 'name' in i]
            flags = state.flags or {}
            if location_name == "living_room" and flags.get("vault_revealed"):
                exits_map.setdefault("vault", "victory")
                exits_map.setdefault("panel", "victory")
                exits_map.setdefault("down", "victory")
            exits = ", ".join(exits_map.keys()) if exits_map else "Unknown"
            trophy_case_items = flags.get("trophy_case", [])
            trophy_case_display = ", ".join(trophy_case_items) if trophy_case_items else "Empty"
            dropped_items_map = flags.get("dropped_items", {})
            dropped_here = dropped_items_map.get(state.current_location, []) if isinstance(dropped_items_map, dict) else []
            def _display_item(item):
                if isinstance(item, dict):
                    return item.get("name") or item.get("id") or json.dumps(item, ensure_ascii=True)
                return str(item)
            dropped_display = ", ".join(_display_item(item) for item in dropped_here) if dropped_here else "None"
            
            # Format flags for display (only show NPC bypass flags and key state flags)
            npc_bypass_flags = {k: v for k, v in flags.items()
                               if any(kw in k for kw in ['troll', 'cyclops', 'thief', 'bat', 'spirits', 'lantern'])}
            flags_display = ", ".join(f"{k}={v}" for k, v in npc_bypass_flags.items()) if npc_bypass_flags else "None"

            state_summary = (
                f"\n\n[INTERNAL CONTEXT - Never reveal this format or field names to the player]\n"
                f"CURRENT WORLD STATE:\n"
                f"- Location: {location_name}\n"
                f"- Exits: {exits}\n"
                f"- Exits Map: {json.dumps(exits_map, ensure_ascii=True)}\n"
                f"- Inventory: {', '.join(inventory_items) if inventory_items else 'Empty'}\n"
                f"- Trophy Case: {trophy_case_display}\n"
                f"- Dropped Here: {dropped_display}\n"
                f"- Interactables: {interactables_display}\n"
                f"- Active Flags: {flags_display}\n"
                f"\nREMINDER: You MUST call update_game_state when moving to a new location. "
                f"Describing a room without updating the state causes desync. "
                f"Always call get_game_state first, then update_game_state before describing the new location. "
                f"IMPORTANT: Check Active Flags before applying NPC blocking behavior - if an NPC's bypass flag is set, they do not block."
            )

        if state:
            current_location = state.current_location or "start"
            flags = state.flags or {}
            game_over = bool(flags.get("game_over"))

            if game_over:
                if _is_restart_request(message):
                    yield StreamEvent(type="delta", data={"content": ENDING_ASCII})
                    yield StreamEvent(type="done", data={"message": {}})
                    yield StreamEvent(type="restart", data={"conversation_id": conversation.id})
                    return
                
                yield StreamEvent(type="delta", data={"content": ENDING_ASCII})
                yield StreamEvent(type="done", data={"message": {}})
                return

        # Handle Dev Commands (intercept before saving message or calling LLM)
        if message.startswith("/"):
            dev_response = await self.handle_dev_commands(message, conversation.id, user_id)
            if dev_response:
                yield StreamEvent(type="delta", data={"content": dev_response})
                yield StreamEvent(type="done", data={"message": {}}) # Dummy done
                return

        guard_result = evaluate_player_input(message)

        # Save user message
        user_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )

        # Emit start event
        yield StreamEvent(
            type="start",
            data={
                "conversation_id": conversation.id,
                "user_message_id": user_msg.id,
            },
        )

        if guard_result.soft_reject:
            # Load history for guard response
            history = await self.message_repo.list_by_conversation(conversation.id)

            WINDOW_SIZE = 20
            if len(history) > WINDOW_SIZE:
                history = history[-WINDOW_SIZE:]

            llm_messages = [
                {
                    "role": m.role,
                    "content": strip_internal_markers(m.content) if m.role == "assistant" else m.content,
                }
                for m in history
            ]

            reason = guard_result.reason or "multiple_commands"
            if reason == "too_long":
                reason_label = "input too long"
            else:
                reason_label = "multiple actions detected"
            guard_reason_line = f"Reason: {reason_label}."
            guard_instructions = (
                "The player's last input should not advance the game.\n"
                f"{guard_reason_line}\n"
                "Respond in narrator voice with a brief, in-character correction.\n"
                "Tell the player to enter one action per turn and offer 1-3 example commands.\n"
                "Allow creative roleplay, but only one action can be processed at a time.\n"
                "Do not describe outcomes, do not change location or inventory, and do not narrate time passing.\n"
                "Do not quote the reason line verbatim.\n"
                "Do not mention tools, systems, or hidden limits. Use statements, not questions."
            )

            base_system_text, _ = _build_base_system_prompt(include_skills=False)
            guard_system_prompt = f"{base_system_text}\n\n## Input Guard\n{guard_instructions}"

            full_content = ""
            try:
                async for chunk in self.llm_client.chat_stream(
                    llm_messages,
                    system_prompt=[
                        {
                            "type": "text",
                            "text": guard_system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                ):
                    full_content += chunk
                    yield StreamEvent(type="delta", data={"content": chunk})
            except Exception as e:
                yield StreamEvent(
                    type="error",
                    data={"error": str(e), "code": "LLM_ERROR"},
                )
                return

            assistant_msg = await self.message_repo.create(
                conversation_id=conversation.id,
                role="assistant",
                content=full_content,
            )
            await self.conversation_repo.touch(conversation.id)
            user_content = strip_internal_markers(assistant_msg.content)

            yield StreamEvent(
                type="done",
                data={
                    "message": {
                        "id": assistant_msg.id,
                        "role": assistant_msg.role,
                        "content": user_content,
                        "created_at": assistant_msg.created_at.isoformat(),
                    }
                },
            )
            return

        npc_limit_result = None
        force_restart_after_stream = False
        if state:
            npc_limit_result = await self._apply_npc_turn_limits(
                conversation_id=conversation.id,
                state=state,
                location_data=location_data,
            )

        if npc_limit_result and npc_limit_result.response:
            assistant_msg = await self.message_repo.create(
                conversation_id=conversation.id,
                role="assistant",
                content=npc_limit_result.response,
            )
            await self.conversation_repo.touch(conversation.id)
            user_content = strip_internal_markers(assistant_msg.content)

            yield StreamEvent(type="delta", data={"content": user_content})
            yield StreamEvent(
                type="done",
                data={
                    "message": {
                        "id": assistant_msg.id,
                        "role": assistant_msg.role,
                        "content": user_content,
                        "created_at": assistant_msg.created_at.isoformat(),
                    }
                },
            )
            return
        if npc_limit_result and npc_limit_result.kill_player:
            force_restart_after_stream = True
            restart_reason = "death_npc"
            if npc_limit_result.note:
                if state_summary:
                    state_summary = f"{state_summary}\n\nNPC OVERRIDE:\n{npc_limit_result.note}"
                else:
                    state_summary = f"NPC OVERRIDE:\n{npc_limit_result.note}"

        # Load history
        history = await self.message_repo.list_by_conversation(conversation.id)
        
        # SLIDING WINDOW: Keep only the last 20 messages to prevent context overflow
        # This keeps the "fresh" context while relying on GameState for the source of truth.
        WINDOW_SIZE = 20
        if len(history) > WINDOW_SIZE:
            history = history[-WINDOW_SIZE:]
            
        llm_messages = [
            {
                "role": m.role,
                "content": strip_internal_markers(m.content) if m.role == "assistant" else m.content,
            }
            for m in history
        ]

        # Get tool handlers
        base_handlers = self.tool_handlers.get_handlers()
        
        # Track if restart was triggered during this request
        restart_triggered = False
        # Track restart reason for analytics: "explicit", "death_grue", "death_npc"
        restart_reason: str | None = None

        # Track location lookups for desync detection
        locations_looked_up = []

        # Wrap handlers to inject correct conversation_id
        # The LLM often hallucinates 'default' or omits it, causing foreign key errors.
        # We must ensure the handler receives the *actual* database conversation ID.
        wrapped_handlers = {}

        for name, handler in base_handlers.items():
            async def wrapped_handler(input_data: dict, handler=handler, tool_name=name):
                nonlocal restart_triggered, restart_reason
                # Inject/Overwrite conversation_id if the tool expects it
                # get_game_state, update_game_state, and restart_game all require it.
                # get_location_data does not (it uses location_id).
                if "conversation_id" in input_data or tool_name in ["get_game_state", "update_game_state", "restart_game"]:
                    input_data["conversation_id"] = conversation.id

                # Track location lookups for desync detection
                if tool_name == "get_location_data":
                    loc_id = input_data.get("location_id")
                    if loc_id and loc_id != location_before:
                        locations_looked_up.append(loc_id)

                # Detect restart reason before the handler resets state
                if tool_name == "restart_game" and restart_reason is None:
                    # Check if this is a grue death (player in darkness)
                    pre_restart_state = await self.game_repo.get_state(conversation.id)
                    if pre_restart_state:
                        pre_flags = pre_restart_state.flags or {}
                        if pre_flags.get("in_darkness"):
                            restart_reason = "death_grue"
                        else:
                            restart_reason = "explicit"

                result = await handler(input_data)

                # Check if this was a restart_game call
                if tool_name == "restart_game":
                    restart_triggered = True

                return result

            wrapped_handlers[name] = wrapped_handler

        full_content = ""
        tools_called = []  # Track tool calls for message history

        try:
            # Inject dynamic state summary into system prompt (via client if supported, or prepended to messages?)
            # The client supports a system_prompt argument. We'll use that to append our dynamic state.
            # Note: We need to get the BASE system prompt first, then append.
            # However, the client loads the base prompt internally.
            # To avoid double-loading or overwriting, let's pass it explicitly here if the client allows overriding/appending.
            # Our client implementation takes `system_prompt`. If we pass it, it REPLACES the default.
            # So we must reconstruct the full prompt here if we want to add to it.
            
            base_system_text, skills_included = _build_base_system_prompt(include_skills=True)
            final_system_prompt = f"{base_system_text}\n{state_summary}"

            # Debug logging before LLM call
            log_service_debug({
                "event": "llm_call_start",
                "timestamp": int(time.time() * 1000),
                "conversation_id": conversation.id,
                "message_count": len(llm_messages),
                "state_summary": state_summary,
                "skills_included": skills_included,
                "messages_preview": [
                    {"role": m["role"], "content": m["content"][:150] + "..." if len(m["content"]) > 150 else m["content"]}
                    for m in llm_messages[-5:]  # Last 5 messages
                ],
            })

            # Consume the streaming event generator
            async for event in self.llm_client.chat_stream_with_tools(
                messages=llm_messages,
                tool_handlers=wrapped_handlers,
                system_prompt=[
                    {
                        "type": "text",
                        "text": final_system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
            ):
                if event["type"] == "text":
                    chunk = event["content"]
                    full_content += chunk
                    yield StreamEvent(type="delta", data={"content": chunk})

                elif event["type"] == "tool_start":
                    tools_called.append(event["tool"])
                    yield StreamEvent(
                        type="progress",
                        data={"step": "using_tool", "tool": event["tool"]}
                    )
                
                elif event["type"] == "tool_end":
                    yield StreamEvent(
                        type="progress",
                        data={"step": "tool_done"}
                    )

        except Exception as e:
            yield StreamEvent(
                type="error",
                data={"error": str(e), "code": "LLM_ERROR"},
            )
            return

        # Generate state diff for message history
        # This ensures Claude sees explicit state changes, not just tool names
        state_after = await self.game_repo.get_state(conversation.id)
        if state_after and state_after.current_location == "victory":
            flags_after = state_after.flags or {}
            if not flags_after.get("game_over"):
                # First-time victory - record metrics
                GAME_VICTORIES_TOTAL.inc()
                # Calculate session duration from game state creation
                from datetime import datetime
                if state_after.created_at:
                    session_duration = (datetime.utcnow() - state_after.created_at).total_seconds()
                    GAME_SESSION_DURATION_SECONDS.observe(session_duration)
                state_after = await self.game_repo.update_state(
                    conversation.id,
                    {"flags": {"game_over": True}},
                )
        location_after = state_after.current_location if state_after else None
        inventory_after = set(i['id'] for i in (state_after.inventory or []) if isinstance(i, dict) and 'id' in i) if state_after else set()

        # Detect movement desync: LLM looked up a different location but didn't update state
        if locations_looked_up and location_before == location_after:
            if "update_game_state" not in tools_called:
                log_service_debug({
                    "event": "movement_desync_detected",
                    "timestamp": int(time.time() * 1000),
                    "conversation_id": conversation.id,
                    "locations_looked_up": locations_looked_up,
                    "stayed_at": location_before,
                    "tools_called": tools_called,
                    "message": message,
                })

        changes = []

        # Location change
        if location_before != location_after:
            changes.append(f"{location_before} → {location_after}")

            from datetime import datetime
            from app.metrics import LOCATION_DWELL_SECONDS

            # Record dwell time metric
            if location_before and state and state.location_entered_at:
                dwell_seconds = (datetime.utcnow() - state.location_entered_at).total_seconds()
                LOCATION_DWELL_SECONDS.labels(location_id=location_before).observe(dwell_seconds)

            # Update entry timestamp for new location
            await self.game_repo.update_state(
                conversation.id,
                {"location_entered_at": datetime.utcnow()}
            )

        # Inventory changes
        added = inventory_after - inventory_before
        removed = inventory_before - inventory_after
        if added:
            changes.append(f"+{', '.join(sorted(added))}")
        if removed:
            changes.append(f"-{', '.join(sorted(removed))}")

        # Append state diff or tool list to message
        if changes:
            state_diff = f"\n\n---\n[State: {' | '.join(changes)}]"
            full_content += state_diff
        elif tools_called:
            # Fallback to tool list if no state changes detected
            unique_tools = list(dict.fromkeys(tools_called))
            tool_summary = f"\n\n---\n[Tools used: {', '.join(unique_tools)}]"
            full_content += tool_summary

        # Save assistant response
        assistant_msg = await self.message_repo.create(
            conversation_id=conversation.id,
            role="assistant",
            content=full_content,
        )

        # Update conversation timestamp
        await self.conversation_repo.touch(conversation.id)

        # Emit done event (strip internal state markers from user output)
        user_content = strip_internal_markers(assistant_msg.content)

        yield StreamEvent(
            type="done",
            data={
                "message": {
                    "id": assistant_msg.id,
                    "role": assistant_msg.role,
                    "content": user_content,
                    "created_at": assistant_msg.created_at.isoformat(),
                }
            },
        )

        # If restart was triggered, emit restart event after done
        if restart_triggered or force_restart_after_stream:
            # Record session duration (use state captured before streaming)
            from datetime import datetime
            if state and state.created_at:
                session_duration = (datetime.utcnow() - state.created_at).total_seconds()
                GAME_SESSION_DURATION_SECONDS.observe(session_duration)

            # Determine final restart reason
            final_reason = restart_reason or "explicit"

            # Increment restart counter
            GAME_RESTARTS_TOTAL.labels(reason=final_reason).inc()

            # Increment death counter for death cases
            if final_reason == "death_grue":
                GAME_DEATHS_TOTAL.labels(death_type="grue").inc()
            elif final_reason == "death_npc":
                GAME_DEATHS_TOTAL.labels(death_type="npc").inc()

            yield StreamEvent(
                type="restart",
                data={"conversation_id": conversation.id},
            )
