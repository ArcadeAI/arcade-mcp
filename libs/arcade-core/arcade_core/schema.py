"""
Arcade Core Schema

Defines transport-agnostic tool schemas and runtime context protocols used
across Arcade libraries. This includes:

- Tool and toolkit specifications (parameters, outputs, requirements)
- Transport-agnostic ToolContext carrying authorization, secrets, metadata
- Runtime ModelContext Protocol and its namespaced sub-protocols for logs,
  progress, resources, tools, prompts, sampling, UI, and notifications

Note: ToolContext does not embed runtime capabilities; those are provided by
implementations of ModelContext (e.g., in arcade-mcp-server) that subclasses ToolContext
to expose the namespaced APIs to tools without changing function signatures.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from arcade_core.errors import ErrorKind

# allow for custom tool name separator
TOOL_NAME_SEPARATOR = os.getenv("ARCADE_TOOL_NAME_SEPARATOR", ".")


# =====================
# MCP Feature Protocols and No-Op Implementations
# =====================
# These protocols and stubs enable graceful degradation of MCP features
# in deployed (non-local) environments where the full MCP context is not available.


class LogsProtocol(Protocol):
    """Protocol for logging interface."""

    async def log(
        self,
        level: str,
        message: str,
        logger_name: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None: ...

    async def debug(self, message: str, **kwargs: Any) -> None: ...

    async def info(self, message: str, **kwargs: Any) -> None: ...

    async def warning(self, message: str, **kwargs: Any) -> None: ...

    async def error(self, message: str, **kwargs: Any) -> None: ...


class ProgressProtocol(Protocol):
    """Protocol for progress reporting interface."""

    async def report(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None: ...


class _NoOpLogs:
    """No-op implementation for logging in deployed environments."""

    async def log(
        self,
        level: str,
        message: str,
        logger_name: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def debug(self, message: str, **kwargs: Any) -> None:
        pass

    async def info(self, message: str, **kwargs: Any) -> None:
        pass

    async def warning(self, message: str, **kwargs: Any) -> None:
        pass

    async def error(self, message: str, **kwargs: Any) -> None:
        pass


class _NoOpProgress:
    """No-op implementation for progress in deployed environments."""

    async def report(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        pass


class ValueSchema(BaseModel):
    """Value schema for input parameters and outputs."""

    val_type: Literal["string", "integer", "number", "boolean", "json", "array"]
    """The type of the value."""

    inner_val_type: Literal["string", "integer", "number", "boolean", "json"] | None = None
    """The type of the inner value, if the value is a list."""

    enum: list[str] | None = None
    """The list of possible values for the value, if it is a closed list."""

    properties: dict[str, ValueSchema] | None = None
    """For object types (json), the schema of nested properties."""

    inner_properties: dict[str, ValueSchema] | None = None
    """For array types with json items, the schema of properties for each array item."""

    description: str | None = None
    """Optional description of the value."""


class InputParameter(BaseModel):
    """A parameter that can be passed to a tool."""

    name: str = Field(..., description="The human-readable name of this parameter.")
    required: bool = Field(
        ...,
        description="Whether this parameter is required (true) or optional (false).",
    )
    description: str | None = Field(
        None,
        description="A descriptive, human-readable explanation of the parameter.",
    )
    value_schema: ValueSchema = Field(
        ...,
        description="The schema of the value of this parameter.",
    )
    inferrable: bool = Field(
        True,
        description="Whether a value for this parameter can be inferred by a model. Defaults to `true`.",
    )


class ToolInput(BaseModel):
    """The inputs that a tool accepts."""

    parameters: list[InputParameter]
    """The list of parameters that the tool accepts."""

    tool_context_parameter_name: str | None = Field(default=None, exclude=True)
    """
    The name of the target parameter that will contain the tool context (if any).
    This field will not be included in serialization.
    """


class ToolOutput(BaseModel):
    """The output of a tool."""

    description: str | None = Field(
        None, description="A descriptive, human-readable explanation of the output."
    )
    available_modes: list[str] = Field(
        default_factory=lambda: ["value", "error", "null"],
        description="The available modes for the output.",
    )
    value_schema: ValueSchema | None = Field(
        None, description="The schema of the value of the output."
    )


class OAuth2Requirement(BaseModel):
    """Indicates that the tool requires OAuth 2.0 authorization."""

    scopes: list[str] | None = None
    """The scope(s) needed for the authorized action."""


class ToolAuthRequirement(BaseModel):
    """A requirement for authorization to use a tool."""

    # Provider ID, Type, and ID needed for the Arcade Engine to look up the auth provider.
    # However, the developer generally does not need to set these directly.
    # Instead, they will use:
    #    @tool(requires_auth=Google(scopes=["profile", "email"]))
    # or
    #    client.auth.authorize(provider=AuthProvider.google, scopes=["profile", "email"])
    #
    # The Arcade TDK translates these into the appropriate provider ID (Google) and type (OAuth2).
    # The only time the developer will set these is if they are using a custom auth provider.
    provider_id: str | None = None
    """The provider ID configured in Arcade that acts as an alias to well-known configuration."""

    provider_type: str
    """The type of the authorization provider."""

    id: str | None = None
    """A provider's unique identifier, allowing the tool to specify a specific authorization provider. Recommended for private tools only."""

    oauth2: OAuth2Requirement | None = None
    """The OAuth 2.0 requirement, if any."""


