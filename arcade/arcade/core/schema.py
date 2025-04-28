import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

# allow for custom tool name separator
TOOL_NAME_SEPARATOR = os.getenv("ARCADE_TOOL_NAME_SEPARATOR", ".")


class ValueSchema(BaseModel):
    """Value schema for input parameters and outputs."""

    val_type: Literal["string", "integer", "number", "boolean", "json", "array"]
    """The type of the value."""

    inner_val_type: Optional[Literal["string", "integer", "number", "boolean", "json"]] = None
    """The type of the inner value, if the value is a list."""

    enum: Optional[list[str]] = None
    """The list of possible values for the value, if it is a closed list."""


class InputParameter(BaseModel):
    """A parameter that can be passed to a tool."""

    name: str = Field(..., description="The human-readable name of this parameter.")
    required: bool = Field(
        ...,
        description="Whether this parameter is required (true) or optional (false).",
    )
    description: Optional[str] = Field(
        None, description="A descriptive, human-readable explanation of the parameter."
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

    description: Optional[str] = Field(
        None, description="A descriptive, human-readable explanation of the output."
    )
    available_modes: list[str] = Field(
        default_factory=lambda: ["value", "error", "null"],
        description="The available modes for the output.",
    )
    value_schema: Optional[ValueSchema] = Field(
        None, description="The schema of the value of the output."
    )


class OAuth2Requirement(BaseModel):
    """Indicates that the tool requires OAuth 2.0 authorization."""

    scopes: Optional[list[str]] = None
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
    # The Arcade SDK translates these into the appropriate provider ID (Google) and type (OAuth2).
    # The only time the developer will set these is if they are using a custom auth provider.
    provider_id: Optional[str] = None
    """The provider ID configured in Arcade that acts as an alias to well-known configuration."""

    provider_type: str
    """The type of the authorization provider."""

    id: Optional[str] = None
    """A provider's unique identifier, allowing the tool to specify a specific authorization provider. Recommended for private tools only."""

    oauth2: Optional[OAuth2Requirement] = None
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

    authorization: Union[ToolAuthRequirement, None] = None
    """The authorization requirements for the tool, if any."""

    secrets: Union[list[ToolSecretRequirement], None] = None
    """The secret requirements for the tool, if any."""

    metadata: Union[list[ToolMetadataRequirement], None] = None
    """The metadata requirements for the tool, if any."""


class ToolkitDefinition(BaseModel):
    """The specification of a toolkit."""

    name: str
    """The name of the toolkit."""

    description: Optional[str] = None
    """The description of the toolkit."""

    version: Optional[str] = None
    """The version identifier of the toolkit."""


@dataclass(frozen=True)
class FullyQualifiedName:
    """The fully-qualified name of a tool."""

    name: str
    """The name of the tool."""

    toolkit_name: str
    """The name of the toolkit containing the tool."""

    toolkit_version: Optional[str] = None
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

    def equals_ignoring_version(self, other: "FullyQualifiedName") -> bool:
        """Check if two fully-qualified tool names are equal, ignoring the version."""
        return (
            self.name.lower() == other.name.lower()
            and self.toolkit_name.lower() == other.toolkit_name.lower()
        )

    @staticmethod
    def from_toolkit(tool_name: str, toolkit: ToolkitDefinition) -> "FullyQualifiedName":
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

    deprecation_message: Optional[str] = None
    """The message to display when the tool is deprecated."""

    def get_fully_qualified_name(self) -> FullyQualifiedName:
        return FullyQualifiedName(self.name, self.toolkit.name, self.toolkit.version)


class ToolReference(BaseModel):
    """The name and version of a tool."""

    name: str
    """The name of the tool."""

    toolkit: str
    """The name of the toolkit containing the tool."""

    version: Optional[str] = None
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
    """The context for a tool invocation."""

    authorization: ToolAuthorizationContext | None = None
    """The authorization context for the tool invocation that requires authorization."""

    secrets: list[ToolSecretItem] | None = None
    """The secrets for the tool invocation."""

    metadata: list[ToolMetadataItem] | None = None
    """The metadata for the tool invocation."""

    user_id: str | None = None
    """The user ID for the tool invocation (if any)."""

    def get_auth_token_or_empty(self) -> str:
        """Retrieve the authorization token, or return an empty string if not available."""
        return self.authorization.token if self.authorization and self.authorization.token else ""

    def get_secret(self, key: str) -> str:
        """Retrieve the secret for the tool invocation."""
        return self._get_item(key, self.secrets, "secret")

    def get_metadata(self, key: str) -> str:
        """Retrieve the metadata for the tool invocation."""
        return self._get_item(key, self.metadata, "metadata")

    def _get_item(
        self, key: str, items: list[ToolMetadataItem] | list[ToolSecretItem] | None, item_name: str
    ) -> str:
        if not key or not key.strip():
            raise ValueError(
                f"{item_name.capitalize()} key passed to get_{item_name} cannot be empty."
            )
        if not items:
            raise ValueError(f"{item_name.capitalize()}s not found in context.")

        normalized_key = key.lower()
        for item in items:
            if item.key.lower() == normalized_key:
                return item.value

        raise ValueError(f"{item_name.capitalize()} {key} not found in context.")

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret for the tool invocation."""
        if not self.secrets:
            self.secrets = []
        secret = ToolSecretItem(key=str(key), value=str(value))
        self.secrets.append(secret)


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

    subtype: Optional[Literal["deprecation"]] = None
    """Optional field for further categorization of the log."""


class ToolCallError(BaseModel):
    """The error that occurred during the tool invocation."""

    message: str
    """The user-facing error message."""
    developer_message: str | None = None
    """The developer-facing error details."""
    can_retry: bool = False
    """Whether the tool call can be retried."""
    additional_prompt_content: str | None = None
    """Additional content to be included in the retry prompt."""
    retry_after_ms: int | None = None
    """The number of milliseconds (if any) to wait before retrying the tool call."""
    traceback_info: str | None = None
    """The traceback information for the tool call."""


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

    value: Union[str, int, float, bool, dict, list[str]] | None = None
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
