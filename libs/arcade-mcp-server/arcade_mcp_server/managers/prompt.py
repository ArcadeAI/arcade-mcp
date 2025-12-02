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
                    raise PromptError(
                        f"✗ Missing required argument: '{arg.name}'\n\n"
                        f"  Prompt requires this argument but it was not provided.\n\n"
                        f"To fix:\n"
                        f"  Provide the '{arg.name}' argument when calling the prompt"
                    )

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
            raise NotFoundError(
                f"✗ Prompt not found: '{name}'\n\n"
                f"  The requested prompt does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available prompts with prompts/list\n"
                f"  2. Check for typos in the prompt name\n"
                f"  3. Verify the prompt was registered with the server"
            )

        try:
            messages = await handler.get_messages(arguments)
            return GetPromptResult(
                description=handler.prompt.description,
                messages=messages,
            )
        except Exception as e:
            if isinstance(e, PromptError):
                raise
            raise PromptError(
                f"✗ Prompt generation failed\n\n"
                f"  Error: {e}\n\n"
                f"Possible causes:\n"
                f"  1. Invalid arguments provided to the prompt\n"
                f"  2. Error in prompt template rendering\n"
                f"  3. Missing required dependencies\n\n"
                f"Check the error message above for details."
            ) from e

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
            raise NotFoundError(
                f"✗ Prompt not found: '{name}'\n\n"
                f"  The requested prompt does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available prompts with prompts/list\n"
                f"  2. Check for typos in the prompt name\n"
                f"  3. Verify the prompt was registered with the server"
            )
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
            raise NotFoundError(
                f"✗ Prompt not found: '{name}'\n\n"
                f"  The requested prompt does not exist.\n\n"
                f"To fix:\n"
                f"  1. List available prompts with prompts/list\n"
                f"  2. Check for typos in the prompt name\n"
                f"  3. Verify the prompt was registered with the server"
            )

        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)
        return prompt
