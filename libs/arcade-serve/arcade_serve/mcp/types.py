from collections.abc import Callable
from typing import (
    Any,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
)

from pydantic import BaseModel, ConfigDict, Field

ProgressToken = str | int
Cursor = str
Role = Literal["user", "assistant"]
RequestId = str | int
AnyFunction: TypeAlias = Callable[..., Any]


class RequestParams(BaseModel):
    class Meta(BaseModel):
        progressToken: ProgressToken | None = None
        model_config = ConfigDict(extra="allow")

    meta: Meta | None = Field(alias="_meta", default=None)

    model_config = ConfigDict(extra="allow")


class NotificationParams(BaseModel):
    """Base notification parameters with metadata support."""

    class Meta(BaseModel):
        model_config = ConfigDict(extra="allow")

    meta: Meta | None = Field(alias="_meta", default=None)
    model_config = ConfigDict(extra="allow", populate_by_name=True)


RequestParamsT = TypeVar("RequestParamsT", bound=RequestParams)
NotificationParamsT = TypeVar("NotificationParamsT", bound=NotificationParams)
MethodT = TypeVar("MethodT", bound=str)


class Request(BaseModel, Generic[RequestParamsT, MethodT]):
    method: MethodT
    params: RequestParamsT
    model_config = ConfigDict(extra="allow")


class PaginatedRequest(Request[RequestParamsT, MethodT]):
    cursor: Cursor | None = None
    model_config = ConfigDict(extra="allow")


class Notification(BaseModel, Generic[NotificationParamsT, MethodT]):
    method: MethodT
    params: NotificationParamsT
    model_config = ConfigDict(extra="allow")


class Result(BaseModel):
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    model_config = ConfigDict(extra="allow")


# Generic JSONRPC Message types for better type safety
T = TypeVar("T", bound=Result)


class JSONRPCMessage(BaseModel):
    """Base class for all JSON-RPC messages."""

    model_config = ConfigDict(extra="allow")
    jsonrpc: str = Field(default="2.0", frozen=True)


class JSONRPCRequest(JSONRPCMessage):
    """A JSON-RPC request message."""

    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(BaseModel, Generic[T]):
    """Typed JSON-RPC response with result type parameter."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: RequestId
    result: T


class PaginatedResult(Result):
    nextCursor: Cursor | None = None
    model_config = ConfigDict(extra="allow")


# -----------------------------
# Additional MCP message types
# -----------------------------


# Error messages and helpers
class JSONRPCError(JSONRPCMessage):
    """A JSON-RPC error message."""

    id: str | int | None
    error: dict[str, Any]


class ErrorData(BaseModel):
    code: int
    message: str
    data: Any | None = None
    model_config = ConfigDict(extra="allow")


# Common responses
class PingRequest(JSONRPCRequest):
    method: str = Field(default="ping", frozen=True)
    params: dict[str, Any] | None = None


class PingResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any] = Field(default_factory=lambda: {})


class ShutdownRequest(JSONRPCRequest):
    method: str = Field(default="shutdown", frozen=True)
    params: dict[str, Any] | None = None


class ShutdownResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any] = Field(default_factory=lambda: {"ok": True})


class CancelRequest(JSONRPCRequest):
    method: str = Field(default="$/cancelRequest", frozen=True)
    params: dict[str, Any]


# Initialize
class Implementation(BaseModel):
    """Describes the name and version of an MCP implementation, with an optional title for UI representation."""

    name: str
    version: str
    title: str | None = None
    model_config = ConfigDict(extra="allow")


class ServerCapabilities(BaseModel):
    """Describes the server's capabilities."""

    model_config = ConfigDict(extra="allow")
    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    notifications: dict[str, Any] | None = None


class InitializeResult(BaseModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None


class InitializeResponse(JSONRPCResponse[InitializeResult]):
    result: InitializeResult


class InitializeRequest(JSONRPCRequest):
    method: str = Field(default="initialize", frozen=True)
    params: dict[str, Any] | None = None


# Tools list and call
class ListToolsRequest(JSONRPCRequest):
    method: str = Field(default="tools/list", frozen=True)
    params: dict[str, Any] | None = None


class ToolAnnotations(BaseModel):
    """
    Represents tool annotations for hints about behavior.
    """

    title: str | None = None
    readOnlyHint: bool | None = None
    destructiveHint: bool | None = None
    idempotentHint: bool | None = None
    openWorldHint: bool | None = None
    model_config = ConfigDict(extra="allow")


class Tool(BaseModel):
    """
    Definition for a tool the client can call.
    """

    name: str
    title: str | None = None
    description: str | None = None
    inputSchema: dict[str, Any]
    outputSchema: dict[str, Any] | None = None
    annotations: ToolAnnotations | None = None
    meta_: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListToolsResult(BaseModel):
    tools: list[Tool]


class ListToolsResponse(JSONRPCResponse[ListToolsResult]):
    result: ListToolsResult


class CallToolRequest(JSONRPCRequest):
    method: str = Field(default="tools/call", frozen=True)
    params: dict[str, Any]


class CallToolResult(BaseModel):
    """The server's response to a tool call."""

    content: list[dict[str, Any]]
    isError: bool | None = None
    structuredContent: dict[str, Any] | list[Any] | None = None
    meta_: dict[str, Any] | None = Field(alias="_meta", default=None)


class CallToolResponse(JSONRPCResponse[CallToolResult]):
    result: CallToolResult


# Resources and prompts
class ListResourcesRequest(JSONRPCRequest):
    method: str = Field(default="resources/list", frozen=True)
    params: dict[str, Any] | None = None


class ListResourcesResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any]


