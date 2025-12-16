"""Converters for transforming tool definitions between formats."""

from .anthropic import (
    AnthropicInputSchema,
    AnthropicInputSchemaProperty,
    AnthropicToolList,
    AnthropicToolSchema,
    to_anthropic,
)
from .openai import (
    OpenAIFunctionParameterProperty,
    OpenAIFunctionParameters,
    OpenAIFunctionSchema,
    OpenAIToolList,
    OpenAIToolSchema,
    to_openai,
)

__all__ = [
    # Anthropic
    "AnthropicInputSchema",
    "AnthropicInputSchemaProperty",
    "AnthropicToolList",
    "AnthropicToolSchema",
    "to_anthropic",
    # OpenAI
    "OpenAIFunctionParameterProperty",
    "OpenAIFunctionParameters",
    "OpenAIFunctionSchema",
    "OpenAIToolList",
    "OpenAIToolSchema",
    "to_openai",
]
