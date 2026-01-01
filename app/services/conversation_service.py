from typing import AsyncIterator, Optional
from dataclasses import dataclass
import os
import json
import time
import re

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
from app.utils.message_sanitizer import strip_internal_markers


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

NPC_DIALOGUE_DEFAULTS = {
    "max_turns": 4,
    "decay_seconds": 300,
    "cooldown_seconds": 120,
    "exhausted_response": "{name} loses focus and turns away, no longer engaging.",
    "cooldown_response": "{name} remains unavailable for now.",
    "kill_player": False,
}

NPC_TALK_WORDS = {
    "talk",
    "speak",
    "ask",
    "say",
    "tell",
    "chat",
    "converse",
    "greet",
    "address",
}

NPC_GREETINGS = {
    "hello",
    "hi",
    "hey",
    "greetings",
}


def _normalize_command(message: str) -> str:
    return " ".join(message.strip().lower().split())


def _contains_word(text: str, word: str) -> bool:
    if not text or not word:
        return False
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def _npc_state_key(npc: dict) -> str:
    npc_id = str(npc.get("id") or "").strip().lower()
    if npc_id:
        return npc_id
    return str(npc.get("name") or "npc").strip().lower()


def _message_mentions_npc(cmd: str, npc: dict) -> bool:
    npc_id = str(npc.get("id") or "").strip().lower()
    npc_name = str(npc.get("name") or "").strip().lower()

    if npc_id and _contains_word(cmd, npc_id):
        return True
    if npc_name:
        if " " in npc_name:
            return npc_name in cmd
        return _contains_word(cmd, npc_name)
    return False


def _is_npc_engagement(message: str, npc: dict, npcs: list[dict]) -> bool:
    cmd = _normalize_command(message)
    if not cmd:
        return False

    if _message_mentions_npc(cmd, npc):
        return True

    if _has_any_word(cmd, NPC_TALK_WORDS | NPC_GREETINGS):
        return len(npcs) == 1

    if cmd.endswith("?") or cmd.startswith('"') or cmd.startswith("'"):
        return len(npcs) == 1

    return False


def _has_any_word(cmd: str, words: set[str]) -> bool:
    return any(_contains_word(cmd, word) for word in words)


def _select_dialogue_npc(message: str, npcs: list[dict]) -> Optional[dict]:
    if not npcs:
        return None
    if len(npcs) == 1:
        return npcs[0]

    cmd = _normalize_command(message)
    for npc in npcs:
        if _message_mentions_npc(cmd, npc):
            return npc

    return npcs[0]


