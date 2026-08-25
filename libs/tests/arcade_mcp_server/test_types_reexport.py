"""The resource models live in arcade-core; arcade_mcp_server re-exports them.

arcade-serve needs these shapes and cannot import arcade-mcp-server, since the
dependency runs the other way. Anything importing them from the old location
must keep getting the same class object, not a copy.
"""

from arcade_core import resource_schema as core_resources
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


def test_moved_names_are_the_same_objects():
    for name in MOVED:
        assert getattr(mcp_types, name) is getattr(core_resources, name), name


def test_json_rpc_request_envelopes_stayed_behind():
    """The worker protocol carries params and results, never a JSON-RPC envelope."""
    for name in ("ListResourcesRequest", "ListResourceTemplatesRequest", "ReadResourceRequest"):
        assert hasattr(mcp_types, name)
        assert not hasattr(core_resources, name)
