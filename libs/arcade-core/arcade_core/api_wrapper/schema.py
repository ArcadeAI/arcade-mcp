from typing import Any, Literal

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field, field_validator

from arcade_core.api_wrapper.errors import InvalidObjectVersionError
from arcade_core.schema import InputParameter, ToolDefinition, ToolInput


class ObjectMetadata(BaseModel):
    """Object metadata (part of the serialized JSON stored in a Wrapper toolkit package)."""

    object_type: Literal["http_endpoint", "api_wrapper_tool"]
    """The type of the object."""

    version: str
    """The version of the object."""

    description: str = ""
    """The description of the object."""

    @field_validator("version")
    @classmethod
    def validate_semver(cls, version: str) -> str:
        """Validate that object version follows semantic versioning format."""
        try:
            Version(version)
            return version
        except InvalidVersion as e:
            raise InvalidObjectVersionError(version, cls.__name__) from e


class HttpValueSchema(BaseModel):
    """The schema of the value of an HTTP API endpoint parameter."""

    val_type: Literal["string", "integer", "number", "boolean", "json", "array"]
    """The type of the value."""

    array_inner_val_type: Literal["string", "integer", "number", "boolean"] | None = (
        None
    )
    """The value schema of the inner value of an array (if applicable)."""


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

    documentation_urls: list[str] = []
    """The URLs to the documentation for the HTTP API endpoint."""

    def model_dump_full(
        self, mode: Literal["json", "python"] = "json"
    ) -> dict[str, Any]:
        return {
            "metadata": self.metadata.model_dump(mode=mode),
            **self.model_dump(mode=mode),
        }


class WrapperToolInputParameter(InputParameter):
    """A parameter that can be passed to an API wrapper tool."""

    # This field is used only during tool-call runtime and is excluded from serialization.
    http_endpoint_parameter_name: str = Field(..., exclude=True)
    """The name of the HTTP endpoint parameter associated to this Wrapper Tool parameter."""

    def model_dump_full(
        self, mode: Literal["json", "python"] = "json"
    ) -> dict[str, Any]:
        return {
            **self.model_dump(mode=mode),
            "http_endpoint_parameter_name": self.http_endpoint_parameter_name,
        }


class WrapperToolInput(ToolInput):
    """The inputs of an Wrapper tool."""

    parameters: list[WrapperToolInputParameter]
    """The list of parameters that the tool accepts."""

    def model_dump_full(
        self, mode: Literal["json", "python"] = "json"
    ) -> dict[str, Any]:
        return {
            **self.model_dump(mode=mode),
            "parameters": [
                param.model_dump_full(mode=mode) for param in self.parameters
            ],
        }


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

    @property
    def qualified_name(self) -> str:
        return self.fully_qualified_name.split("@")[0]

    def model_dump_full(
        self, mode: Literal["json", "python"] = "json"
    ) -> dict[str, Any]:
        data = {
            "metadata": self.metadata.model_dump(mode=mode),
            **self.model_dump(mode=mode),
        }
        data["input"] = self.input.model_dump_full(mode=mode)
        data["http_endpoint"] = self.http_endpoint.model_dump_full(mode=mode)
        return data
