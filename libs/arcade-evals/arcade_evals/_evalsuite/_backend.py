"""Provider-agnostic inference backends for arcade_evals.

``EvalSuite.run()`` supports ``provider="openai"`` and ``provider="anthropic"``
via a closed enum. This module introduces an ``InferenceBackend`` Protocol that
enables running evals against *any* LLM provider -- Google Gemini, Together AI,
Groq, Fireworks, local Ollama, or any other OpenAI-compatible endpoint.

Quick start::

    from openai import AsyncOpenAI
    from arcade_evals import OpenAICompatBackend

    client = AsyncOpenAI(
        api_key=os.environ["GOOGLE_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    backend = OpenAICompatBackend(client, model="gemini-2.5-flash", seed=None, strict=False)
    results = await suite.run(backend=backend)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry


@runtime_checkable
class InferenceBackend(Protocol):
    """Interface for LLM inference providers used in evals.

    Each backend is responsible for:

    * Converting tool definitions to the provider's expected format
    * Sending the chat completion request with appropriate parameters
    * Parsing tool calls from the provider's response format

    Tool name resolution (e.g. ``Google_Search`` -> ``Google.Search``) is
    handled by ``EvalSuiteToolRegistry.process_tool_call()`` after the
    backend returns, so backends should return raw tool names from the
    provider's response.
    """

    @property
    def model_name(self) -> str:
        """The model identifier for results tracking."""
        ...

    async def call_with_tools(
        self,
        messages: list[dict[str, Any]],
        registry: EvalSuiteToolRegistry,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Send a chat completion request with tools and return parsed tool calls.

        Args:
            messages: Conversation messages in OpenAI format
                (system/user/assistant roles).
            registry: The tool registry. Use
                ``registry.list_tools_for_model(tool_format=...)``
                to get provider-appropriate schemas.

        Returns:
            List of ``(tool_name, arguments)`` tuples as returned by the
            provider. Name resolution is handled by the caller.
        """
        ...


@dataclass
class OpenAICompatBackend:
    """Backend for any OpenAI-compatible endpoint.

    Works with OpenAI, Google Gemini, Together AI, Groq, Fireworks,
    local Ollama, and any provider exposing ``/chat/completions``
    with tool calling support.

    Provider-specific behavior is controlled via constructor parameters::

        # OpenAI (defaults)
        OpenAICompatBackend(client, model="gpt-4o")

        # Gemini (no seed, no strict)
        OpenAICompatBackend(client, model="gemini-2.5-flash", seed=None, strict=False)

        # Together / Groq
        OpenAICompatBackend(client, model="meta-llama/...", seed=None)

    Args:
        client: An ``AsyncOpenAI``-compatible client instance.
        model: The model identifier string.
        seed: Seed for reproducibility. ``None`` to omit (for providers
            that don't support it).
        strict: Whether to keep ``strict: true`` and
            ``additionalProperties: false`` in tool schemas.
            Set ``False`` for providers that reject strict-mode artifacts.
        user: Optional user identifier for audit logging.
    """

    client: Any
    model: str
    seed: int | None = 42
    strict: bool = True
    user: str | None = "eval_user"

    @property
    def model_name(self) -> str:
        return self.model

    async def call_with_tools(
        self,
        messages: list[dict[str, Any]],
        registry: EvalSuiteToolRegistry,
    ) -> list[tuple[str, dict[str, Any]]]:
        tools = registry.list_tools_for_model(tool_format="openai")

        if not self.strict:
            for schema in tools:
                func = schema.get("function", {})
                func.pop("strict", None)
                params = func.get("parameters", {})
                params.pop("additionalProperties", None)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tool_choice": "auto",
            "tools": tools,
            "stream": False,
        }
        if self.seed is not None:
            kwargs["seed"] = self.seed
        if self.user is not None:
            kwargs["user"] = self.user

        response = await self.client.chat.completions.create(**kwargs)

        # Parse OpenAI-format response
        tool_calls: list[tuple[str, dict[str, Any]]] = []
        message = response.choices[0].message
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append((tc.function.name, json.loads(tc.function.arguments)))
        return tool_calls


@dataclass
class AnthropicBackend:
    """Backend for the Anthropic Messages API.

    Converts tool schemas to Anthropic's format and parses
    ``tool_use`` content blocks from the response.

    Args:
        client: An ``AsyncAnthropic`` client instance.
        model: The model identifier string.
        max_tokens: Maximum tokens for the response.
    """

    client: Any
    model: str
    max_tokens: int = 4096

    @property
    def model_name(self) -> str:
        return self.model

    async def call_with_tools(
        self,
        messages: list[dict[str, Any]],
        registry: EvalSuiteToolRegistry,
    ) -> list[tuple[str, dict[str, Any]]]:
        from arcade_evals._evalsuite._providers import convert_messages_to_anthropic

        tools = registry.list_tools_for_model(tool_format="anthropic")

        # Extract system message (Anthropic takes it as a separate parameter)
        system_message = ""
        api_messages = messages
        if messages and messages[0].get("role") == "system":
            system_message = messages[0]["content"]
            api_messages = messages[1:]

        anthropic_messages = convert_messages_to_anthropic(api_messages)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_message,
            messages=anthropic_messages,
            tools=tools,
        )

        tool_calls: list[tuple[str, dict[str, Any]]] = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append((block.name, block.input))
        return tool_calls
