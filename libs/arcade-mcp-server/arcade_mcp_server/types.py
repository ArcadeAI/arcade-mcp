from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from arcade_mcp_server.resource_server.base import ResourceOwner

# -----------------------------------------------------------------------------
# JSON-RPC constants
# -----------------------------------------------------------------------------

JSONRPC_VERSION: Literal["2.0"] = "2.0"
LATEST_PROTOCOL_VERSION: str = "2025-06-18"

# -----------------------------------------------------------------------------
# Basic types
# -----------------------------------------------------------------------------

ProgressToken = str | int
Cursor = str
RequestId = str | int
AnyFunction: TypeAlias = Callable[..., Any]


# -----------------------------------------------------------------------------
# Base JSON-RPC shapes
# -----------------------------------------------------------------------------


class Request(BaseModel):
    method: str
    params: Any = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Notification(BaseModel):
    method: str
    params: Any = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Result(BaseModel):
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class JSONRPCMessage(BaseModel):
    jsonrpc: Literal["2.0"] = Field(default=JSONRPC_VERSION, frozen=True)

    model_config = ConfigDict(extra="allow")


class JSONRPCRequest(JSONRPCMessage, Request):
    id: RequestId


T = TypeVar("T", bound=Result)


class JSONRPCResponse(JSONRPCMessage, Generic[T]):
    id: RequestId
    result: T | dict[str, Any]


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ErrorData(BaseModel):
    code: int
    message: str
    data: Any | None = None


class JSONRPCError(JSONRPCMessage):
    id: RequestId
    error: dict[str, Any]


# -----------------------------------------------------------------------------
# Transport types
# -----------------------------------------------------------------------------


@dataclass
class SessionMessage:
    """Wrapper for messages in transport sessions.

    Carries both the MCP protocol message and optional authenticated user
    information from front-door authentication.
    """

    message: JSONRPCMessage
    resource_owner: ResourceOwner | None = None


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------


class BaseMetadata(BaseModel):
    name: str
    title: str | None = None

    model_config = ConfigDict(extra="allow")


class Implementation(BaseMetadata):
    version: str


class ClientCapabilities(BaseModel):
    experimental: dict[str, object] | None = None
    roots: dict[str, Any] | None = None
    sampling: dict[str, Any] | None = None
    elicitation: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class ServerCapabilities(BaseModel):
    experimental: dict[str, object] | None = None
    logging: dict[str, Any] | None = None
    completions: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class InitializeParams(BaseModel):
    protocolVersion: str
    capabilities: ClientCapabilities = Field(default_factory=ClientCapabilities)
    clientInfo: Implementation


class InitializeRequest(JSONRPCRequest):
    method: Literal["initialize"] = Field(default="initialize", frozen=True)
    params: InitializeParams


class InitializeResult(Result):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None


class InitializedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/initialized"] = Field(
        default="notifications/initialized", frozen=True
    )


# -----------------------------------------------------------------------------
# Ping
# -----------------------------------------------------------------------------


class PingRequest(JSONRPCRequest):
    method: Literal["ping"] = Field(default="ping", frozen=True)


# -----------------------------------------------------------------------------
# Progress notifications
# -----------------------------------------------------------------------------


class ProgressNotificationParams(BaseModel):
    progressToken: ProgressToken
    progress: float
    total: float | None = None
    message: str | None = None


class ProgressNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/progress"] = Field(default="notifications/progress", frozen=True)
    params: ProgressNotificationParams


# -----------------------------------------------------------------------------
# Pagination
# -----------------------------------------------------------------------------


class PaginatedRequest(JSONRPCRequest):
    params: dict[str, Any] | None = None


class PaginatedResult(Result):
    nextCursor: Cursor | None = None


# -----------------------------------------------------------------------------
# Annotations (used across resources, content, etc.)
# -----------------------------------------------------------------------------

Role = Literal["user", "assistant"]


class Annotations(BaseModel):
    audience: list[Role] | None = None
    priority: float | None = None
    lastModified: str | None = None

    model_config = ConfigDict(extra="allow")


# -----------------------------------------------------------------------------
# Resources
# -----------------------------------------------------------------------------


class Resource(BaseMetadata):
    uri: str
    description: str | None = None
    mimeType: str | None = None
    annotations: Annotations | None = None
    size: int | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListResourcesRequest(PaginatedRequest):
    method: Literal["resources/list"] = Field(default="resources/list", frozen=True)


class ListResourcesResult(PaginatedResult):
    resources: list[Resource] = Field(default_factory=list)


class ListResourceTemplatesRequest(PaginatedRequest):
    method: Literal["resources/templates/list"] = Field(
        default="resources/templates/list", frozen=True
    )


