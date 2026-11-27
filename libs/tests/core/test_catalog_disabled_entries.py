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


@tool
def delete_document() -> str:
    """Delete a document."""
    return "deleted"


@tool
def send_email() -> str:
    """Send an email."""
    return "sent"


@pytest.fixture(autouse=True)
def _fresh_malformed_warnings(monkeypatch):
    """Malformed entries warn once per process; give each test its own process view."""
    monkeypatch.setattr(catalog_module, "_warned_malformed_entries", set())


def _build_catalog(toolkit_name: str = "Admin") -> ToolCatalog:
    catalog = ToolCatalog()
    for func in ADMIN_TOOL_FUNCS:
        catalog.add_tool(func, toolkit_name)
    return catalog


def _cataloged(catalog: ToolCatalog) -> set[str]:
    return {str(name) for name in catalog.get_tool_names()}


def _messages(caplog: pytest.LogCaptureFixture, level: int) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno == level and record.name == "arcade_core.catalog"
    ]


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return _messages(caplog, logging.WARNING)


def _infos(caplog: pytest.LogCaptureFixture) -> list[str]:
    return _messages(caplog, logging.INFO)


@pytest.mark.parametrize(
    ("env_var", "value", "disabled"),
    [
        # Controls: these worked before and must keep working.
        ("ARCADE_DISABLED_TOOLS", "Admin.DeleteAll", {"Admin.DeleteAll"}),
        ("ARCADE_DISABLED_TOOLS", "admin.deleteall", {"Admin.DeleteAll"}),
        ("ARCADE_DISABLED_TOOLKITS", "Admin", ALL_ADMIN_TOOLS),
        ("ARCADE_DISABLED_TOOLKITS", "admin", ALL_ADMIN_TOOLS),
        ("ARCADE_DISABLED_TOOLKITS", "ADMIN", ALL_ADMIN_TOOLS),
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


@pytest.mark.parametrize(
    "value",
    [
        "AdminTools",
        "admin_tools",
        "ADMIN_TOOLS",
        # Package spellings of the same toolkit.
        "arcade_admin_tools",
        "arcade-admin-tools",
        "admin-tools",
    ],
)
def test_toolkit_entry_matches_every_spelling_of_the_toolkit(monkeypatch, value):
    """An app named admin_tools is cataloged as AdminTools; each spelling disables it."""
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", value)

    assert _cataloged(_build_catalog("admin_tools")) == set()


@pytest.mark.parametrize("value", ["arcade_ops", "arcade-ops", "ops", "Arcade-Ops"])
def test_toolkit_entry_matches_a_dashed_package_name(monkeypatch, value):
    """A toolkit loaded from the package arcade-ops keeps that name; ops names it too."""
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", value)

    assert _cataloged(_build_catalog("arcade-ops")) == set()


def test_toolkit_entry_does_not_match_a_different_toolkit(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "admin")

    catalog = _build_catalog("admin_tools")

    assert _cataloged(catalog) == {
        "AdminTools.DeleteAll",
        "AdminTools.ExportV2",
        "AdminTools.ResetPasswords",
    }


@pytest.mark.parametrize(
    "value",
    [
        "AdminTools.DeleteAll",
        "admin_tools.DeleteAll",
        "arcade-admin-tools.DeleteAll",
        "AdminTools_DeleteAll",
        "admin_tools::DeleteAll",
    ],
)
def test_tool_entry_toolkit_part_matches_every_spelling(monkeypatch, value):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", value)

    catalog = _build_catalog("admin_tools")

    assert _cataloged(catalog) == {"AdminTools.ExportV2", "AdminTools.ResetPasswords"}


@pytest.mark.parametrize(
    "toolkit_name",
    [
        "arcade-ops",  # a package named arcade-ops keeps that name
        "arcade_ops",  # cataloged as ArcadeOps, so only the given name carries "ops"
    ],
)
def test_tool_entry_toolkit_part_matches_a_package_spelling(monkeypatch, toolkit_name):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "ops.DeleteAll")

    catalog = _build_catalog(toolkit_name)

    assert {str(name).split(".", 1)[1] for name in catalog.get_tool_names()} == {
        "ExportV2",
        "ResetPasswords",
    }


def test_tool_entry_with_raw_toolkit_name_is_applied_beside_a_disabled_toolkit(monkeypatch):
    """ARCADE_DISABLED_TOOLKITS=admin must not stop admin_tools.DeleteAll from applying."""
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "admin")
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "admin_tools.DeleteAll")

    catalog = _build_catalog("admin")
    for func in ADMIN_TOOL_FUNCS:
        catalog.add_tool(func, "admin_tools")

    assert _cataloged(catalog) == {"AdminTools.ExportV2", "AdminTools.ResetPasswords"}


