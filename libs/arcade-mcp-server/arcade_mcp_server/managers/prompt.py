"""
Prompt Manager

Async-safe prompts with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable, Union, cast

from arcade_mcp_server.exceptions import NotFoundError, PromptError
from arcade_mcp_server.managers.base import ComponentManager
from arcade_mcp_server.types import GetPromptResult, Prompt, PromptMessage

if TYPE_CHECKING:
    from arcade_mcp_server.context import Context

logger = logging.getLogger("arcade.mcp.managers.prompt")

# Type aliases for prompt handler signatures
PromptHandlerLegacy = Callable[[dict[str, str]], list[PromptMessage]]
PromptHandlerWithContext = Callable[["Context", dict[str, str]], list[PromptMessage]]
PromptHandlerType = Union[PromptHandlerLegacy, PromptHandlerWithContext]


class PromptHandler:
    """Handler for generating prompt messages.

    Supports two handler signatures:
    1. Legacy: handler(args: dict[str, str]) -> list[PromptMessage]
    2. New (with context): handler(context: Context, args: dict[str, str]) -> list[PromptMessage]

    The handler signature is detected automatically using introspection.
    """

    def __init__(
        self,
        prompt: Prompt,
        handler: PromptHandlerType | None = None,
    ) -> None:
        self.prompt = prompt
        self.handler: Any = handler or self._default_handler
        self._accepts_context = self._check_context_signature(self.handler)

    def __eq__(self, other: object) -> bool:  # pragma: no cover - simple comparison
        if not isinstance(other, PromptHandler):
            return False
        return self.prompt == other.prompt and self.handler == other.handler

    def _check_context_signature(self, handler: Any) -> bool:
        """Check if handler accepts context parameter.

        Returns True if the first parameter is type-annotated as Context or named "context"
        without a conflicting type annotation. Returns False for legacy signatures.

        Examples:
            - handler(context: Context, args) -> True (typed context)
            - handler(context, args) -> True (untyped context)
            - handler(context: dict[str, str]) -> False (legacy with misleading name)
            - handler(args) -> False (legacy)
        """
        try:
            sig = inspect.signature(handler)
            params = list(sig.parameters.values())
            # Filter out 'self' parameter for bound methods
            params = [p for p in params if p.name != "self"]

            if not params:
                return False

            first_param = params[0]

            # Check if first parameter is type-annotated
            if first_param.annotation != inspect.Parameter.empty:
                annotation_str = str(first_param.annotation)
                # Only return True if the type annotation contains "Context"
                # This handles Context, arcade_mcp_server.context.Context, etc.
                return "Context" in annotation_str
            else:
                # No type annotation - check if named "context" (untyped context handler)
                return first_param.name == "context"
        except (ValueError, TypeError):
            # If we can't inspect, assume legacy signature
            return False

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

        # Call handler with appropriate signature
        result: Any
        if self._accepts_context:
            if context is None:
                raise PromptError("Handler requires context but none was provided")
            result = self.handler(context, args)
        else:
            result = self.handler(args)

        if hasattr(result, "__await__"):
            result = await result

        # Cast result to expected type after dynamic invocation
        return cast(list[PromptMessage], result)


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
        handler: PromptHandlerType | None = None,
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
        handler: PromptHandlerType | None = None,
    ) -> Prompt:
        # Ensure exists
        try:
            _ = await self.registry.get(name)
        except KeyError:
            raise NotFoundError(f"Prompt '{name}' not found")

        prompt_handler = PromptHandler(prompt, handler)
        await self.registry.upsert(prompt.name, prompt_handler)
        return prompt
