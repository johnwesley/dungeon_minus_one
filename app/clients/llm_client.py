from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
import anthropic

from app.config import get_settings


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send messages and return the complete response."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Send messages and yield response chunks."""
        pass


class AnthropicClient(LLMClient):
    """Anthropic Claude client implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )
        self.model = model or settings.model_name
        self.max_tokens = 4096
        self.default_system_prompt = """You are the narrator of a text-adventure game. Your role is to describe the world, respond to player actions, and keep the story moving. You are clever, dry, and occasionally sarcastic, but never outright hostile. You do not coddle the player.

Follow these principles:
1. Describe scenes vividly but concisely.
2. Present interactable elements clearly (objects, characters, paths).
3. Respond to player input with a mix of guidance and playful sarcasm.
4. Never take control of the player's actions; react to them.
5. Never break character or mention being an AI system.
6. Maintain continuity across steps of the game.

Inputs provided for each session:
- Environment Description: {{ENVIRONMENT}}
- Player: {{PLAYER_INFO}}

Use these as the foundation for narration and interactions."""

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send messages and return the complete response."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt or self.default_system_prompt,
            messages=messages,
        )
        return response.content[0].text

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Send messages and yield response chunks."""
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt or self.default_system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text


def get_llm_client() -> LLMClient:
    """Get the configured LLM client."""
    return AnthropicClient()
