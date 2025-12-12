"""
Prompt Manager

Async-safe prompts with registry-based storage and deterministic listing.
"""

from __future__ import annotations

import inspect
import logging
import types
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

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
        from arcade_mcp_server.context import Context as ArcadeContext

        def _is_context_annotation(ann: Any) -> bool:
            """Return True only for the actual Context type (or Optional/Union/Annotated wrappers).

            Important: do NOT do substring matching on string annotations. That can produce false
            positives for unrelated types like ContextManager/ExecutionContext/etc.
            """
            if ann is ArcadeContext:
                return True

            # Real class annotations (including subclasses).
            if isinstance(ann, type) and issubclass(ann, ArcadeContext):
                return True

            # Unwrap common typing wrappers.
            origin = get_origin(ann)
            if origin is Annotated:
                args = get_args(ann)
                return _is_context_annotation(args[0]) if args else False

            if origin is Union or origin is types.UnionType:
                return any(_is_context_annotation(a) for a in get_args(ann))

            # Conservative fallback for unresolved forward refs (strings).
            if isinstance(ann, str):
                s = ann.strip().strip("'\"")

                # Handle PEP604 unions in string form: "Context | None"
                if "|" in s:
                    return any(_is_context_annotation(part.strip()) for part in s.split("|"))

                # Handle Optional/Union/Annotated in string form. We only unwrap these;
                # we intentionally do NOT look inside arbitrary generics like ContextManager[...].
                for wrapper in ("Optional[", "Union[", "Annotated["):
                    if s.startswith(wrapper) and s.endswith("]"):
                        inner = s[len(wrapper) : -1].strip()
                        if wrapper == "Union[":
                            return any(_is_context_annotation(p.strip()) for p in inner.split(","))
                        if wrapper == "Annotated[":
                            first = inner.split(",", 1)[0].strip()
                            return _is_context_annotation(first)
                        # Optional[
                        return _is_context_annotation(inner)

                # Accept only the actual arcade_mcp_server Context name(s).
                return s in {"Context", "arcade_mcp_server.context.Context", "arcade_mcp_server.Context"}

            return False

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
                ann: Any = first_param.annotation

                # Prefer resolving type hints (handles forward refs, Optional/Union, etc.)
                try:
                    import arcade_mcp_server

                    globalns = getattr(handler, "__globals__", {}) or {}
                    if "arcade_mcp_server" not in globalns:
                        # Avoid mutating handler globals in-place.
                        globalns = dict(globalns)
                        globalns["arcade_mcp_server"] = arcade_mcp_server

                    hints = get_type_hints(
                        handler,
                        globalns=globalns,
                        localns={"Context": ArcadeContext},
                        include_extras=True,
                    )
                    ann = hints.get(first_param.name, ann)
                except Exception:
                    # Fall back to raw signature annotation.
                    logger.debug(
                        "Failed to resolve prompt handler type hints; falling back to raw signature annotations",
                        exc_info=True,
                    )
                    ann = first_param.annotation

                return _is_context_annotation(ann)
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
