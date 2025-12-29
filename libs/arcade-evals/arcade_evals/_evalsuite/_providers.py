"""Provider abstractions and message conversion utilities.

This module contains:
- ProviderName type for supported LLM providers
- Message conversion utilities for different provider formats

Anthropic has different message format requirements than OpenAI:
- Only "user" and "assistant" roles (system is a separate parameter)
- tool_use/tool_result content blocks instead of tool_calls/tool role
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Supported LLM providers for evaluations
ProviderName = Literal["openai", "anthropic"]


def convert_messages_to_anthropic(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert OpenAI-format messages to Anthropic format.

    Anthropic only supports "user" and "assistant" roles (system is a separate parameter).

    Key differences handled:
    - "system" -> skipped (handled separately in Anthropic API)
    - "user" -> "user" (pass through)
    - "assistant" -> "assistant" (pass through)
    - "assistant" with "tool_calls" -> "assistant" with tool_use content blocks
    - "tool" -> "user" with tool_result content block
    - "function" (legacy) -> "user" with tool_result content block

    Args:
        messages: List of OpenAI-format messages

    Returns:
        List of Anthropic-format messages
    """
    anthropic_messages: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "")

        if role == "system":
            # Skip system messages - Anthropic API takes system as a separate parameter.
            # In _run_anthropic(), we pass system=case.system_message to client.messages.create().
            # This is the correct approach per Anthropic's API design.
            continue

        elif role == "user":
            # User messages convert directly
            content = msg.get("content", "")
            if content:
                anthropic_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            if "tool_calls" in msg and msg.get("tool_calls"):
                # Convert OpenAI tool_calls to Anthropic tool_use blocks
                # Anthropic supports mixed content: text blocks + tool_use blocks
                content_blocks: list[dict[str, Any]] = []

                # Include text content if present (assistant can say something before using tools)
                text_content = msg.get("content")
                if text_content:
                    content_blocks.append({"type": "text", "text": text_content})

                # Add tool_use blocks
                for tool_call in msg.get("tool_calls", []):
                    function = tool_call.get("function")
                    if not function:
                        continue  # Skip malformed tool calls

                    # Parse arguments JSON
                    arguments_str = function.get("arguments", "{}")
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "Failed to parse tool arguments JSON for '%s': %s. Using empty dict.",
                            function.get("name", "unknown"),
                            e,
                        )
                        arguments = {}

                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call.get("id", ""),
                        "name": function.get("name", ""),
                        "input": arguments,
                    })

                if content_blocks:
                    anthropic_messages.append({"role": "assistant", "content": content_blocks})
            else:
                # Regular assistant message (no tool calls)
                content = msg.get("content", "")
                if content:
                    anthropic_messages.append({"role": "assistant", "content": content})

        elif role == "tool":
            # Convert OpenAI tool response to Anthropic tool_result block
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id", ""),
                "content": msg.get("content", ""),
            }
            # Batch consecutive tool results into the last user message
            if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                # Add to existing user message's content array
                last_content = anthropic_messages[-1]["content"]
                if isinstance(last_content, list):
                    last_content.append(tool_result_block)
                else:
                    # Convert string content to array with both blocks
                    anthropic_messages[-1]["content"] = [
                        {"type": "text", "text": last_content},
                        tool_result_block,
                    ]
            else:
                # Start new user message with tool result
                anthropic_messages.append({"role": "user", "content": [tool_result_block]})

        elif role == "function":
            # Legacy OpenAI function role (deprecated) - same as tool
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("name", ""),  # function uses "name" not "tool_call_id"
                "content": msg.get("content", ""),
            }
            # Batch consecutive tool results into the last user message
            if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                # Add to existing user message's content array
                last_content = anthropic_messages[-1]["content"]
                if isinstance(last_content, list):
                    last_content.append(tool_result_block)
                else:
                    # Convert string content to array with both blocks
                    anthropic_messages[-1]["content"] = [
                        {"type": "text", "text": last_content},
                        tool_result_block,
                    ]
            else:
                # Start new user message with tool result
                anthropic_messages.append({"role": "user", "content": [tool_result_block]})

    return anthropic_messages
