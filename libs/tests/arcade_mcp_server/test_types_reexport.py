"""``arcade_mcp_server.types`` re-exports the resource models, which live in arcade-core.

arcade-serve needs these shapes and cannot import arcade-mcp-server, because the dependency
runs the other way, so the definitions moved down a layer.

This pins the one failure that move introduces and that nothing else would catch: an edit
that redefines a model here instead of re-exporting it forks the schema, and the two import
paths then serialize differently with every test still passing.
"""

from arcade_core import resource_schema
from arcade_mcp_server import types as mcp_types

MOVED = [
    "Annotations",
    "BaseMetadata",
    "BlobResourceContents",
    "Cursor",
    "Icon",
    "ListResourceTemplatesResult",
    "ListResourcesParams",
    "ListResourcesResult",
    "PaginatedResult",
    "ReadResourceParams",
    "ReadResourceResult",
    "Resource",
    "ResourceContents",
    "ResourceTemplate",
    "Result",
    "Role",
    "TextResourceContents",
]


def test_the_re_exported_models_are_not_copies():
    for name in MOVED:
        assert getattr(mcp_types, name) is getattr(resource_schema, name), name
