from abc import ABC
from typing import Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, Field


class ValueSchema(BaseModel):
    """Value schema for input parameters and outputs."""

    val_type: Literal["string", "integer", "float", "boolean", "json"]
    """The type of the value."""

    enum: Optional[list[str]] = None


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


class ToolAuthorizationRequirement(BaseModel, ABC):
    """A requirement for authorization to use a tool."""

    pass


class OAuth2AuthorizationRequirement(ToolAuthorizationRequirement):
    """Specifies OAuth2 requirement for tool execution."""

    url: AnyUrl
    """The URL to which the user should be redirected to authorize the tool."""

    scope: Optional[list[str]] = None
    """The scope of the authorization."""


class ToolRequirements(BaseModel):
    """The requirements for a tool to run."""

    authorization: Union[ToolAuthorizationRequirement, None] = None


class ToolDefinition(BaseModel):
    """The specification of a tool."""

    name: str
    description: str
    version: str
    inputs: ToolInputs
    output: ToolOutput
    requirements: ToolRequirements
