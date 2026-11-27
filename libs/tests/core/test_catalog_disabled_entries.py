"""ARCADE_DISABLED_TOOLS / ARCADE_DISABLED_TOOLKITS parsing and matching.

Every test builds a real ToolCatalog with the environment variable set, because
the catalog reads both variables when it is constructed.
"""

import logging

import pytest
from arcade_core import catalog as catalog_module
from arcade_core import schema as schema_module
from arcade_core.catalog import ToolCatalog
from arcade_core.toolkit import Toolkit
from arcade_tdk import tool

ALL_ADMIN_TOOLS = {"Admin.DeleteAll", "Admin.ExportV2", "Admin.ResetPasswords"}


@tool
def delete_all() -> str:
    """Delete every record."""
    return "deleted"


@tool
def export_v2() -> str:
    """Export all data."""
    return "exported"


@tool
def reset_passwords() -> str:
    """Reset all passwords."""
    return "reset"


ADMIN_TOOL_FUNCS = (delete_all, export_v2, reset_passwords)


def _build_catalog(toolkit_name: str = "Admin") -> ToolCatalog:
    catalog = ToolCatalog()
    for func in ADMIN_TOOL_FUNCS:
        catalog.add_tool(func, toolkit_name)
    return catalog


def _cataloged(catalog: ToolCatalog) -> set[str]:
    return {str(name) for name in catalog.get_tool_names()}


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING and record.name == "arcade_core.catalog"
    ]


@pytest.mark.parametrize(
    ("env_var", "value", "disabled"),
    [
        # Controls: these worked before and must keep working.
        ("ARCADE_DISABLED_TOOLS", "Admin.DeleteAll", {"Admin.DeleteAll"}),
        ("ARCADE_DISABLED_TOOLS", "admin.deleteall", {"Admin.DeleteAll"}),
        ("ARCADE_DISABLED_TOOLKITS", "Admin", ALL_ADMIN_TOOLS),
        ("ARCADE_DISABLED_TOOLKITS", "admin", ALL_ADMIN_TOOLS),
        # A digit in the tool name.
        ("ARCADE_DISABLED_TOOLS", "Admin.ExportV2", {"Admin.ExportV2"}),
        # Whitespace after the comma.
        (
            "ARCADE_DISABLED_TOOLS",
            "Admin.DeleteAll, Admin.ResetPasswords",
            {"Admin.DeleteAll", "Admin.ResetPasswords"},
        ),
        ("ARCADE_DISABLED_TOOLS", "  Admin.ExportV2  ,", {"Admin.ExportV2"}),
        # The Toolkit::Tool format CLAUDE.md used to document.
        ("ARCADE_DISABLED_TOOLS", "Admin::DeleteAll", {"Admin.DeleteAll"}),
        # The name MCP clients show for the tool (the separator becomes "_").
        ("ARCADE_DISABLED_TOOLS", "Admin_ExportV2", {"Admin.ExportV2"}),
        # Whitespace after the comma in the toolkit list.
        ("ARCADE_DISABLED_TOOLKITS", "Billing, Admin", ALL_ADMIN_TOOLS),
    ],
)
def test_disabled_entry_removes_tool(monkeypatch, env_var, value, disabled):
    monkeypatch.setenv(env_var, value)

    catalog = _build_catalog()

    assert _cataloged(catalog) == ALL_ADMIN_TOOLS - disabled


def test_toolkit_entry_matches_the_name_the_catalog_shows(monkeypatch):
    """An app named admin_tools is cataloged as AdminTools; both names disable it."""
    for value in ("AdminTools", "admin_tools"):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", value)
        catalog = _build_catalog("admin_tools")
        assert _cataloged(catalog) == set(), value


@pytest.mark.parametrize(
    ("value", "remaining"),
    [
        # Control: the configured separator worked before.
        ("Admin_DeleteAll", {"Admin_ExportV2", "Admin_ResetPasswords"}),
        ("Admin_DeleteAll, Admin.ExportV2", {"Admin_ResetPasswords"}),
    ],
)
def test_tool_entry_matches_with_custom_separator(monkeypatch, value, remaining):
    """ARCADE_TOOL_NAME_SEPARATOR changes the fully-qualified name; "." still works."""
    monkeypatch.setattr(schema_module, "TOOL_NAME_SEPARATOR", "_")
    monkeypatch.setattr(catalog_module, "TOOL_NAME_SEPARATOR", "_")
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", value)

    catalog = _build_catalog()

    assert _cataloged(catalog) == remaining


