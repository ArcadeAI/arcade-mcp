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
from typing import Any, Literal

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
            # Skip system messages - handled separately in Anthropic
            continue

        elif role == "user":
            # User messages convert directly
            content = msg.get("content", "")
            if content:
                anthropic_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            if "tool_calls" in msg:
                # Convert OpenAI tool_calls to Anthropic tool_use blocks
                tool_use_blocks = []
                for tool_call in msg.get("tool_calls", []):
                    # Parse arguments JSON, fallback to empty dict on parse error
                    arguments_str = tool_call.get("function", {}).get("arguments", "{}")
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except json.JSONDecodeError:
                        arguments = {}
                    tool_use_blocks.append({
                        "type": "tool_use",
                        "id": tool_call.get("id", ""),
                        "name": tool_call.get("function", {}).get("name", ""),
                        "input": arguments,
                    })
                if tool_use_blocks:
                    anthropic_messages.append({"role": "assistant", "content": tool_use_blocks})
            else:
                # Regular assistant message
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
            anthropic_messages.append({"role": "user", "content": [tool_result_block]})

        elif role == "function":
            # Legacy OpenAI function role (deprecated) - same as tool
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("name", ""),  # function uses "name" not "tool_call_id"
                "content": msg.get("content", ""),
            }
            anthropic_messages.append({"role": "user", "content": [tool_result_block]})

    return anthropic_messages
