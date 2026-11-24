from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class ToolResult(Generic[T]):
    """A tool's value plus MCP content blocks, such as an image, sent to the model with it.

    Annotate the tool's return as ``ToolResult[T]``. ``value`` is the tool's result and sets
    its output schema. MCP clients get the ``content`` blocks first, then ``value`` as a JSON
    text block and as ``structuredContent``.
    """

    value: T
    content: list[Any] = field(default_factory=list)
    """MCP content blocks: plain dicts or Pydantic models such as ``ImageContent``."""
