from typing import AsyncIterator, Optional
from dataclasses import dataclass

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.game_repository import GameRepository
from app.clients.llm_client import LLMClient
from app.models.database import Conversation, Message
from app.services.game_tools import GameToolHandlers


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