class ResourceTemplate(BaseMetadata):
    uriTemplate: str
    description: str | None = None
    mimeType: str | None = None
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListResourceTemplatesResult(PaginatedResult):
    resourceTemplates: list[ResourceTemplate] = Field(default_factory=list)


class ReadResourceParams(BaseModel):
    uri: str


class ReadResourceRequest(JSONRPCRequest):
    method: Literal["resources/read"] = Field(default="resources/read", frozen=True)
    params: ReadResourceParams


class ResourceContents(BaseModel):
    uri: str
    mimeType: str | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class TextResourceContents(ResourceContents):
    text: str


class BlobResourceContents(ResourceContents):
    blob: str


class ReadResourceResult(Result):
    contents: list[TextResourceContents | BlobResourceContents]


class ResourceListChangedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/resources/list_changed"] = Field(
        default="notifications/resources/list_changed", frozen=True
    )


class ResourceUpdatedNotificationParams(BaseModel):
    uri: str


class ResourceUpdatedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/resources/updated"] = Field(
        default="notifications/resources/updated", frozen=True
    )
    params: ResourceUpdatedNotificationParams


class SubscribeParams(BaseModel):
    uri: str


class SubscribeRequest(JSONRPCRequest):
    method: Literal["resources/subscribe"] = Field(default="resources/subscribe", frozen=True)
    params: SubscribeParams


class UnsubscribeParams(BaseModel):
    uri: str


class UnsubscribeRequest(JSONRPCRequest):
    method: Literal["resources/unsubscribe"] = Field(default="resources/unsubscribe", frozen=True)
    params: UnsubscribeParams


# -----------------------------------------------------------------------------
# Prompts
# -----------------------------------------------------------------------------


class PromptArgument(BaseMetadata):
    description: str | None = None
    required: bool | None = None


class Prompt(BaseMetadata):
    description: str | None = None
    arguments: list[PromptArgument] | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListPromptsRequest(PaginatedRequest):
    method: Literal["prompts/list"] = Field(default="prompts/list", frozen=True)


class ListPromptsResult(PaginatedResult):
    prompts: list[Prompt] = Field(default_factory=list)


class PromptMessage(BaseModel):
    role: Role
    content: dict[str, Any]


class GetPromptParams(BaseModel):
    name: str
    arguments: dict[str, str] | None = None


class GetPromptRequest(JSONRPCRequest):
    method: Literal["prompts/get"] = Field(default="prompts/get", frozen=True)
    params: GetPromptParams


class GetPromptResult(Result):
    description: str | None = None
    messages: list[PromptMessage]


class PromptListChangedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/prompts/list_changed"] = Field(
        default="notifications/prompts/list_changed", frozen=True
    )


# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------


class ToolAnnotations(BaseModel):
    title: str | None = None
    readOnlyHint: bool | None = None
    destructiveHint: bool | None = None
    idempotentHint: bool | None = None
    openWorldHint: bool | None = None

    model_config = ConfigDict(extra="allow")


class MCPTool(BaseModel):
    name: str
    description: str | None = None
    inputSchema: dict[str, Any]
    outputSchema: dict[str, Any] | None = None
    annotations: ToolAnnotations | None = None
    title: str | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListToolsRequest(PaginatedRequest):
    method: Literal["tools/list"] = Field(default="tools/list", frozen=True)


class ListToolsResult(PaginatedResult):
    tools: list[MCPTool]


class ToolListChangedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/tools/list_changed"] = Field(
        default="notifications/tools/list_changed", frozen=True
    )


class CallToolParams(BaseModel):
    name: str
    arguments: dict[str, Any] | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class CallToolRequest(JSONRPCRequest):
    method: Literal["tools/call"] = Field(default="tools/call", frozen=True)
    params: CallToolParams


class TextContent(BaseModel):
    type: Literal["text"]
    text: str
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ImageContent(BaseModel):
    type: Literal["image"]
    data: str
    mimeType: str
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class AudioContent(BaseModel):
    type: Literal["audio"]
    data: str
    mimeType: str
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ResourceLink(Resource):
    type: Literal["resource_link"] = Field(default="resource_link", frozen=True)


class EmbeddedResource(BaseModel):
    type: Literal["resource"] = Field(default="resource", frozen=True)
    resource: TextResourceContents | BlobResourceContents
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


MCPContent = TextContent | ImageContent | AudioContent | ResourceLink | EmbeddedResource


class CallToolResult(Result):
    """
    A list of content objects that represent the unstructured result of the tool call.
    """

    content: list[MCPContent]

    """
    An optional JSON object that represents the structured result of the tool call.
    """
    structuredContent: dict[str, Any] | None = None

    isError: bool | None = None


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------


class LoggingLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class SetLevelParams(BaseModel):
    level: LoggingLevel


class SetLevelRequest(JSONRPCRequest):
    method: Literal["logging/setLevel"] = Field(default="logging/setLevel", frozen=True)
    params: SetLevelParams


class LoggingMessageParams(BaseModel):
    level: LoggingLevel
    logger: str | None = None
    data: Any


class LoggingMessageNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/message"] = Field(default="notifications/message", frozen=True)
    params: LoggingMessageParams


# -----------------------------------------------------------------------------
# Cancellation (notification-only)
# -----------------------------------------------------------------------------


class CancelledParams(BaseModel):
    requestId: RequestId
    reason: str | None = None


class CancelledNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/cancelled"] = Field(
        default="notifications/cancelled", frozen=True
    )
    params: CancelledParams


# -----------------------------------------------------------------------------
# Sampling (server -> client)
# -----------------------------------------------------------------------------


class SamplingMessage(BaseModel):
    role: Role
    content: TextContent | ImageContent | AudioContent


class ModelHint(BaseModel):
    name: str | None = None


class ModelPreferences(BaseModel):
    hints: list[ModelHint] | None = None
    costPriority: float | None = None
    speedPriority: float | None = None
    intelligencePriority: float | None = None


class CreateMessageParams(BaseModel):
    messages: list[SamplingMessage]
    modelPreferences: ModelPreferences | None = None
    systemPrompt: str | None = None
    includeContext: Literal["none", "thisServer", "allServers"] | None = None
    temperature: float | None = None
    maxTokens: int
    stopSequences: list[str] | None = None
    metadata: dict[str, Any] | None = None


class CreateMessageRequest(JSONRPCRequest):
    method: Literal["sampling/createMessage"] = Field(default="sampling/createMessage", frozen=True)
    params: CreateMessageParams


class CreateMessageResult(Result, SamplingMessage):
    model: str
    stopReason: Literal["endTurn", "stopSequence", "maxTokens"] | str | None = None


# -----------------------------------------------------------------------------
# Completion (client -> server)
# -----------------------------------------------------------------------------


class ResourceTemplateReference(BaseModel):
    type: Literal["ref/resource"]
    uri: str


class PromptReference(BaseMetadata):
    type: Literal["ref/prompt"]


class CompletionArgument(BaseModel):
    name: str
    value: str


class CompletionContext(BaseModel):
    arguments: dict[str, str] | None = None


class CompleteParams(BaseModel):
    ref: ResourceTemplateReference | PromptReference
    argument: CompletionArgument
    context: CompletionContext | None = None


class CompleteRequest(JSONRPCRequest):
    method: Literal["completion/complete"] = Field(default="completion/complete", frozen=True)
    params: CompleteParams


class Completion(BaseModel):
    values: list[str]
    total: int | None = None
    hasMore: bool | None = None


class CompleteResult(Result):
    completion: Completion


# -----------------------------------------------------------------------------
# Roots
# -----------------------------------------------------------------------------


class ListRootsRequest(JSONRPCRequest):
    method: Literal["roots/list"] = Field(default="roots/list", frozen=True)


class Root(BaseModel):
    uri: str
    name: str | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)


class ListRootsResult(Result):
    roots: list[Root]


class RootsListChangedNotification(JSONRPCMessage, Notification):
    method: Literal["notifications/roots/list_changed"] = Field(
        default="notifications/roots/list_changed", frozen=True
    )


# -----------------------------------------------------------------------------
# Elicitation (server -> client)
# -----------------------------------------------------------------------------

ElicitRequestedSchema = dict[str, Any]


class ElicitParams(BaseModel):
    message: str
    requestedSchema: ElicitRequestedSchema


class ElicitRequest(JSONRPCRequest):
    method: Literal["elicitation/create"] = Field(default="elicitation/create", frozen=True)
    params: ElicitParams


class ElicitResult(Result):
    action: Literal["accept", "decline", "cancel"]
    content: dict[str, str | int | float | bool | None] | None = None


# -----------------------------------------------------------------------------
# Union for middleware typing and convenience
# -----------------------------------------------------------------------------

MCPMessage = (
    JSONRPCRequest
    | JSONRPCResponse[Any]
    | JSONRPCError
    | InitializedNotification
    | CancelledNotification
    | ProgressNotification
    | LoggingMessageNotification
    | ResourceListChangedNotification
    | ResourceUpdatedNotification
    | PromptListChangedNotification
    | ToolListChangedNotification
    | RootsListChangedNotification
)
