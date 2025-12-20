from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Callable, Any
import anthropic
import json
import time

from app.config import get_settings
from prompts import load_prompt, NARRATOR_PROMPT
from app.clients.tools import GAME_TOOLS


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> str:
        """Send messages and return the complete response."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Send messages and yield response chunks."""
        pass

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tool_handlers: dict[str, Callable],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> str:
        """Send messages with tool use and return the complete response."""
        pass

    @abstractmethod
    async def chat_stream_with_tools(
        self,
        messages: list[dict[str, Any]],
        tool_handlers: dict[str, Callable],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send messages with tool use and yield streaming events."""
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
        
        # Load prompts and combine them
        narrator_prompt = load_prompt(NARRATOR_PROMPT)
        try:
            premise_prompt = load_prompt("premise")
            full_system_text = f"{narrator_prompt}\n\n## Game Premise\n{premise_prompt}"
        except FileNotFoundError:
            full_system_text = narrator_prompt

        # Enable Prompt Caching
        self.default_system_prompt = [
            {
                "type": "text",
                "text": full_system_text,
                "cache_control": {"type": "ephemeral"}
            }
        ]

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
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
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
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

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tool_handlers: dict[str, Callable],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> str:
        """Send messages with tool use support.

        Handles the tool use loop: Claude may call tools, we execute them
        and return results, then Claude provides the final response.

        Args:
            messages: Conversation history
            tool_handlers: Dict mapping tool names to async handler functions
            system_prompt: System prompt for the narrator

        Returns:
            Final text response from Claude after all tool use(s)
        """
        # Make a mutable copy of messages for the tool loop
        working_messages = list(messages)

        # Initial request with tools
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt or self.default_system_prompt,
            tools=GAME_TOOLS,
            messages=working_messages,
        )

        # Handle tool use loop
        while response.stop_reason == "tool_use":
            # Extract all tool use blocks from response
            tool_uses = [
                block for block in response.content if block.type == "tool_use"
            ]

            # Execute all tools and collect results
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_input = tool_use.input

                # Execute the tool via handler
                if tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](tool_input)
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                            "is_error": True,
                        })
                        continue
                else:
                    result = f"Tool {tool_name} not implemented"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                        "is_error": True,
                    })
                    continue

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result),
                })

            # Append assistant response and tool results to messages
            working_messages.append({"role": "assistant", "content": response.content})
            working_messages.append({"role": "user", "content": tool_results})

            # Continue conversation with tool results
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt or self.default_system_prompt,
                tools=GAME_TOOLS,
                messages=working_messages,
            )

        # Extract final text response
        for block in response.content:
            if hasattr(block, "text"):
                return block.text

        return ""

    async def chat_stream_with_tools(
        self,
        messages: list[dict[str, Any]],
        tool_handlers: dict[str, Callable],
        system_prompt: Optional[str | list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Send messages with tool use and yield streaming events."""
        # Calculate and log context size
        msg_count = len(messages)
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        print(f"DEBUG: Context - Messages: {msg_count}, Approx Chars: {total_chars}")
        
        # region agent log
        try:
            with open("/Users/johnwesley/github/dungeon_minus_one/.cursor/debug.log", "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "repro-attempt-1",
                    "hypothesisId": "D", 
                    "location": "app/clients/llm_client.py:chat_stream_with_tools",
                    "message": "Context size",
                    "data": {"msg_count": msg_count, "total_chars": total_chars},
                    "timestamp": int(time.time() * 1000)
                }) + "\n")
        except Exception:
            pass
        # endregion

        working_messages = list(messages)

        while True:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt or self.default_system_prompt,
                messages=working_messages,
                tools=GAME_TOOLS,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            # region agent log
                            try:
                                with open("/Users/johnwesley/github/dungeon_minus_one/.cursor/debug.log", "a") as f:
                                    f.write(json.dumps({
                                        "sessionId": "debug-session",
                                        "runId": "repro-attempt-1",
                                        "hypothesisId": "A",
                                        "location": "app/clients/llm_client.py:stream",
                                        "message": "Tool Use Detected",
                                        "data": {"tool": event.content_block.name},
                                        "timestamp": int(time.time() * 1000)
                                    }) + "\n")
                            except Exception:
                                pass
                            # endregion
                            yield {
                                "type": "tool_start",
                                "tool": event.content_block.name
                            }
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield {"type": "text", "content": event.delta.text}

            # Get the complete message from the stream accumulator
            final_message = await stream.get_final_message()
            
            # Append assistant response to history
            working_messages.append({"role": final_message.role, "content": final_message.content})

            # Check if tools were used
            if final_message.stop_reason != "tool_use":
                break

            # Extract tool uses
            tool_uses = [
                block for block in final_message.content if block.type == "tool_use"
            ]

            # Execute tools
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_input = tool_use.input
                tool_id = tool_use.id

                if tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](tool_input)
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result,
                            "is_error": True,
                            "is_error": True,
                        })
                        continue
                else:
                    result = f"Tool {tool_name} not implemented"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                        "is_error": True,
                    })
                    continue

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": str(result),
                })

            # Append tool results to history
            working_messages.append({"role": "user", "content": tool_results})
            yield {"type": "tool_end"}


def get_llm_client() -> LLMClient:
    """Get the configured LLM client."""
    return AnthropicClient()
