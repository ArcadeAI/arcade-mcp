"""
Datacache support for Arcade MCP Server.

This package provides:
- a per-tool, per-key DuckDB-backed cache
- S3 persistence (download before tool execution, upload after)
- Redis locking to ensure single-flight execution per cache key
"""

from arcade_mcp_server.datacache.client import DatacacheClient
from arcade_mcp_server.datacache.config import (
    DatacacheConfigError,
    DatacacheKeys,
    build_datacache_identity,
    is_datacache_enabled,
)
from arcade_mcp_server.datacache.types import DatacacheSetResult

__all__ = [
    "DatacacheClient",
    "DatacacheConfigError",
    "DatacacheKeys",
    "DatacacheSetResult",
    "build_datacache_identity",
    "is_datacache_enabled",
]