class ListPromptsRequest(JSONRPCRequest):
    method: str = Field(default="prompts/list", frozen=True)
    params: dict[str, Any] | None = None


class ListPromptsResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any]


# Logging level enum used by notifications
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


# Notification models
class NotificationCapability(BaseModel):
    method: str


class NotificationSubscription(BaseModel):
    subscription_id: str
    method: str
    created_at: float
    filters: dict[str, Any] | None = None


class EnhancedProgressNotificationParams(NotificationParams):
    progressToken: ProgressToken
    progress: float
    total: float | None = None
    message: str | None = None


class EnhancedProgressNotification(
    Notification[EnhancedProgressNotificationParams, Literal["notifications/progress"]]
):
    method: Literal["notifications/progress"]
    params: EnhancedProgressNotificationParams


class LoggingMessageNotificationParams(NotificationParams):
    level: LogLevel
    data: Any
    logger: str | None = None


class LoggingMessageNotification(
    Notification[LoggingMessageNotificationParams, Literal["notifications/message"]]
):
    method: Literal["notifications/message"]
    params: LoggingMessageNotificationParams


class ResourceUpdatedNotificationParams(NotificationParams):
    uri: str
    timestamp: str | None = None


class ResourceUpdatedNotification(
    Notification[
        ResourceUpdatedNotificationParams,
        Literal["notifications/resources/updated"],
    ]
):
    method: Literal["notifications/resources/updated"]
    params: ResourceUpdatedNotificationParams


class ResourceListChangedNotificationParams(NotificationParams):
    pass


class ResourceListChangedNotification(
    Notification[
        ResourceListChangedNotificationParams,
        Literal["notifications/resources/list_changed"],
    ]
):
    method: Literal["notifications/resources/list_changed"]
    params: ResourceListChangedNotificationParams


class ToolListChangedNotificationParams(NotificationParams):
    pass


class ToolListChangedNotification(
    Notification[
        ToolListChangedNotificationParams,
        Literal["notifications/tools/list_changed"],
    ]
):
    method: Literal["notifications/tools/list_changed"]
    params: ToolListChangedNotificationParams


class CancelledNotificationParams(NotificationParams):
    requestId: str | int
    reason: str | None = None


class CancelledNotification(
    Notification[CancelledNotificationParams, Literal["notifications/cancelled"]]
):
    method: Literal["notifications/cancelled"]
    params: CancelledNotificationParams


# Logging set level
class SetLevelRequest(JSONRPCRequest):
    method: str = Field(default="logging/setLevel", frozen=True)
    params: dict[str, Any]


class SetLevelResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any] = Field(default_factory=lambda: {})


# Subscription requests
class SubscribeRequest(JSONRPCRequest):
    method: str = Field(default="notifications/subscribe", frozen=True)
    params: dict[str, Any]


class SubscribeResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any]


class UnsubscribeRequest(JSONRPCRequest):
    method: str = Field(default="notifications/unsubscribe", frozen=True)
    params: dict[str, Any]


class UnsubscribeResponse(JSONRPCResponse[dict[str, Any]]):
    result: dict[str, Any]


# Union for all messages (handy for middleware typing)
MCPMessage = (
    JSONRPCRequest
    | JSONRPCResponse[Any]
    | JSONRPCError
    | PingRequest
    | PingResponse
    | InitializeRequest
    | InitializeResponse
    | ListToolsRequest
    | ListToolsResponse
    | CallToolRequest
    | CallToolResponse
    | CancelRequest
    | ShutdownRequest
    | ShutdownResponse
    | ListResourcesRequest
    | ListResourcesResponse
    | ListPromptsRequest
    | ListPromptsResponse
    | SetLevelRequest
    | SetLevelResponse
    | SubscribeRequest
    | SubscribeResponse
    | UnsubscribeRequest
    | UnsubscribeResponse
)
