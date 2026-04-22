"""Validation helpers shared by the server and the elicitation flow.

Kept in its own module (rather than ``server.py``) so that ``context.py`` can
import these without creating a circular dependency back to the server.
"""

from __future__ import annotations

import re
from typing import Any

from arcade_mcp_server.exceptions import UnsupportedSchemaDialectError

# Tool name validation pattern: 1-128 chars, only [A-Za-z0-9_.-]
_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,128}$")

# Accepted JSON Schema 2020-12 dialect URIs
_ACCEPTED_SCHEMA_DIALECTS: set[str] = {
    "https://json-schema.org/draft/2020-12/schema",
    "https://json-schema.org/draft/2020-12/schema#",
    "http://json-schema.org/draft/2020-12/schema",
    "http://json-schema.org/draft/2020-12/schema#",
    "https://json-schema.org/2025-11-25/2020-12/schema",
}


def is_valid_tool_name(name: str) -> bool:
    """Check whether a tool name conforms to the MCP name constraints.

    Rules: 1-128 chars, only ``[A-Za-z0-9_.-]``. This is a MCP SHOULD rule,
    so we return a bool rather than raising.
    """
    if not name:
        return False
    return _TOOL_NAME_RE.fullmatch(name) is not None


def _validate_schema_dialect(schema: dict[str, Any]) -> None:
    """Validate that a JSON Schema uses a supported dialect (2020-12).

    If ``$schema`` is absent, the schema is treated as 2020-12 (valid).
    If ``$schema`` is present and matches a recognized 2020-12 URI, it is
    valid. Otherwise, raises :class:`UnsupportedSchemaDialectError`.
    """
    dollar_schema = schema.get("$schema")
    if dollar_schema is None:
        return  # No $schema -> default to 2020-12 (valid)
    if dollar_schema in _ACCEPTED_SCHEMA_DIALECTS:
        return
    raise UnsupportedSchemaDialectError(
        f"Unsupported JSON Schema dialect: {dollar_schema}. "
        "Only JSON Schema 2020-12 is supported."
    )
