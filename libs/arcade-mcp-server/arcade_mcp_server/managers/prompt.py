"""
Prompt Manager

Async-safe prompts with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Callable, Union

from arcade_mcp_server.exceptions import NotFoundError, PromptError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import GetPromptResult, Prompt, PromptMessage

if TYPE_CHECKING:
    from arcade_mcp_server.context import Context

logger = logging.getLogger("arcade.mcp.managers.prompt")

# Prompt handlers come in two flavors:
# - legacy: (args) -> list[PromptMessage]
# - context-aware: (context, args) -> list[PromptMessage], matching tool handlers
PromptHandlerFunc = Union[
    Callable[[dict[str, str]], "list[PromptMessage]"],
    Callable[["Context | None", dict[str, str]], "list[PromptMessage]"],
]


def _handler_accepts_context(handler: Callable) -> bool:
    """Whether a handler uses the context-aware (context, args) signature.

    Handlers with two or more explicit positional parameters are treated as
    context-aware. Handlers whose signature cannot be inspected, or that only
    accept *args, are treated as legacy (args-only).
    """
    try:
        sig = inspect.signature(handler)
    except (TypeError, ValueError):
        return False
    positional = [
        p
        for p in sig.parameters.values()
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) >= 2


class PromptHandler:
    """Handler for generating prompt messages."""

    def __init__(
        self,
        prompt: Prompt,
        handler: PromptHandlerFunc | None = None,
    ) -> None:
        self.prompt = prompt
        self.handler = handler or self._default_handler
        self._accepts_context = handler is not None and _handler_accepts_context(handler)

    def __eq__(self, other: object) -> bool:  # pragma: no cover - simple comparison
        if not isinstance(other, PromptHandler):
            return False
        return self.prompt == other.prompt and self.handler == other.handler

    def _default_handler(self, arguments: dict[str, str]) -> list[PromptMessage]:
        return [
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": self.prompt.description or f"Prompt: {self.prompt.name}",
                },
            )
        ]

    async def get_messages(
        self,
        arguments: dict[str, str] | None = None,
        context: Context | None = None,
    ) -> list[PromptMessage]:
        args = arguments or {}

        # Validate required arguments
        if self.prompt.arguments:
            for arg in self.prompt.arguments:
                if arg.required and arg.name not in args:
                    raise PromptError(f"Required argument '{arg.name}' not provided")

        if self._accepts_context:
            if context is None:
                from arcade_mcp_server.context import get_current_model_context

                context = get_current_model_context()
            result = self.handler(context, args)  # type: ignore[call-arg, arg-type]
        else:
            result = self.handler(args)  # type: ignore[call-arg, arg-type]
        if hasattr(result, "__await__"):
            result = await result

        return result


class PromptManager(ComponentManager[str, PromptHandler]):
    """
    Manages prompts for the MCP server.
    """

    def __init__(self) -> None:
        super().__init__("prompt")

    async def list_prompts(self) -> list[Prompt]:
        handlers = await self.registry.list()
        return [h.prompt for h in handlers]

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, str] | None = None,
        context: Context | None = None,
    ) -> GetPromptResult:
        try:
            handler = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        try:
            messages = await handler.get_messages(arguments, context)
            return GetPromptResult(
                description=handler.prompt.description,
                messages=messages,
            )
        except Exception as e:
            if isinstance(e, PromptError):
                raise
            raise PromptError(f"Error generating prompt: {e}") from e

    async def add_prompt(
        self,
        prompt: Prompt,
        handler: PromptHandlerFunc | None = None,
    ) -> None:
        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)

    async def remove_prompt(self, name: str) -> Prompt:
        try:
            handler = await self.registry.remove(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")
        return handler.prompt

    async def update_prompt(
        self,
        name: str,
        prompt: Prompt,
        handler: PromptHandlerFunc | None = None,
    ) -> Prompt:
        # Ensure exists
        try:
            _ = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)
        return prompt
