"""Tests for the precomputed catalog manifest."""

from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.manifest import (
    MANIFEST_SCHEMA_VERSION,
    CatalogManifest,
    IncompatibleManifestError,
    build_manifest,
    load_manifest,
    write_manifest,
)
from arcade_core.schema import ToolContext
from arcade_core.toolkit import Toolkit
from arcade_tdk import tool


@tool
def echo(text: Annotated[str, "Text to echo"]) -> str:
    """Return the input unchanged."""
    return text


@tool
def add(x: Annotated[int, "First addend"], y: Annotated[int, "Second addend"]) -> int:
    """Add two integers."""
    return x + y


@tool
def with_context(context: ToolContext, text: Annotated[str, "Input"]) -> str:
    """Tool whose first parameter is the tool context."""
    return f"ctx:{text}"


@pytest.fixture
def populated_catalog() -> ToolCatalog:
    toolkit = Toolkit(
        name="manifest_test",
        package_name="manifest_test_package",
        version="0.1.0",
        description="Manifest test toolkit",
    )
    catalog = ToolCatalog()
    catalog.add_tool(echo, toolkit)
    catalog.add_tool(add, toolkit)
    return catalog


def test_build_manifest_records_each_tool(populated_catalog: ToolCatalog) -> None:
    manifest = build_manifest(populated_catalog)

    assert manifest.schema_version == MANIFEST_SCHEMA_VERSION
    assert len(manifest.entries) == 2
    function_names = {e.function_name for e in manifest.entries}
    assert function_names == {"echo", "add"}

    for entry in manifest.entries:
        # toolkit name is normalized to PascalCase in the definition
        assert entry.toolkit_name == "ManifestTest"
        assert entry.toolkit_version == "0.1.0"
        assert entry.module_name == __name__
        # definition.name is PascalCase; function_name is the raw identifier
        assert entry.function_name != entry.definition.name


def test_write_and_load_manifest_roundtrip(
    populated_catalog: ToolCatalog, tmp_path
) -> None:
    out = tmp_path / "catalog.json"
    written = write_manifest(populated_catalog, out)
    assert written == out
    assert out.exists()

    loaded = load_manifest(out)
    assert isinstance(loaded, CatalogManifest)
    assert loaded.schema_version == MANIFEST_SCHEMA_VERSION
    assert len(loaded.entries) == 2

    # Every definition is byte-equivalent after a round-trip.
    original = build_manifest(populated_catalog)
    for orig_entry, loaded_entry in zip(original.entries, loaded.entries, strict=True):
        assert orig_entry.model_dump(mode="json") == loaded_entry.model_dump(mode="json")


def test_build_manifest_rejects_non_catalog() -> None:
    with pytest.raises(TypeError, match="ToolCatalog"):
        build_manifest({"not": "a catalog"})


def test_from_manifest_preserves_definitions(
    populated_catalog: ToolCatalog, tmp_path
) -> None:
    out = tmp_path / "catalog.json"
    write_manifest(populated_catalog, out)

    loaded = ToolCatalog.from_manifest(out)
    assert len(loaded) == len(populated_catalog)

    original_defs = {t.definition.name: t.definition.model_dump(mode="json") for t in populated_catalog}
    loaded_defs = {t.definition.name: t.definition.model_dump(mode="json") for t in loaded}
    assert original_defs == loaded_defs


def test_from_manifest_defers_tool_resolution(
    populated_catalog: ToolCatalog, tmp_path
) -> None:
    out = tmp_path / "catalog.json"
    write_manifest(populated_catalog, out)

    loaded = ToolCatalog.from_manifest(out)
    materialized = next(iter(loaded))

    # Before touching .tool, the callable is unresolved.
    assert not materialized.is_tool_resolved
    # Touching .definition (manifest path) does not force a tool import.
    _ = materialized.definition
    assert not materialized.is_tool_resolved

    # Touching .tool resolves it (from this test module's namespace).
    resolved = materialized.tool
    assert callable(resolved)
    assert materialized.is_tool_resolved


def test_from_manifest_preserves_tool_context_parameter_name(tmp_path) -> None:
    """Round-trip must restore ToolInput.tool_context_parameter_name.

    The field is ``exclude=True`` on ``ToolInput`` so it's dropped from
    the on-wire definition. Without explicit handling in the manifest,
    every manifest-loaded tool with a Context parameter would silently
    fail to receive its context at execution time
    (see arcade_core/executor.py:55-56).
    """
    toolkit = Toolkit(
        name="manifest_ctx_test",
        package_name="manifest_ctx_pkg",
        version="0.1.0",
        description="Context test toolkit",
    )
    catalog = ToolCatalog()
    catalog.add_tool(with_context, toolkit)

    pre = next(iter(catalog))
    assert pre.definition.input.tool_context_parameter_name == "context"

    out = tmp_path / "ctx.json"
    write_manifest(catalog, out)
    loaded = ToolCatalog.from_manifest(out)
    restored = next(iter(loaded))
    assert restored.definition.input.tool_context_parameter_name == "context"


def test_load_manifest_rejects_incompatible_schema_version(
    populated_catalog: ToolCatalog, tmp_path
) -> None:
    out = tmp_path / "stale.json"
    write_manifest(populated_catalog, out)
    # Corrupt the version on disk
    import json as jsonlib

    data = jsonlib.loads(out.read_text())
    data["schema_version"] = "0-prehistoric"
    out.write_text(jsonlib.dumps(data))

    with pytest.raises(IncompatibleManifestError, match="schema_version"):
        load_manifest(out)


def test_from_manifest_respects_disabled_tools(
    populated_catalog: ToolCatalog, tmp_path, monkeypatch
) -> None:
    out = tmp_path / "catalog.json"
    write_manifest(populated_catalog, out)

    # ARCADE_DISABLED_TOOLS is read by ToolCatalog.__init__ via class-var hooks.
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "ManifestTest.Add")

    loaded = ToolCatalog.from_manifest(out)
    names = {t.definition.name for t in loaded}
    assert "Add" not in names
    assert "Echo" in names
