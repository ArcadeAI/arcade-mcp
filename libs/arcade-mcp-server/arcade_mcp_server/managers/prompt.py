"""
Prompt Manager

Async-safe prompts with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import logging
from typing import Callable

from arcade_mcp_server.exceptions import NotFoundError, PromptError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import GetPromptResult, Prompt, PromptMessage

logger = logging.getLogger("arcade.mcp.managers.prompt")


class PromptHandler:
    """Handler for generating prompt messages."""

    def __init__(
        self,
        prompt: Prompt,
        handler: Callable[[dict[str, str]], list[PromptMessage]] | None = None,
    ) -> None:
        self.prompt = prompt
        self.handler = handler or self._default_handler

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

    async def get_messages(self, arguments: dict[str, str] | None = None) -> list[PromptMessage]:
        args = arguments or {}

        # Validate required arguments
        if self.prompt.arguments:
            for arg in self.prompt.arguments:
                if arg.required and arg.name not in args:
                    raise PromptError(f"Required argument '{arg.name}' not provided")

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
        self, name: str, arguments: dict[str, str] | None = None
    ) -> GetPromptResult:
        try:
            handler = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        try:
            messages = await handler.get_messages(arguments)
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
        handler: Callable[[dict[str, str]], list[PromptMessage]] | None = None,
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
        handler: Callable[[dict[str, str]], list[PromptMessage]] | None = None,
    ) -> Prompt:
        # Ensure exists
        try:
            _ = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)
        return prompt
