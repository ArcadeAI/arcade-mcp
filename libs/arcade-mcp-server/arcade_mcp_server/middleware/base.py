"""Base middleware classes for MCP server."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from functools import partial
from typing import Any, Generic, Literal, Protocol, TypeVar, cast, runtime_checkable

from arcade_mcp_server.types import (
    CallToolParams,
    CallToolResult,
    GetPromptParams,
    GetPromptResult,
    JSONRPCMessage,
    ListPromptsRequest,
    ListResourcesRequest,
    ListResourceTemplatesRequest,
    ListToolsRequest,
    MCPTool,
    Prompt,
    ReadResourceParams,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
)

T = TypeVar("T")
R = TypeVar("R", covariant=True)


@runtime_checkable
class CallNext(Protocol[T, R]):
    """Protocol for the next handler in the middleware chain."""

    def __call__(self, context: "MiddlewareContext[T]") -> Awaitable[R]: ...


@dataclass(kw_only=True)
class MiddlewareContext(Generic[T]):
    """Context passed through the middleware chain.

    Contains the message being processed and metadata about the request.
    """

    # The message being processed
    message: T

    # The MCP context (optional, set when in request context)
    mcp_context: Any | None = None

    # Metadata
    source: Literal["client", "server"] = "client"
    type: Literal["request", "notification"] = "request"
    method: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Request-specific metadata
    request_id: str | None = None
    session_id: str | None = None

    # Additional metadata that can be added by middleware
    metadata: dict[str, Any] = field(default_factory=dict)

    def copy(self, **kwargs: Any) -> "MiddlewareContext[T]":
        """Create a copy with updated fields."""
        return replace(self, **kwargs)


class Middleware:
    """Base class for MCP middleware with typed handlers for each method.

    Middleware can intercept and modify requests and responses at various
    stages of processing. Each handler receives the context and a call_next
    function to invoke the next handler in the chain.
    """

    async def __call__(
        self,
        context: MiddlewareContext[T],
        call_next: CallNext[T, Any],
    ) -> Any:
        """Main entry point that orchestrates the middleware chain."""
        # Build handler chain based on message type
        handler = await self._build_handler_chain(context, call_next)
        return await handler(context)

    async def _build_handler_chain(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> CallNext[Any, Any]:
        """Build the handler chain for the specific message type."""
        handler = call_next

        # Method-specific handlers
        if context.method:
            match context.method:
                case "tools/call":
                    handler = partial(self.on_call_tool, call_next=handler)
                case "tools/list":
                    handler = partial(self.on_list_tools, call_next=handler)
                case "resources/read":
                    handler = partial(self.on_read_resource, call_next=handler)
                case "resources/list":
                    handler = partial(self.on_list_resources, call_next=handler)
                case "resources/templates/list":
                    handler = partial(self.on_list_resource_templates, call_next=handler)
                case "prompts/get":
                    handler = partial(self.on_get_prompt, call_next=handler)
                case "prompts/list":
                    handler = partial(self.on_list_prompts, call_next=handler)

        # Type-specific handlers
        match context.type:
            case "request":
                handler = partial(self.on_request, call_next=handler)
            case "notification":
                handler = partial(self.on_notification, call_next=handler)

        # Generic message handler (always runs)
        handler = partial(self.on_message, call_next=handler)

        return handler

    # Generic handlers
    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Handle any message. Override to add generic processing."""
        return await call_next(context)

    async def on_request(
        self,
        context: MiddlewareContext[JSONRPCMessage],
        call_next: CallNext[JSONRPCMessage, Any],
    ) -> Any:
        """Handle request messages. Override to add request processing."""
        return await call_next(context)

    async def on_notification(
        self,
        context: MiddlewareContext[JSONRPCMessage],
        call_next: CallNext[JSONRPCMessage, Any],
    ) -> Any:
        """Handle notification messages. Override to add notification processing."""
        return await call_next(context)

    # Tool handlers
    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolParams],
        call_next: CallNext[CallToolParams, CallToolResult],
    ) -> CallToolResult:
        """Handle tool calls. Override to add tool-specific processing."""
        return await call_next(context)

    async def on_list_tools(
        self,
        context: MiddlewareContext[ListToolsRequest],
        call_next: CallNext[ListToolsRequest, list[MCPTool]],
    ) -> list[MCPTool]:
        """Handle tool listing. Override to filter or modify tool list."""
        return await call_next(context)

    # Resource handlers
    async def on_read_resource(
        self,
        context: MiddlewareContext[ReadResourceParams],
        call_next: CallNext[ReadResourceParams, ReadResourceResult],
    ) -> ReadResourceResult:
        """Handle resource reading. Override to add resource processing."""
        return await call_next(context)

    async def on_list_resources(
        self,
        context: MiddlewareContext[ListResourcesRequest],
        call_next: CallNext[ListResourcesRequest, list[Resource]],
    ) -> list[Resource]:
        """Handle resource listing. Override to filter or modify resource list."""
        return await call_next(context)

    async def on_list_resource_templates(
        self,
        context: MiddlewareContext[ListResourceTemplatesRequest],
        call_next: CallNext[ListResourceTemplatesRequest, list[ResourceTemplate]],
    ) -> list[ResourceTemplate]:
        """Handle resource template listing. Override to filter or modify template list."""
        return await call_next(context)

    # Prompt handlers
    async def on_get_prompt(
        self,
        context: MiddlewareContext[GetPromptParams],
        call_next: CallNext[GetPromptParams, GetPromptResult],
    ) -> GetPromptResult:
        """Handle prompt retrieval. Override to add prompt processing."""
        return await call_next(context)

    async def on_list_prompts(
        self,
        context: MiddlewareContext[ListPromptsRequest],
        call_next: CallNext[ListPromptsRequest, list[Prompt]],
    ) -> list[Prompt]:
        """Handle prompt listing. Override to filter or modify prompt list."""
        return await call_next(context)


def compose_middleware(
    *middleware: Middleware,
) -> Callable[[MiddlewareContext[T], CallNext[T, R]], Awaitable[R]]:
    """Compose multiple middleware into a single handler.

    The middleware are applied in reverse order, so the first middleware
    in the list is the outermost (runs first on request, last on response).
    """

    async def composed(
        context: MiddlewareContext[T],
        call_next: CallNext[T, R],
    ) -> R:
        # Build the chain in reverse order into a CallNext[T, R]
        current: CallNext[T, R] = call_next

        for mw in reversed(middleware):

            async def wrapper(
                ctx: MiddlewareContext[T],
                next_handler: CallNext[T, R] = current,
                m: Middleware = mw,
            ) -> R:
                result = await m(ctx, next_handler)
                return cast(R, result)

            # wrapper conforms to CallNext[T, R]
            current = wrapper  # type: ignore[assignment]

        return await current(context)

    return composed