class ToolSecretRequirement(BaseModel):
    """A requirement for a tool to run."""

    key: str
    """The ID of the secret."""


class ToolMetadataKey(str, Enum):
    """Convience enum for commonly used metadata keys."""

    CLIENT_ID = "client_id"
    COORDINATOR_URL = "coordinator_url"

    @staticmethod
    def requires_auth(key: str) -> bool:
        """Whether the key depends on the tool having an authorization requirement."""
        keys_that_require_auth = [ToolMetadataKey.CLIENT_ID]
        return key.strip().lower() in keys_that_require_auth


class ToolMetadataRequirement(BaseModel):
    """A requirement for a tool to run."""

    key: str
    """The ID of the metadata."""


class ToolRequirements(BaseModel):
    """The requirements for a tool to run."""

    authorization: ToolAuthRequirement | None = None
    """The authorization requirements for the tool, if any."""

    secrets: list[ToolSecretRequirement] | None = None
    """The secret requirements for the tool, if any."""

    metadata: list[ToolMetadataRequirement] | None = None
    """The metadata requirements for the tool, if any."""


class ToolkitDefinition(BaseModel):
    """The specification of a toolkit."""

    name: str
    """The name of the toolkit."""

    description: str | None = None
    """The description of the toolkit."""

    version: str | None = None
    """The version identifier of the toolkit."""


@dataclass(frozen=True)
class FullyQualifiedName:
    """The fully-qualified name of a tool."""

    name: str
    """The name of the tool."""

    toolkit_name: str
    """The name of the toolkit containing the tool."""

    toolkit_version: str | None = None
    """The version of the toolkit containing the tool."""

    def __str__(self) -> str:
        return f"{self.toolkit_name}{TOOL_NAME_SEPARATOR}{self.name}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FullyQualifiedName):
            return False
        return (
            self.name.lower() == other.name.lower()
            and self.toolkit_name.lower() == other.toolkit_name.lower()
            and (self.toolkit_version or "").lower() == (other.toolkit_version or "").lower()
        )

    def __hash__(self) -> int:
        return hash((
            self.name.lower(),
            self.toolkit_name.lower(),
            (self.toolkit_version or "").lower(),
        ))

    def equals_ignoring_version(self, other: FullyQualifiedName) -> bool:
        """Check if two fully-qualified tool names are equal, ignoring the version."""
        return (
            self.name.lower() == other.name.lower()
            and self.toolkit_name.lower() == other.toolkit_name.lower()
        )

    @staticmethod
    def from_toolkit(tool_name: str, toolkit: ToolkitDefinition) -> FullyQualifiedName:
        """Creates a fully-qualified tool name from a tool name and a ToolkitDefinition."""
        return FullyQualifiedName(tool_name, toolkit.name, toolkit.version)


class ToolDefinition(BaseModel):
    """The specification of a tool."""

    name: str
    """The name of the tool."""

    fully_qualified_name: str
    """The fully-qualified name of the tool."""

    description: str
    """The description of the tool."""

    toolkit: ToolkitDefinition
    """The toolkit that contains the tool."""

    input: ToolInput
    """The inputs that the tool accepts."""

    output: ToolOutput
    """The output types that the tool can return."""

    requirements: ToolRequirements
    """The requirements (e.g. authorization) for the tool to run."""

    deprecation_message: str | None = None
    """The message to display when the tool is deprecated."""

    def get_fully_qualified_name(self) -> FullyQualifiedName:
        return FullyQualifiedName(self.name, self.toolkit.name, self.toolkit.version)


