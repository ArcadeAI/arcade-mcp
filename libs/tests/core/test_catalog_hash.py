"""Tests for ToolCatalog.compute_hash used in worker tool sync."""

from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_tdk import tool


@tool
def tool_alpha(x: Annotated[str, "input"]) -> str:
    """Tool Alpha"""
    return x


@tool
def tool_beta(y: Annotated[int, "number"]) -> int:
    """Tool Beta"""
    return y


@tool
def tool_gamma(z: Annotated[str, "data"]) -> str:
    """Tool Gamma"""
    return z


class TestComputeHash:
    """Tests for ToolCatalog.compute_hash()."""

    def test_determinism_same_insertion_order(self):
        """Same tools inserted in the same order produce the same hash."""
        catalog1 = ToolCatalog()
        catalog1.add_tool(tool_alpha, "TestKit")
        catalog1.add_tool(tool_beta, "TestKit")

        catalog2 = ToolCatalog()
        catalog2.add_tool(tool_alpha, "TestKit")
        catalog2.add_tool(tool_beta, "TestKit")

        assert catalog1.compute_hash() == catalog2.compute_hash()

    def test_determinism_different_insertion_order(self):
        """Same tools inserted in different order produce the same hash."""
        catalog1 = ToolCatalog()
        catalog1.add_tool(tool_alpha, "TestKit")
        catalog1.add_tool(tool_beta, "TestKit")

        catalog2 = ToolCatalog()
        catalog2.add_tool(tool_beta, "TestKit")
        catalog2.add_tool(tool_alpha, "TestKit")

        assert catalog1.compute_hash() == catalog2.compute_hash()

    def test_stability_multiple_calls(self):
        """Calling compute_hash() multiple times returns the same value."""
        catalog = ToolCatalog()
        catalog.add_tool(tool_alpha, "TestKit")

        hash1 = catalog.compute_hash()
        hash2 = catalog.compute_hash()
        hash3 = catalog.compute_hash()

        assert hash1 == hash2 == hash3

    def test_sensitivity_add_tool(self):
        """Adding a tool changes the hash."""
        catalog = ToolCatalog()
        catalog.add_tool(tool_alpha, "TestKit")
        hash_before = catalog.compute_hash()

        catalog.add_tool(tool_beta, "TestKit")
        hash_after = catalog.compute_hash()

        assert hash_before != hash_after

    def test_sensitivity_different_tools(self):
        """Different tools produce different hashes."""
        catalog1 = ToolCatalog()
        catalog1.add_tool(tool_alpha, "TestKit")

        catalog2 = ToolCatalog()
        catalog2.add_tool(tool_beta, "TestKit")

        assert catalog1.compute_hash() != catalog2.compute_hash()

    def test_empty_catalog(self):
        """Empty catalog produces a valid hash (not an error)."""
        catalog = ToolCatalog()
        result = catalog.compute_hash()

        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest length

    def test_hash_is_valid_hex_string(self):
        """Hash is a valid hex string of correct length."""
        catalog = ToolCatalog()
        catalog.add_tool(tool_alpha, "TestKit")

        result = catalog.compute_hash()
        assert isinstance(result, str)
        assert len(result) == 64
        int(result, 16)  # Should not raise

    def test_different_toolkit_names_produce_different_hashes(self):
        """Same tool in different toolkits produces different hashes."""
        catalog1 = ToolCatalog()
        catalog1.add_tool(tool_alpha, "ToolkitA")

        catalog2 = ToolCatalog()
        catalog2.add_tool(tool_alpha, "ToolkitB")

        assert catalog1.compute_hash() != catalog2.compute_hash()
