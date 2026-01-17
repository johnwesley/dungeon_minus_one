import asyncio
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

from app.services.conversation_service import ConversationService
from app.utils.message_sanitizer import strip_internal_markers


@dataclass
class FakeMessage:
    id: str
    role: str
    content: str
    created_at: datetime


class FakeMessageRepo:
    def __init__(self, messages=None):
        self.messages = list(messages) if messages else []
        self._counter = len(self.messages)

    async def create(self, conversation_id: str, role: str, content: str) -> FakeMessage:
        self._counter += 1
        message = FakeMessage(
            id=str(self._counter),
            role=role,
            content=content,
            created_at=datetime.utcnow(),
        )
        self.messages.append(message)
        return message

    async def list_by_conversation(self, conversation_id: str, limit=None):
        if limit:
            return self.messages[-limit:]
        return list(self.messages)


class FakeConversationRepo:
    def __init__(self, conversation):
        self.conversation = conversation

    async def get(self, conversation_id: str):
        if conversation_id == self.conversation.id:
            return self.conversation
        return None

    async def touch(self, conversation_id: str) -> None:
        return None


class FakeLLMClient:
    def __init__(self):
        self.seen_messages = None

    async def chat_stream(self, messages):
        self.seen_messages = messages
        yield "OK"


def test_strip_internal_markers_removes_state_and_tools():
    content = "Room text.\n\n---\n[State: a -> b]"
    assert strip_internal_markers(content) == "Room text."
    tools_content = "Output.\n\n---\n[Tools used: get_game_state]"
    assert strip_internal_markers(tools_content) == "Output."


def test_chat_stream_strips_internal_markers_from_history():
    history = [
        FakeMessage(
            id="1",
            role="assistant",
            content="Room text.\n\n---\n[State: start -> kitchen]",
            created_at=datetime.utcnow(),
        ),
        FakeMessage(
            id="2",
            role="user",
            content="look",
            created_at=datetime.utcnow(),
        ),
    ]
    message_repo = FakeMessageRepo(messages=history)
    conversation = SimpleNamespace(id="conv-1", user_id="user-1")
    llm_client = FakeLLMClient()
    service = ConversationService(
        conversation_repo=FakeConversationRepo(conversation),
        message_repo=message_repo,
        llm_client=llm_client,
        game_repo=None,
    )

    async def run():
        async for _ in service.chat_stream("go north", conversation_id="conv-1"):
            pass

    asyncio.run(run())

    assert llm_client.seen_messages is not None
    assistant_msg = llm_client.seen_messages[0]
    assert "[State:" not in assistant_msg["content"]
    assert assistant_msg["content"] == "Room text."
