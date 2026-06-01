"""
Prompt Manager

Async-safe prompts with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from arcade_mcp_server.exceptions import NotFoundError, PromptError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import GetPromptResult, Prompt, PromptMessage

logger = logging.getLogger("arcade.mcp.managers.prompt")


class PromptHandler:
    """Handler for generating prompt messages."""

    def __init__(
        self,
        prompt: Prompt,
        handler: Callable[..., list[PromptMessage]] | None = None,
    ) -> None:
        self.prompt = prompt
        self.handler = handler or self._default_handler
        self._accepts_context = self._check_accepts_context(self.handler)

    @staticmethod
    def _check_accepts_context(handler: Callable[..., Any]) -> bool:
        """Check if the handler accepts a context parameter (2-parameter signature)."""
        try:
            sig = inspect.signature(handler)
            params = [
                p
                for p in sig.parameters.values()
                if p.name != "self" and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            ]
            return len(params) >= 2
        except (ValueError, TypeError):
            return False

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
        self, arguments: dict[str, str] | None = None, context: Any | None = None
    ) -> list[PromptMessage]:
        args = arguments or {}

        # Validate required arguments
        if self.prompt.arguments:
            for arg in self.prompt.arguments:
                if arg.required and arg.name not in args:
                    raise PromptError(f"Required argument '{arg.name}' not provided")

        if self._accepts_context:
            result = self.handler(context, args)
        else:
            result = self.handler(args)
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
        context: Any | None = None,
    ) -> GetPromptResult:
        try:
            handler = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        try:
            messages = await handler.get_messages(arguments, context=context)
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
        handler: Callable[..., list[PromptMessage]] | None = None,
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
        handler: Callable[..., list[PromptMessage]] | None = None,
    ) -> Prompt:
        # Ensure exists
        try:
            _ = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)
        return prompt