def test_tool_entry_with_snake_toolkit_is_applied_beside_a_prefix_toolkit(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Google")
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "google_docs.DeleteDocument")

    catalog = ToolCatalog()
    catalog.add_tool(delete_document, "Google")
    catalog.add_tool(delete_document, "google_docs")

    assert _cataloged(catalog) == set()


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

    def test_malformed_entry_is_still_applied_and_the_warning_says_so(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "my kit")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog = _build_catalog("MyKit")

        assert _cataloged(catalog) == set()
        assert "still applied" in _warnings(caplog)[0]

    def test_malformed_entry_warns_once_per_process(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            ToolCatalog()
            ToolCatalog()

        assert len(_warnings(caplog)) == 1

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

        with caplog.at_level(logging.INFO, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "ARCADE_DISABLED_TOOLS" in warnings[0]
        assert "'admin.deletealll'" in warnings[0]
        assert any("'billing'" in message for message in _infos(caplog))

    def test_only_a_typo_in_a_loaded_toolkit_warns(self, monkeypatch, caplog):
        """Servers that share one environment each load only some toolkits; entries for the
        others are expected and must not warn."""
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "GitHub.ListIssues,Gmail.SendEmaill")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Slack")
        catalog = ToolCatalog()
        catalog.add_tool(send_email, "Gmail")

        with caplog.at_level(logging.INFO, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "'gmail.sendemaill'" in warnings[0]
        infos = _infos(caplog)
        assert any("'github.listissues'" in message for message in infos), infos
        assert any("'slack'" in message for message in infos), infos

    def test_typo_beside_a_disabled_prefix_toolkit_warns(self, monkeypatch, caplog):
        """A disabled Google toolkit does not cover an entry for google_docs."""
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Google")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "google_docs.DeleteDocumentt")
        catalog = ToolCatalog()
        catalog.add_toolkit(
            Toolkit(
                name="google",
                package_name="google",
                version="1.0.0",
                description="Google",
                tools={__name__: ["delete_document"]},
            )
        )
        catalog.add_tool(delete_document, "google_docs")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "'google_docs.deletedocumentt'" in warnings[0]

    def test_entry_covered_by_only_one_of_its_readings_warns(self, monkeypatch, caplog):
        """Admin_Tools_DeleteAlll reads as Admin + Tools_DeleteAlll and as Admin_Tools +
        DeleteAlll. A disabled Admin covers only the first, so the typo still warns."""
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Admin")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin_Tools_DeleteAlll")
        catalog = ToolCatalog()
        catalog.add_tool(delete_all, "Admin")
        catalog.add_tool(delete_all, "admin_tools")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        assert _cataloged(catalog) == {"AdminTools.DeleteAll"}
        warnings = _warnings(caplog)
        assert len(warnings) == 1, warnings
        assert "'admin_tools_deletealll'" in warnings[0]

    def test_malformed_reading_does_not_uncover_an_entry(self, monkeypatch, caplog):
        """Admin.Delete_Alll also reads as Admin.Delete + Alll, which is not a tool name. Only
        well-formed readings decide coverage, so a disabled Admin covers the entry."""
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Admin")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin.Delete_Alll")
        catalog = ToolCatalog()
        catalog.add_tool(delete_all, "Admin")

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        assert _warnings(caplog) == []

    def test_tool_and_toolkit_entry_for_the_same_tool_report_nothing(self, monkeypatch, caplog):
        monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "Admin.DeleteAll")
        monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "Admin")
        catalog = ToolCatalog()
        catalog.add_tool(delete_all, "Admin")

        with caplog.at_level(logging.INFO, logger="arcade_core.catalog"):
            catalog.warn_unmatched_disabled_entries()

        assert _cataloged(catalog) == set()
        assert _warnings(caplog) == []
        assert not [m for m in _infos(caplog) if "does not match" in m]

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
