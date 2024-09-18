from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, Field


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


class ToolInputs(BaseModel):
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

    authority: Optional[AnyUrl] = None
    """The URL of the OAuth 2.0 authorization server."""

    scopes: Optional[list[str]] = None
    """The scope(s) needed for authorization, if any."""


class ToolAuthRequirement(BaseModel):
    """A requirement for authorization to use a tool."""

    provider: str
    """The provider type."""

    oauth2: Optional[OAuth2Requirement] = None
    """The OAuth 2.0 requirement, if any."""


class ToolRequirements(BaseModel):
    """The requirements for a tool to run."""

    authorization: Union[ToolAuthRequirement, None] = None
    """The authorization requirements for the tool, if any."""


class ToolDefinition(BaseModel):
    """The specification of a tool."""

    name: str
    description: str
    version: str
    inputs: ToolInputs
    output: ToolOutput
    requirements: ToolRequirements


class ToolVersion(BaseModel):
    """The name and version of a tool."""

    name: str
    """The name of the tool."""

    version: str
    """The version of the tool."""


class ToolAuthorizationContext(BaseModel):
    """The context for a tool invocation that requires authorization."""

    token: str | None = None
    """The token for the tool invocation."""


class ToolContext(BaseModel):
    """The context for a tool invocation."""

    authorization: ToolAuthorizationContext | None = None
    """The authorization context for the tool invocation that requires authorization."""


class ToolCallRequest(BaseModel):
    """The request to call (invoke) a tool."""

    run_id: str | None = None
    """The globally-unique run ID provided by the Engine."""
    invocation_id: str | None = None
    """The globally-unique ID for this tool invocation in the run."""
    created_at: str | None = None
    """The timestamp when the tool invocation was created."""
    tool: ToolVersion
    """The name and version of the tool."""
    inputs: dict[str, Any] | None = None
    """The inputs for the tool."""
    context: ToolContext = Field(default_factory=ToolContext)
    """The context for the tool invocation."""


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

    invocation_id: str
    """The globally-unique ID for this tool invocation."""
    finished_at: str
    """The timestamp when the tool invocation finished."""
    duration: float
    """The duration of the tool invocation in milliseconds (ms)."""
    success: bool
    """Whether the tool invocation was successful."""
    output: ToolCallOutput | None = None
    """The output of the tool invocation."""
