"""Type definitions for JSON tool schemas used by OpenAI APIs.
This module defines the proper types for tool schemas to ensure
compatibility with OpenAI's Responses and Chat Completions APIs.
"""

from typing import Any, Literal, TypedDict


class OpenAIFunctionParameterProperty(TypedDict, total=False):
    """Type definition for a property within OpenAI function parameters schema."""

    type: str | list[str]
    """The JSON Schema type(s) for this property. Can be a single type or list for unions (e.g., ["string", "null"])."""

    description: str
    """Description of the property."""

    enum: list[Any]
    """Allowed values for enum properties."""

    items: dict[str, Any]
    """Schema for array items when type is 'array'."""

    properties: dict[str, "OpenAIFunctionParameterProperty"]
    """Nested properties when type is 'object'."""

    required: list[str]
    """Required fields for nested objects."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class OpenAIFunctionParameters(TypedDict, total=False):
    """Type definition for OpenAI function parameters schema."""

    type: Literal["object"]
    """Must be 'object' for function parameters."""

    properties: dict[str, OpenAIFunctionParameterProperty]
    """The properties of the function parameters."""

    required: list[str]
    """List of required parameter names. In strict mode, all properties should be listed here."""

    additionalProperties: Literal[False]
    """Must be False for strict mode compliance."""


class OpenAIFunctionSchema(TypedDict, total=False):
    """Type definition for a function tool parameter matching OpenAI's API."""

    name: str
    """The name of the function to call."""

    parameters: OpenAIFunctionParameters | None
    """A JSON schema object describing the parameters of the function."""

    strict: Literal[True]
    """Always enforce strict parameter validation. Default `true`."""

    description: str | None
    """A description of the function.
    Used by the model to determine whether or not to call the function.
    """


class OpenAIToolSchema(TypedDict):
    """
    Schema for a tool definition passed to OpenAI's `tools` parameter.
    A tool wraps a callable function for function-calling. Each tool
    includes a type (always 'function') and a `function` payload that
    specifies the callable via `OpenAIFunctionSchema`.
    """

    type: Literal["function"]
    """The type field, always 'function'."""

    function: OpenAIFunctionSchema
    """The function definition."""


# Type alias for a list of openai tool schemas
OpenAIToolList = list[OpenAIToolSchema]
