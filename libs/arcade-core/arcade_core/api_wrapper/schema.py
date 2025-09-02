from typing import Literal

from pydantic import BaseModel, Field

from arcade_core.schema import InputParameter, ToolDefinition, ToolInput


class ObjectMetadata(BaseModel):
    """Object metadata (part of the serialized JSON stored in a Wrapper toolkit package)."""

    object_type: str
    """The type of the object."""

    version: str
    """The version of the object."""

    description: str = ""
    """The description of the object."""


class HttpValueSchema(BaseModel):
    """The schema of the value of an HTTP API endpoint parameter."""

    val_type: Literal["string", "integer", "number", "boolean", "json", "array"]
    """The type of the value."""

    inner_val_type: Literal["string", "integer", "number", "boolean"] | None = None
    """The value schema of the inner value, in case of an array."""


class HttpEndpointParameter(BaseModel):
    """The value of an HTTP API endpoint parameter."""

    name: str
    """The name of the parameter."""

    description: str = ""
    """The description of the parameter."""

    value_schema: HttpValueSchema
    """The schema of the value."""

    accepted_as: Literal["path", "query", "header", "body", "form_data"]
    """How the parameter is accepted by the HTTP API endpoint."""

    required: bool
    """Whether the parameter is required."""

    deprecated: bool = False
    """Whether the parameter is deprecated."""

    # NOTE: sometimes API documentation points to additional URL(s) explaining about the options
    # accepted by the parameter, or how to build a json value, for example.
    documentation_urls: list[str] = []
    """The URLs to the documentation for the parameter."""


class HttpEndpointMetadata(ObjectMetadata):
    object_type: Literal["http_endpoint"] = "http_endpoint"


class HttpEndpointDefinition(BaseModel):
    """The definition of an HTTP API endpoint."""

    metadata: HttpEndpointMetadata = Field(
        default_factory=HttpEndpointMetadata, exclude=True
    )
    """The object metadata."""

    url: str
    """The URL of the HTTP API endpoint."""

    http_method: Literal["GET", "POST", "PUT", "DELETE"]
    """The HTTP method of the HTTP API endpoint."""

    headers: dict[str, str] | None = None
    """The headers of the HTTP API endpoint."""

    parameters: list[HttpEndpointParameter]
    """The parameters of the HTTP API endpoint."""

    # Utility to facilitate converting tool inputs to HTTP endpoint parameters
    # when building the HTTP request.
    parameters_by_name: dict[str, HttpEndpointParameter] = Field(
        exclude=True,
        default_factory=dict,
        init=False,
    )

    documentation_urls: list[str] = []
    """The URLs to the documentation for the HTTP API endpoint."""

    def model_post_init(self, __context) -> None:
        """Initialize computed fields after model creation."""
        self.parameters_by_name = {param.name: param for param in self.parameters}


class WrapperToolInputParameter(InputParameter):
    """A parameter that can be passed to an API wrapper tool."""

    # This field is used only during tool-call runtime and is excluded from serialization.
    http_endpoint_parameter_name: str = Field(..., exclude=True)
    """The name of the HTTP endpoint parameter associated to this Wrapper Tool parameter."""


class WrapperToolInput(ToolInput):
    """The inputs of an Wrapper tool."""

    parameters: list[WrapperToolInputParameter]
    """The list of parameters that the tool accepts."""


class WrapperToolMetadata(ObjectMetadata):
    object_type: Literal["api_wrapper_tool"] = "api_wrapper_tool"


class WrapperToolDefinition(ToolDefinition):
    """The specification of a Wrapper Tool."""

    metadata: WrapperToolMetadata = Field(
        default_factory=WrapperToolMetadata, exclude=True
    )
    """The object metadata."""

    input: WrapperToolInput
    """The inputs of the Wrapper Tool."""

    http_endpoint: HttpEndpointDefinition = Field(..., exclude=True)
    """The HTTP API endpoint that the Wrapper Tool wraps."""
