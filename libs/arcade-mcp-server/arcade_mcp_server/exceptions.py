"""
MCP Exception Hierarchy

Provides domain-specific exceptions for better error handling and debugging.
"""

from arcade_core.errors import (
    ContextRequiredToolError,
    ErrorKind,
    FatalToolError,
    RetryableToolError,
    ToolExecutionError,
    ToolRuntimeError,
    UpstreamError,
    UpstreamRateLimitError,
)

__all__ = [
    # Re-exports
    "ErrorKind",
    "FatalToolError",
    "RetryableToolError",
    "ToolExecutionError",
    "ToolRuntimeError",
    "UpstreamError",
    "UpstreamRateLimitError",
    "ContextRequiredToolError",
    # Base exceptions
    "MCPError",
    "MCPRuntimeError",
    # Server exceptions
    "ServerError",
    "SessionError",
    "RequestError",
    "ResponseError",
    "ServerRequestError",
    "LifespanError",
    # Context exceptions
    "MCPContextError",
    "NotFoundError",
    "AuthorizationError",
    "PromptError",
    "ResourceError",
    "TransportError",
    "ProtocolError",
]


class MCPError(Exception):
    """Base error for all MCP-related exceptions."""


class MCPRuntimeError(MCPError):
    """Runtime error for all MCP-related exceptions."""


class ServerError(MCPRuntimeError):
    """Error in server operations."""


class SessionError(ServerError):
    """Error in session management"""


class RequestError(ServerError):
    """Error in request processing from client to server"""


class ResponseError(ServerError):
    """Error in request processing from server -> client"""


class ServerRequestError(RequestError):
    """Error in sending request from server -> client initiated by the server"""


class LifespanError(ServerError):
    """Error in lifespan management."""


class MCPContextError(MCPError):
    """Error in context management."""


class NotFoundError(MCPContextError):
    """Requested entity not found."""


class AuthorizationError(MCPContextError):
    """Authorization failure."""


class PromptError(MCPContextError):
    """Error in prompt management."""


class ResourceError(MCPContextError):
    """Error in resource management."""


# Transport and Protocol Errors


class TransportError(MCPRuntimeError):
    """Error in transport layer (stdio, HTTP, etc)."""


class ProtocolError(MCPRuntimeError):
    """Error in MCP protocol handling."""
