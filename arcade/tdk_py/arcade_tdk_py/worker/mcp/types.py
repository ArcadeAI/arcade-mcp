import json
from collections.abc import Callable
from typing import (
    Any,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
    Union,
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
    class Meta(BaseModel):
        model_config = ConfigDict(extra="allow")

    meta: Meta | None = Field(alias="_meta", default=None)
    model_config = ConfigDict(extra="allow")


RequestParamsT = TypeVar("RequestParamsT", bound=RequestParams | dict[str, Any] | None)
NotificationParamsT = TypeVar(
    "NotificationParamsT", bound=NotificationParams | dict[str, Any] | None
)
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


class PaginatedResult(Result):
    nextCursor: Cursor | None = None
    model_config = ConfigDict(extra="allow")


class JSONRPCMessage(BaseModel):
    """Base class for all JSON-RPC messages."""

    model_config = ConfigDict(extra="allow")
    jsonrpc: str = Field(default="2.0", frozen=True)


class JSONRPCRequest(JSONRPCMessage):
    """A JSON-RPC request message."""

    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(JSONRPCMessage):
    """A JSON-RPC response message."""

    id: str | int | None
    result: Any = None
    error: dict[str, Any] | None = None

    def model_dump_json(self, **kwargs: Any) -> str:
        """Convert to JSON string with proper formatting."""

        # Convert to dict
        data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }

        # Add result if present
        if self.result is not None:
            # Check if result is a Pydantic model
            if hasattr(self.result, "model_dump"):
                data["result"] = self.result.model_dump(exclude_none=True)
            # Check if result is already a dict/list/primitive
            elif (
                isinstance(self.result, (dict, list, str, int, float, bool)) or self.result is None
            ):
                data["result"] = self.result  # type: ignore[assignment]
            else:
                # Try to convert using str() as a fallback
                data["result"] = str(self.result)

        # Add error if present
        if self.error is not None:
            data["error"] = self.error  # type: ignore[assignment]

        return json.dumps(data, ensure_ascii=False)


class JSONRPCError(JSONRPCMessage):
    """A JSON-RPC error message."""

    id: str | int | None
    error: dict[str, Any]


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ErrorData(BaseModel):
    code: int
    message: str
    data: Any | None = None
    model_config = ConfigDict(extra="allow")


JSONRPCMessageBaseModel = BaseModel | JSONRPCRequest | JSONRPCResponse | JSONRPCError


class EmptyResult(Result):
    pass


class Implementation(BaseModel):
    """Describes the server or client implementation."""

    name: str
    version: str
    model_config = ConfigDict(extra="allow")


class RootsCapability(BaseModel):
    listChanged: bool | None = None
    model_config = ConfigDict(extra="allow")


class SamplingCapability(BaseModel):
    model_config = ConfigDict(extra="allow")


class ClientCapabilities(BaseModel):
    experimental: dict[str, dict[str, Any]] | None = None
    sampling: SamplingCapability | None = None
    roots: RootsCapability | None = None
    model_config = ConfigDict(extra="allow")


class PromptsCapability(BaseModel):
    listChanged: bool | None = None
    model_config = ConfigDict(extra="allow")


class ResourcesCapability(BaseModel):
    subscribe: bool | None = None
    listChanged: bool | None = None
    model_config = ConfigDict(extra="allow")


class ToolsCapability(BaseModel):
    listChanged: bool | None = None
    model_config = ConfigDict(extra="allow")


class LoggingCapability(BaseModel):
    model_config = ConfigDict(extra="allow")


class ServerCapabilities(BaseModel):
    """Describes the server's capabilities."""

    model_config = ConfigDict(extra="allow")
    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None


class InitializeRequestParams(RequestParams):
    protocolVersion: str | int
    capabilities: ClientCapabilities
    clientInfo: Implementation
    model_config = ConfigDict(extra="allow")


class InitializeRequest(JSONRPCRequest):
    method: str = Field(default="initialize", frozen=True)
    params: dict[str, Any] | None = None


class InitializeResult(BaseModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None


class InitializedNotification(
    Notification[NotificationParams | None, Literal["notifications/initialized"]]
):
    method: Literal["notifications/initialized"]
    params: NotificationParams | None = None
    model_config = ConfigDict(extra="allow")


class PingRequest(JSONRPCRequest):
    method: str = Field(default="ping", frozen=True)
    params: dict[str, Any] | None = None


class ProgressNotificationParams(NotificationParams):
    progressToken: ProgressToken
    progress: float
    total: float | None = None
    model_config = ConfigDict(extra="allow")


class ProgressNotification(JSONRPCMessage):
    method: str = Field(default="progress", frozen=True)
    params: dict[str, Any]


class PingResponse(JSONRPCResponse):
    result: dict[str, Any] = Field(default_factory=lambda: {"pong": True})


class ShutdownRequest(JSONRPCRequest):
    method: str = Field(default="shutdown", frozen=True)
    params: dict[str, Any] | None = None


class ShutdownResponse(JSONRPCResponse):
    result: dict[str, Any] = Field(default_factory=lambda: {"ok": True})


class CancelRequest(JSONRPCRequest):
    method: str = Field(default="$/cancelRequest", frozen=True)
    params: dict[str, Any]


class InitializeResponse(JSONRPCResponse):
    """
    Response to an initialize request.

    Note: This must be a properly formatted JSON-RPC response with a `result` field
    containing the initialization data, not another request.
    """

    result: InitializeResult

    def model_dump_json(self, **kwargs: Any) -> str:
        """Convert to JSON string with proper formatting."""
        # Convert to dict
        data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "result": self.result.model_dump(exclude_none=True),
        }

        # Return JSON string
        return json.dumps(data, ensure_ascii=False)


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
    Represents an MCP tool definition.
    """

    name: str
    description: str
    inputSchema: dict[str, Any] | None = None
    annotations: ToolAnnotations | None = None

    model_config = ConfigDict(extra="allow")


class ListToolsResult(BaseModel):
    tools: list[Tool]


class ListToolsResponse(JSONRPCResponse):
    result: ListToolsResult


class CallToolRequest(JSONRPCRequest):
    method: str = Field(default="tools/call", frozen=True)
    params: dict[str, Any]


class CallToolResult(BaseModel):
    content: Any


class CallToolResponse(JSONRPCResponse):
    result: CallToolResult


# Resource and Prompt protocol stubs (expand as needed)
class ListResourcesRequest(JSONRPCRequest):
    method: str = Field(default="resources/list", frozen=True)
    params: dict[str, Any] | None = None


class ListResourcesResponse(JSONRPCResponse):
    result: dict[str, Any]


class ListPromptsRequest(JSONRPCRequest):
    method: str = Field(default="prompts/list", frozen=True)
    params: dict[str, Any] | None = None


class ListPromptsResponse(JSONRPCResponse):
    result: dict[str, Any]


# Utility type alias for all MCP protocol messages
MCPMessage = Union[
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    PingRequest,
    PingResponse,
    InitializeRequest,
    InitializeResponse,
    ListToolsRequest,
    ListToolsResponse,
    CallToolRequest,
    CallToolResponse,
    ProgressNotification,
    CancelRequest,
    ShutdownRequest,
    ShutdownResponse,
    ListResourcesRequest,
    ListResourcesResponse,
    ListPromptsRequest,
    ListPromptsResponse,
]
