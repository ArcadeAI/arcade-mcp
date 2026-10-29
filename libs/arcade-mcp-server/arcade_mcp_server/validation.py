"""Validation helpers shared by the server and the elicitation flow.

Kept in its own module (rather than ``server.py``) so that ``context.py`` can
import these without creating a circular dependency back to the server.
"""

from __future__ import annotations

import re
from typing import Any

from arcade_core.schema_validation import (
    UnsupportedSchemaDialectError as CoreUnsupportedSchemaDialectError,
)
from arcade_core.schema_validation import (
    validate_schema_dialect,
)

from arcade_mcp_server.exceptions import UnsupportedSchemaDialectError

# Tool name validation pattern: 1-128 chars, only [A-Za-z0-9_.-]
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")


def is_valid_tool_name(name: str) -> bool:
    """Check whether a tool name conforms to the MCP name constraints.

    Rules: 1-128 chars, only ``[A-Za-z0-9_.-]``. This is a MCP SHOULD rule,
    so we return a bool rather than raising.
    """
    if not name:
        return False
    return _TOOL_NAME_RE.fullmatch(name) is not None


def _validate_schema_dialect(schema: dict[str, Any]) -> None:
    try:
        validate_schema_dialect(schema)
    except CoreUnsupportedSchemaDialectError as error:
        raise UnsupportedSchemaDialectError(str(error)) from error
