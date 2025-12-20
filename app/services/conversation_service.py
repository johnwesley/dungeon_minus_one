from typing import AsyncIterator, Optional
from dataclasses import dataclass

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.clients.llm_client import LLMClient
from app.models.database import Conversation, Message
from app.services.game_tools import GameToolHandlers


ENDING_ASCII = "[ PROCESS COMPLETE ]\n[ NO FURTHER INPUT ]\n\n>"


def _normalize_command(message: str) -> str:
    return " ".join(message.strip().lower().split())


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

        # Load history
        history = await self.message_repo.list_by_conversation(conversation.id)
        llm_messages = [{"role": m.role, "content": m.content} for m in history]

        # Get tool handlers
        base_handlers = self.tool_handlers.get_handlers()

        # Track if restart was triggered during this request
        restart_triggered = False

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

                result = await handler(input_data)

                # Check if this was a restart_game call
                if tool_name == "restart_game":
                    restart_triggered = True

                return result

            wrapped_handlers[name] = wrapped_handler

        full_content = ""

        try:
            # Consume the streaming event generator
            async for event in self.llm_client.chat_stream_with_tools(
                messages=llm_messages,
                tool_handlers=wrapped_handlers,
            ):
                if event["type"] == "text":
                    chunk = event["content"]
                    full_content += chunk
                    yield StreamEvent(type="delta", data={"content": chunk})

                elif event["type"] == "tool_start":
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

        # If restart was triggered, emit restart event after done
        if restart_triggered:
            yield StreamEvent(
                type="restart",
                data={"conversation_id": conversation.id},
            )
