from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Callable, Any
import anthropic
import json
import time
import os

from app.config import get_settings
from prompts import load_prompt, NARRATOR_PROMPT
from app.clients.tools import GAME_TOOLS

# Debug flag - set DEBUG_LLM=true to log detailed API payloads
DEBUG_LLM = os.environ.get("DEBUG_LLM", "").lower() == "true"
DEBUG_LLM_LOG_PATH = os.path.join(os.path.dirname(__file__), "../../.cursor/llm_debug.log")


def log_llm_debug(data: dict):
    """Write LLM debug data to log file as JSON line."""
    if not DEBUG_LLM:
        return
    try:
        os.makedirs(os.path.dirname(DEBUG_LLM_LOG_PATH), exist_ok=True)
        with open(DEBUG_LLM_LOG_PATH, "a") as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception:
        pass


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

        # Enhanced debug logging
        log_llm_debug({
            "event": "api_call_start",
            "timestamp": int(time.time() * 1000),
            "msg_count": msg_count,
            "total_chars": total_chars,
            "messages": [
                {
                    "role": m.get("role"),
                    "content_preview": str(m.get("content", ""))[:200]
                }
                for m in messages
            ],
            "system_prompt_preview": str(system_prompt)[:500] if system_prompt else None,
        })

        working_messages = list(messages)
        iteration = 0

        while True:
            iteration += 1
            log_llm_debug({
                "event": "stream_iteration_start",
                "timestamp": int(time.time() * 1000),
                "iteration": iteration,
                "working_messages_count": len(working_messages),
            })

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
                            log_llm_debug({
                                "event": "tool_use_detected",
                                "timestamp": int(time.time() * 1000),
                                "iteration": iteration,
                                "tool": event.content_block.name,
                            })
                            yield {
                                "type": "tool_start",
                                "tool": event.content_block.name
                            }
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield {"type": "text", "content": event.delta.text}

            # Get the complete message from the stream accumulator
            final_message = await stream.get_final_message()

            log_llm_debug({
                "event": "stream_iteration_end",
                "timestamp": int(time.time() * 1000),
                "iteration": iteration,
                "stop_reason": final_message.stop_reason,
                "content_blocks": len(final_message.content),
            })

            # Append assistant response to history
            working_messages.append({"role": final_message.role, "content": final_message.content})

            # Check if tools were used
            if final_message.stop_reason != "tool_use":
                log_llm_debug({
                    "event": "api_call_complete",
                    "timestamp": int(time.time() * 1000),
                    "iterations": iteration,
                    "final_stop_reason": final_message.stop_reason,
                })
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

                log_llm_debug({
                    "event": "tool_execution_start",
                    "timestamp": int(time.time() * 1000),
                    "iteration": iteration,
                    "tool": tool_name,
                    "input": tool_input,
                })

                if tool_name in tool_handlers:
                    try:
                        result = await tool_handlers[tool_name](tool_input)
                        log_llm_debug({
                            "event": "tool_execution_success",
                            "timestamp": int(time.time() * 1000),
                            "tool": tool_name,
                            "result_preview": str(result)[:300],
                        })
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        log_llm_debug({
                            "event": "tool_execution_error",
                            "timestamp": int(time.time() * 1000),
                            "tool": tool_name,
                            "error": str(e),
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result,
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
