"""MCP content blocks and the conversion of a tool's value into an MCP tool result.

The MCP server and the worker build a tool's result from the same functions, so
both send the same blocks and ``structuredContent`` for the same value.
"""

import base64
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from arcade_core.resource_schema import (
    Annotations,
    BlobResourceContents,
    Resource,
    TextResourceContents,
)


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


def convert_to_mcp_content(value: Any) -> list[MCPContent]:
    """
    Convert a Python value to MCP-compatible content.
    """
    if value is None:
        return []

    if isinstance(value, (str, bool, int, float)):
        return [TextContent(type="text", text=str(value))]

    if isinstance(value, (dict, list)):
        try:
            return [TextContent(type="text", text=json.dumps(value, ensure_ascii=False))]
        except Exception as exc:
            raise ValueError("Failed to serialize value to JSON for MCP content") from exc

    if isinstance(value, (bytes, bytearray, memoryview)):
        # Encode bytes as base64 text so it can be transmitted safely
        b = bytes(value)
        encoded = base64.b64encode(b).decode("ascii")
        return [TextContent(type="text", text=encoded)]

    # Default fallback
    return [TextContent(type="text", text=str(value))]


def convert_content_to_structured_content(value: Any) -> dict[str, Any] | None:
    """
    Convert a Python value to MCP-compatible structured content (JSON object).

    According to the MCP specification, structuredContent should be a JSON object
    that represents the structured result of the tool call.

    Args:
        value: The value to convert to structured content

    Returns:
        A dictionary representing the structured content, or None if value is None
    """
    if value is None:
        return None

    if isinstance(value, dict):
        # Already a dictionary - use as-is
        return value
    elif isinstance(value, list):
        # List - wrap in a result object
        return {"result": value}
    elif isinstance(value, (str, int, float, bool)):
        # Primitive types - wrap in a result object
        return {"result": value}
    else:
        # For other types, convert to string and wrap
        return {"result": str(value)}
