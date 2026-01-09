"""Tests for datacache plumbing and helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.schema import ToolContext, ToolMetadataItem
from arcade_mcp_server import tool
from arcade_mcp_server.datacache.config import build_datacache_identity, parse_datacache_config
from arcade_mcp_server.datacache.storage import LocalFileDatacacheStorage


def test_datacache_decorator_persists_to_tool_meta():
    @tool(datacache={"keys": ["user_id"], "ttl": 123})
    def my_tool(x: Annotated[str, "x"]) -> Annotated[str, "y"]:
        """My tool."""
        return x

    catalog = ToolCatalog()
    catalog.add_tool(my_tool, "TestToolkit", toolkit_version="1.0.0", toolkit_description="x")

    tools = list(catalog)
    assert len(tools) == 1
    mat = tools[0]
    assert mat.meta.datacache is not None
    assert mat.meta.datacache["keys"] == ["user_id"]
    assert mat.meta.datacache["ttl"] == 123


@pytest.mark.asyncio
async def test_request_meta_propagates_to_tool_context_metadata(mcp_server, materialized_tool):
    session = SimpleNamespace(
        session_id="test-session",
        _request_meta=SimpleNamespace(organization="acme", project="rocket"),
    )
    tool_ctx = await mcp_server._create_tool_context(materialized_tool, session=session)
    assert tool_ctx.metadata is not None
    md = {m.key: m.value for m in tool_ctx.metadata}
    assert md["organization"] == "acme"
    assert md["project"] == "rocket"


def test_datacache_identity_includes_selected_keys():
    cfg = parse_datacache_config({"keys": ["organization", "project", "user_id"], "ttl": 5})
    assert cfg is not None

    tc = ToolContext()
    tc.user_id = "u1"
    tc.metadata = [
        ToolMetadataItem(key="organization", value="org1"),
        ToolMetadataItem(key="project", value="proj1"),
    ]

    ident1 = build_datacache_identity(tool_fqn="TestToolkit.test_tool", cfg=cfg, tool_context=tc)
    assert ident1.digest

    tc2 = ToolContext()
    tc2.user_id = "u1"
    tc2.metadata = [
        ToolMetadataItem(key="organization", value="org1"),
        ToolMetadataItem(key="project", value="proj2"),
    ]
    ident2 = build_datacache_identity(tool_fqn="TestToolkit.test_tool", cfg=cfg, tool_context=tc2)
    assert ident1.digest != ident2.digest


def test_datacache_identity_defaults_missing_org_project():
    cfg = parse_datacache_config({"keys": ["organization", "project", "user_id"], "ttl": 5})
    assert cfg is not None

    tc = ToolContext()
    tc.user_id = "u1"
    tc.metadata = []  # organization/project missing

    ident = build_datacache_identity(tool_fqn="TestToolkit.test_tool", cfg=cfg, tool_context=tc)
    assert ident.key_parts["organization"] == "default"
    assert ident.key_parts["project"] == "default"


def test_datacache_identity_shared_across_tools_in_toolkit():
    cfg = parse_datacache_config({"keys": ["organization", "project", "user_id"], "ttl": 5})
    assert cfg is not None

    tc = ToolContext()
    tc.user_id = "u1"
    tc.metadata = [
        ToolMetadataItem(key="organization", value="org1"),
        ToolMetadataItem(key="project", value="proj1"),
    ]

    ident_a = build_datacache_identity(tool_fqn="TestToolkit.tool_a", cfg=cfg, tool_context=tc)
    ident_b = build_datacache_identity(tool_fqn="TestToolkit.tool_b", cfg=cfg, tool_context=tc)
    assert ident_a.cache_key_slug == ident_b.cache_key_slug
    assert ident_a.toolkit == "TestToolkit"
    assert ident_a.key_parts == {"organization": "org1", "project": "proj1", "user_id": "u1"}
    assert ident_a.cache_key == "toolkit--TestToolkit--org--org1--project--proj1--user--u1"
    assert ident_a.cache_key_slug == "toolkit--TestToolkit--org--org1--project--proj1--user--u1"


@pytest.mark.asyncio
async def test_datacache_client_set_get_search(tmp_path):
    pytest.importorskip("duckdb")

    from arcade_mcp_server.datacache.client import DatacacheClient

    db_path = tmp_path / "cache.duckdb"
    client = await DatacacheClient.open(path=str(db_path), default_ttl=3600)
    try:
        resp1 = await client.set("profiles", {"id": "p1", "name": "Alice"})
        assert resp1.action == "inserted"
        assert resp1.record is not None
        assert resp1.record["id"] == "p1"
        assert resp1.bytes_saved >= 1
        assert resp1.created_at >= 0
        assert resp1.updated_at >= 0

        resp2 = await client.set("profiles", {"id": "p1", "name": "Alice2"})
        assert resp2.action == "updated"
        assert resp2.created_at == resp1.created_at
        assert resp2.updated_at >= resp1.updated_at
        row = await client.get("profiles", "p1")
        assert row is not None
        assert row["id"] == "p1"
        assert row["name"] == "Alice2"

        results = await client.search("profiles", "name", "ali")
        assert len(results) >= 1
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_local_file_storage_roundtrip(tmp_path):
    storage = LocalFileDatacacheStorage(storage_dir=str(tmp_path / "storage"))
    loc = storage.location_for_digest("deadbeef")

    # Create a source file and upload it into the storage location
    src = tmp_path / "src.duckdb"
    src.write_bytes(b"hello")
    await storage.upload(loc, str(src))

    # Download from storage into a new local path
    dst = tmp_path / "dst.duckdb"
    exists = await storage.download_if_exists(loc, str(dst))
    assert exists is True
    assert dst.read_bytes() == b"hello"