def _int_or_default(value: Optional[object], default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _resolve_dialogue_config(npc: dict) -> dict:
    config = npc.get("dialogue_limits") or {}
    if config.get("enabled") is False:
        return {}

    max_turns = _int_or_default(config.get("max_turns"), NPC_DIALOGUE_DEFAULTS["max_turns"])
    if max_turns <= 0:
        return {}

    decay_seconds = _int_or_default(config.get("decay_seconds"), NPC_DIALOGUE_DEFAULTS["decay_seconds"])
    cooldown_seconds = _int_or_default(
        config.get("cooldown_seconds"),
        NPC_DIALOGUE_DEFAULTS["cooldown_seconds"],
    )

    return {
        "max_turns": max_turns,
        "decay_seconds": max(0, decay_seconds),
        "cooldown_seconds": max(0, cooldown_seconds),
        "exhausted_response": config.get(
            "exhausted_response",
            NPC_DIALOGUE_DEFAULTS["exhausted_response"],
        ),
        "cooldown_response": config.get(
            "cooldown_response",
            NPC_DIALOGUE_DEFAULTS["cooldown_response"],
        ),
        "kill_player": bool(config.get("kill_player", NPC_DIALOGUE_DEFAULTS["kill_player"])),
    }


def _format_npc_response(template: str, npc: dict) -> str:
    name = npc.get("name") or npc.get("id") or "The figure"
    try:
        return template.format(name=name)
    except (KeyError, IndexError, ValueError):
        return template.replace("{name}", str(name))


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


def _is_vault_entry_command(message: str) -> bool:
    cmd = _normalize_command(message)

    if cmd in {"down", "d", "go down"}:
        return True

    if cmd in {
        "enter panel",
        "enter the panel",
        "enter vault",
        "enter the vault",
        "enter stairs",
        "enter the stairs",
        "enter staircase",
        "enter the staircase",
        "down stairs",
        "down the stairs",
        "down staircase",
        "down the staircase",
        "downstairs",
        "go down stairs",
        "go down the stairs",
        "go downstairs",
        "go down staircase",
        "go down the staircase",
    }:
        return True

    return False


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

    async def _apply_npc_dialogue_limits(
        self,
        *,
        message: str,
        conversation_id: str,
        state: GameState,
        location_data: Optional[dict],
    ) -> Optional[NpcDialogueLimitResult]:
        if not self.game_repo or not location_data:
            return None

        npcs = location_data.get("npcs") or []
        if not npcs:
            return None

        npc = _select_dialogue_npc(message, npcs)
        if not npc:
            return None

        config = _resolve_dialogue_config(npc)
        if not config:
            return None

        npc_id = _npc_state_key(npc)
        if not npc_id:
            return None

        flags = state.flags or {}
        npc_dialogue = flags.get("npc_dialogue")
        if not isinstance(npc_dialogue, dict):
            npc_dialogue = {}

        entry = npc_dialogue.get(npc_id)
        if not isinstance(entry, dict):
            entry = {}

        now = int(time.time())
        engaged = _is_npc_engagement(message, npc, npcs)
        count = _int_or_default(entry.get("count"), 0)
        last_exchange_at = _int_or_default(entry.get("last_exchange_at"), 0)
        cooldown_until = _int_or_default(entry.get("cooldown_until"), 0)

        decay_seconds = config["decay_seconds"]
        if last_exchange_at and decay_seconds > 0 and now - last_exchange_at >= decay_seconds:
            count = 0
            cooldown_until = 0

        if cooldown_until and now < cooldown_until:
            npc_dialogue[npc_id] = {
                "count": count,
                "last_exchange_at": last_exchange_at,
                "cooldown_until": cooldown_until,
            }
            new_flags = dict(flags)
            new_flags["npc_dialogue"] = npc_dialogue
            await self.game_repo.update_state(conversation_id, {"flags": new_flags})
            if engaged:
                return NpcDialogueLimitResult(
                    response=_format_npc_response(config["cooldown_response"], npc),
                )
            return None

        count += 1
        last_exchange_at = now

        if count >= config["max_turns"]:
            count = config["max_turns"]
            npc_dialogue[npc_id] = {
                "count": count,
                "last_exchange_at": last_exchange_at,
                "cooldown_until": cooldown_until,
            }
            new_flags = dict(flags)
            new_flags["npc_dialogue"] = npc_dialogue
            await self.game_repo.update_state(conversation_id, {"flags": new_flags})
            if not engaged:
                return None

            if config.get("kill_player"):
                name = npc.get("name") or npc.get("id") or "The figure"
                note = (
                    f"{name} has reached their patience limit and kills the player. "
                    "Narrate the death clearly and end the scene."
                )
                return NpcDialogueLimitResult(
                    kill_player=True,
                    note=note,
                )

            cooldown_seconds = config["cooldown_seconds"]
            cooldown_until = now + cooldown_seconds if cooldown_seconds > 0 else 0
            npc_dialogue[npc_id] = {
                "count": count,
                "last_exchange_at": last_exchange_at,
                "cooldown_until": cooldown_until,
            }
            new_flags = dict(flags)
            new_flags["npc_dialogue"] = npc_dialogue
            await self.game_repo.update_state(conversation_id, {"flags": new_flags})
            return NpcDialogueLimitResult(
                response=_format_npc_response(config["exhausted_response"], npc),
            )

        npc_dialogue[npc_id] = {
            "count": count,
            "last_exchange_at": last_exchange_at,
            "cooldown_until": cooldown_until,
        }
        new_flags = dict(flags)
        new_flags["npc_dialogue"] = npc_dialogue
        await self.game_repo.update_state(conversation_id, {"flags": new_flags})
        return None

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
        llm_messages = [{"role": m.role, "content": m.content} for m in history]

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
        llm_messages = [{"role": m.role, "content": m.content} for m in history]

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
            exits_map = loc_data.get("exits", {}) if loc_data else {}
            exits = ", ".join(exits_map.keys()) if exits_map else "Unknown"
            interactables = loc_data.get("interactables", []) if loc_data else []
            interactables_display = json.dumps(interactables, ensure_ascii=False) if interactables else "None"
            inventory_items = [i['name'] for i in (state.inventory or []) if isinstance(i, dict) and 'name' in i]
            flags = state.flags or {}
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
                f"\n\nCURRENT GAME STATE (Source of Truth):\n"
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
            vault_revealed = bool(flags.get("vault_revealed"))

            if game_over:
                if _is_restart_request(message):
                    yield StreamEvent(type="delta", data={"content": ENDING_ASCII})
                    yield StreamEvent(type="done", data={"message": {}})
                    yield StreamEvent(type="restart", data={"conversation_id": conversation.id})
                    return
                
                yield StreamEvent(type="delta", data={"content": ENDING_ASCII})
                yield StreamEvent(type="done", data={"message": {}})
                return

            if current_location == "living_room" and vault_revealed and _is_vault_entry_command(message):
                user_msg = await self.message_repo.create(
                    conversation_id=conversation.id,
                    role="user",
                    content=message,
                )

                yield StreamEvent(
                    type="start",
                    data={
                        "conversation_id": conversation.id,
                        "user_message_id": user_msg.id,
                    },
                )

                new_flags = dict(flags)
                new_flags["game_over"] = True
                await self.game_repo.update_state(
                    conversation.id,
                    {"current_location": "victory", "flags": new_flags},
                )

                victory = await self.game_repo.get_location("victory")
                victory_description = (victory or {}).get("description", "").rstrip()
                full_content = f"{victory_description}\n\n{ENDING_ASCII}".lstrip()

                assistant_msg = await self.message_repo.create(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_content,
                )
                await self.conversation_repo.touch(conversation.id)

                yield StreamEvent(type="delta", data={"content": full_content})
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
                return

            if current_location == "victory":
                new_flags = dict(flags)
                new_flags["game_over"] = True
                await self.game_repo.update_state(
                    conversation.id,
                    {"flags": new_flags},
                )

                victory = await self.game_repo.get_location("victory")
                victory_description = (victory or {}).get("description", "").rstrip()
                full_content = f"{victory_description}\n\n{ENDING_ASCII}".lstrip()

                assistant_msg = await self.message_repo.create(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_content,
                )
                await self.conversation_repo.touch(conversation.id)

                yield StreamEvent(type="delta", data={"content": full_content})
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
                return

        # Handle Dev Commands (intercept before saving message or calling LLM)
        if message.startswith("/"):
            dev_response = await self.handle_dev_commands(message, conversation.id, user_id)
            if dev_response:
                yield StreamEvent(type="delta", data={"content": dev_response})
                yield StreamEvent(type="done", data={"message": {}}) # Dummy done
                return

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

        npc_limit_result = None
        force_restart_after_stream = False
        if state:
            npc_limit_result = await self._apply_npc_dialogue_limits(
                message=message,
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
            
        llm_messages = [{"role": m.role, "content": m.content} for m in history]

        # Get tool handlers
        base_handlers = self.tool_handlers.get_handlers()
        
        # Track if restart was triggered during this request
        restart_triggered = False

        # Track location lookups for desync detection
        locations_looked_up = []

        # Wrap handlers to inject correct conversation_id
        # The LLM often hallucinates 'default' or omits it, causing foreign key errors.
        # We must ensure the handler receives the *actual* database conversation ID.
        wrapped_handlers = {}

        for name, handler in base_handlers.items():
            async def wrapped_handler(input_data: dict, handler=handler, tool_name=name):
                nonlocal restart_triggered
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
            
            # Better approach: The AnthropicClient loads the default prompt in __init__.
            # We can create a method to "get_default_system_prompt" or just load it here too.
            from prompts import load_prompt, load_all_skills, NARRATOR_PROMPT
            narrator_prompt = load_prompt(NARRATOR_PROMPT)
            try:
                premise_prompt = load_prompt("premise")
                base_system_text = f"{narrator_prompt}\n\n## Game Premise\n{premise_prompt}"
            except FileNotFoundError:
                base_system_text = narrator_prompt

            # Load skills if enabled (prompt concatenation approach)
            settings = get_settings()
            if settings.skills_enabled:
                skills_content = load_all_skills()
                if skills_content:
                    base_system_text = f"{base_system_text}\n\n## Game Mechanics (Skills)\n\n{skills_content}"

            final_system_prompt = f"{base_system_text}\n{state_summary}"

            # Debug logging before LLM call
            log_service_debug({
                "event": "llm_call_start",
                "timestamp": int(time.time() * 1000),
                "conversation_id": conversation.id,
                "message_count": len(llm_messages),
                "state_summary": state_summary,
                "skills_enabled": settings.skills_enabled,
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
            yield StreamEvent(
                type="restart",
                data={"conversation_id": conversation.id},
            )