@pytest.mark.parametrize("value", ["", "   ", ",", " , ,"])
def test_empty_values_disable_nothing_and_do_not_warn(monkeypatch, caplog, value):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", value)
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", value)

    with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
        catalog = _build_catalog()
        catalog.warn_unmatched_disabled_entries()

    assert catalog._disabled_tools.entries == set()
    assert catalog._disabled_toolkits.entries == set()
    assert _cataloged(catalog) == ALL_ADMIN_TOOLS
    assert _warnings(caplog) == []


def test_add_toolkit_skips_a_disabled_toolkit_before_loading_it(monkeypatch):
    """A disabled toolkit is not imported, so a module it cannot import does not fail loading."""
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Broken")
    toolkit = Toolkit(
        name="broken",
        package_name="broken",
        version="1.0.0",
        description="A toolkit whose module cannot be imported",
        tools={"arcade_core_tests_module_that_does_not_exist": ["missing_tool"]},
    )

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert _cataloged(catalog) == set()


def test_add_toolkit_matches_the_toolkit_name(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "AdminTools")
    toolkit = Toolkit(
        name="arcade_admin_tools",
        package_name="arcade_admin_tools",
        version="1.0.0",
        description="Admin tools",
        tools={__name__: [func.__name__ for func in ADMIN_TOOL_FUNCS]},
    )

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert _cataloged(catalog) == set()


class TestMalformedEntriesWarn:
    @pytest.mark.parametrize(
        "value",
        [
            "Admin",  # a toolkit name in the tools variable
            "Admin:DeleteAll",
            "Admin.DeleteAll@1.0.0",
            "Admin.",
            ".DeleteAll",
        ],
    )
    def test_malformed_tool_entry_warns(self, monkeypatch, caplog, value):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", value)

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            ToolCatalog()

        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "ARCADE_DISABLED_TOOLS" in warnings[0]
        assert repr(value) in warnings[0]

    def test_toolkit_name_in_tools_variable_points_at_toolkits_variable(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            ToolCatalog()

        assert "ARCADE_DISABLED_TOOLKITS" in _warnings(caplog)[0]

    @pytest.mark.parametrize("value", ["Admin.DeleteAll", "Admin DeleteAll", "Admin/Tools"])
    def test_malformed_toolkit_entry_warns(self, monkeypatch, caplog, value):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", value)

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            ToolCatalog()

        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "ARCADE_DISABLED_TOOLKITS" in warnings[0]
        assert repr(value) in warnings[0]

    def test_well_formed_entries_do_not_warn_while_loading(self, monkeypatch, caplog):
        monkeypatch.setenv(
            "ARCADE_DISABLED_TOOLS",
            "Admin.DeleteAll, Admin::ExportV2, Admin_ResetPasswords, Admin2.Tool3",
        )
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Billing, admin_tools, Admin-Tools")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            ToolCatalog()

        assert _warnings(caplog) == []


class TestUnmatchedEntriesWarn:
    def test_entries_that_match_nothing_warn(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin.DeleteAll, Admin.DeleteAlll")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Billing")
        catalog = _build_catalog()

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        warnings = _warnings(caplog)
        assert len(warnings) == 2, warnings
        assert any("ARCADE_DISABLED_TOOLS" in w and "'admin.deletealll'" in w for w in warnings)
        assert any("ARCADE_DISABLED_TOOLKITS" in w and "'billing'" in w for w in warnings)

    def test_matched_entries_do_not_warn(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin.DeleteAll, Admin_ExportV2")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Other")
        catalog = _build_catalog()
        for func in ADMIN_TOOL_FUNCS:
            catalog.add_tool(func, "Other")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        assert _warnings(caplog) == []

    def test_tool_entry_in_a_disabled_toolkit_does_not_warn(self, monkeypatch, caplog):
        """add_toolkit skips a disabled toolkit without reading its tools, so the tool entry is
        covered by the toolkit entry rather than unmatched."""
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "AdminTools.DeleteAll")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "admin_tools")
        toolkit = Toolkit(
            name="admin_tools",
            package_name="admin_tools",
            version="1.0.0",
            description="Admin tools",
            tools={__name__: [func.__name__ for func in ADMIN_TOOL_FUNCS]},
        )
        catalog = ToolCatalog()
        catalog.add_toolkit(toolkit)

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        assert _cataloged(catalog) == set()
        assert _warnings(caplog) == []

    def test_malformed_entry_warns_only_once(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog = _build_catalog()
            catalog.warn_unmatched_disabled_entries()

        assert len(_warnings(caplog)) == 1