class ToolReference(BaseModel):
    """The name and version of a tool."""

    name: str
    """The name of the tool."""

    toolkit: str
    """The name of the toolkit containing the tool."""

    version: str | None = None
    """The version of the toolkit containing the tool."""

    def get_fully_qualified_name(self) -> FullyQualifiedName:
        return FullyQualifiedName(self.name, self.toolkit, self.version)


class ToolAuthorizationContext(BaseModel):
    """The context for a tool invocation that requires authorization."""

    token: str | None = None
    """The token for the tool invocation."""

    user_info: dict = Field(default={})
    """
    The user information provided by the authorization server (if any).

    Some providers can provide structured user info,
    for example an internal provider-specific user ID.
    For those providers that support retrieving user info,
    the Engine can automatically pass that to tool invocations.
    """


class ToolSecretItem(BaseModel):
    """The context for a tool secret."""

    key: str
    """The key of the secret."""

    value: str
    """The value of the secret."""


class ToolMetadataItem(BaseModel):
    """The context for a tool metadata."""

    key: str
    """The key of the metadata."""

    value: str
    """The value of the metadata."""


class ToolContext(BaseModel):
    """The context for a tool invocation.

    This type is transport-agnostic and contains only authorization,
    secret, and metadata information needed by the tool. Runtime-specific
    capabilities (logging, resources, etc.) are provided by a separate
    runtime context that wraps this object.

    Recommendation: For new tools, annotate the parameter as
    `arcade_mcp_server.Context` to access namespaced runtime APIs directly.
    """

    authorization: ToolAuthorizationContext | None = None
    """The authorization context for the tool invocation that requires authorization."""

    secrets: list[ToolSecretItem] | None = None
    """The secrets for the tool invocation."""

    metadata: list[ToolMetadataItem] | None = None
    """The metadata for the tool invocation."""

    user_id: str | None = None
    """The user ID for the tool invocation (if any)."""

    model_config = {"arbitrary_types_allowed": True}

    def set_secret(self, key: str, value: str) -> None:
        """Add or update a secret to the tool context."""
        if self.secrets is None:
            self.secrets = []
        # Update existing or add new
        for secret in self.secrets:
            if secret.key == key:
                secret.value = value
                return
        self.secrets.append(ToolSecretItem(key=key, value=value))

    def get_auth_token_or_empty(self) -> str:
        """Retrieve the authorization token, or return an empty string if not available."""
        return self.authorization.token if self.authorization and self.authorization.token else ""

    def get_secret(self, key: str) -> str:
        """Retrieve the secret for the tool invocation.

        Raises a ValueError if the secret is not found.
        """
        return self._get_item(key, self.secrets, "secret")

    def get_metadata(self, key: str) -> str:
        """Retrieve the metadata for the tool invocation.

        Raises a ValueError if the metadata is not found.
        """
        return self._get_item(key, self.metadata, "metadata")

    def _get_item(
        self,
        key: str,
        items: list[ToolMetadataItem] | list[ToolSecretItem] | None,
        item_name: str,
    ) -> str:
        if not key or not key.strip():
            raise ValueError(
                f"{item_name.capitalize()} key passed to get_{item_name} cannot be empty."
            )
        if not items:
            raise ValueError(f"{item_name.capitalize()} '{key}' not found in context.")

        normalized_key = key.lower()
        for item in items:
            if item.key.lower() == normalized_key:
                return item.value

        raise ValueError(f"{item_name.capitalize()} '{key}' not found in context.")

    # ============ MCP Feature Properties ============
    # Non-critical features (no-op in deployed environments)

    @property
    def log(self) -> LogsProtocol:
        """No-op logging interface (not supported in deployed environments)."""
        return _NoOpLogs()

    @property
    def progress(self) -> ProgressProtocol:
        """No-op progress reporting (not supported in deployed environments)."""
        return _NoOpProgress()

    # Critical features (raise error in deployed environments)

    @property
    def resources(self) -> Any:
        """Resources are not available in deployed environments."""
        raise RuntimeError(
            "The resources feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def tools(self) -> Any:
        """Tool calling is not available in deployed environments."""
        raise RuntimeError(
            "The tools feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def prompts(self) -> Any:
        """Prompts are not available in deployed environments."""
        raise RuntimeError(
            "The prompts feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def sampling(self) -> Any:
        """Sampling is not available in deployed environments."""
        raise RuntimeError(
            "The sampling feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def ui(self) -> Any:
        """UI/elicitation is not available in deployed environments."""
        raise RuntimeError("The ui feature is not supported for Arcade managed servers (non-local)")

    @property
    def notifications(self) -> Any:
        """Notifications are not available in deployed environments."""
        raise RuntimeError(
            "The notifications feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def request_id(self) -> Any:
        """Request ID is not available in deployed environments."""
        raise RuntimeError(
            "The request_id feature is not supported for Arcade managed servers (non-local)"
        )

    @property
    def session_id(self) -> Any:
        """Session ID is not available in deployed environments."""
        raise RuntimeError(
            "The session_id feature is not supported for Arcade managed servers (non-local)"
        )


class ToolCallRequest(BaseModel):
    """The request to call (invoke) a tool."""

    run_id: str | None = None
    """The globally-unique run ID provided by the Engine."""
    execution_id: str | None = None
    """The globally-unique ID for this tool execution in the run."""
    created_at: str | None = None
    """The timestamp when the tool invocation was created."""
    tool: ToolReference
    """The fully-qualified name and version of the tool."""
    inputs: dict[str, Any] | None = None
    """The inputs for the tool."""
    context: ToolContext = Field(default_factory=ToolContext)
    """The context for the tool invocation."""


class ToolCallLog(BaseModel):
    """A log that occurred during the tool invocation."""

    message: str
    """The user-facing warning message."""

    level: Literal[
        "debug",
        "info",
        "warning",
        "error",
    ]
    """The level of severity for the log."""

    subtype: Literal["deprecation"] | None = None
    """Optional field for further categorization of the log."""


class ToolCallError(BaseModel):
    """The error that occurred during the tool invocation."""

    message: str
    """The user-facing error message."""
    kind: ErrorKind
    """The error kind that uniquely identifies the kind of error."""
    developer_message: str | None = None
    """The developer-facing error details."""
    can_retry: bool = False
    """Whether the tool call can be retried."""
    additional_prompt_content: str | None = None
    """Additional content to be included in the retry prompt."""
    retry_after_ms: int | None = None
    """The number of milliseconds (if any) to wait before retrying the tool call."""
    stacktrace: str | None = None
    """The stacktrace information for the tool call."""
    status_code: int | None = None
    """The HTTP status code of the error."""
    extra: dict[str, Any] | None = None
    """Additional information about the error."""

    @property
    def is_toolkit_error(self) -> bool:
        """Check if this error originated from loading a toolkit."""
        return self.kind.name.startswith("TOOLKIT_")

    @property
    def is_tool_error(self) -> bool:
        """Check if this error originated from a tool."""
        return self.kind.name.startswith("TOOL_")

    @property
    def is_upstream_error(self) -> bool:
        """Check if this error originated from an upstream service."""
        return self.kind.name.startswith("UPSTREAM_")


class ToolCallRequiresAuthorization(BaseModel):
    """The authorization requirements for the tool invocation."""

    authorization_url: str | None = None
    """The URL to redirect the user to for authorization."""
    authorization_id: str | None = None
    """The ID for checking the status of the authorization."""
    scopes: list[str] | None = None
    """The scopes that are required for authorization."""
    status: str | None = None
    """The status of the authorization."""


class ToolCallOutput(BaseModel):
    """The output of a tool invocation."""

    value: str | int | float | bool | dict | list | None = None
    """The value returned by the tool."""
    logs: list[ToolCallLog] | None = None
    """The logs that occurred during the tool invocation."""
    error: ToolCallError | None = None
    """The error that occurred during the tool invocation."""
    requires_authorization: ToolCallRequiresAuthorization | None = None
    """The authorization requirements for the tool invocation."""

    model_config = {
        "json_schema_extra": {
            "oneOf": [
                {"required": ["value"]},
                {"required": ["error"]},
                {"required": ["requires_authorization"]},
                {"required": ["artifact"]},
            ]
        }
    }


class ToolCallResponse(BaseModel):
    """The response to a tool invocation."""

    execution_id: str
    """The globally-unique ID for this tool execution."""
    finished_at: str
    """The timestamp when the tool execution finished."""
    duration: float
    """The duration of the tool execution in milliseconds (ms)."""
    success: bool
    """Whether the tool execution was successful."""
    output: ToolCallOutput | None = None
    """The output of the tool invocation."""
