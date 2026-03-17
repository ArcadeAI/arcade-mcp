"""Tests for ToolCatalog.resolve_cross_tool_requirements — deferred secret/scope merging."""

import pytest

from arcade_core.catalog import ToolCatalog
from arcade_core.schema import ToolContext


@pytest.fixture
def catalog() -> ToolCatalog:
    return ToolCatalog()


def _make_tool(
    name: str,
    requires_secrets: list[str] | None = None,
    requires_secrets_from: list[str] | None = None,
    request_scopes_from: list[str] | None = None,
) -> callable:
    """Create a minimal decorated tool function."""
    from arcade_tdk import tool
    from arcade_tdk.auth import Google

    auth = None
    if request_scopes_from:
        # The compound tool itself may or may not have auth; we test both cases
        pass

    @tool(
        name=name,
        requires_secrets=requires_secrets,
        requires_secrets_from=requires_secrets_from,
        request_scopes_from=request_scopes_from,
    )
    def tool_func(context: ToolContext) -> str:
        """A test tool."""
        return "ok"

    return tool_func


def _make_authed_tool(name: str, scopes: list[str]) -> callable:
    """Create a tool with OAuth2 auth requirement."""
    from arcade_tdk import tool
    from arcade_tdk.auth import Google

    @tool(name=name, requires_auth=Google(scopes=scopes))
    def tool_func(context: ToolContext) -> str:
        """A test tool with auth."""
        return "ok"

    return tool_func


class TestResolveSecrets:
    def test_merges_secrets_from_referenced_tool(self, catalog: ToolCatalog) -> None:
        provider = _make_tool("Provider", requires_secrets=["API_KEY", "DB_PASS"])
        compound = _make_tool(
            "Compound",
            requires_secrets=["OWN_SECRET"],
            requires_secrets_from=["TestToolkit.Provider"],
        )

        catalog.add_tool(provider, "TestToolkit")
        catalog.add_tool(compound, "TestToolkit")
        catalog.resolve_cross_tool_requirements()

        compound_def = catalog.get_tool_by_name("TestToolkit.Compound").definition
        secret_keys = {s.key for s in compound_def.requirements.secrets or []}
        assert secret_keys == {"OWN_SECRET", "API_KEY", "DB_PASS"}

    def test_no_duplicate_secrets(self, catalog: ToolCatalog) -> None:
        provider = _make_tool("Provider", requires_secrets=["API_KEY"])
        compound = _make_tool(
            "Compound",
            requires_secrets=["API_KEY"],  # Already has this secret
            requires_secrets_from=["TestToolkit.Provider"],
        )

        catalog.add_tool(provider, "TestToolkit")
        catalog.add_tool(compound, "TestToolkit")
        catalog.resolve_cross_tool_requirements()

        compound_def = catalog.get_tool_by_name("TestToolkit.Compound").definition
        secret_keys = [s.key for s in compound_def.requirements.secrets or []]
        assert secret_keys.count("API_KEY") == 1

    def test_missing_reference_warns(self, catalog: ToolCatalog, caplog: pytest.LogCaptureFixture) -> None:
        compound = _make_tool(
            "Compound",
            requires_secrets_from=["NonExistent.Tool"],
        )
        catalog.add_tool(compound, "TestToolkit")

        import logging
        with caplog.at_level(logging.WARNING):
            catalog.resolve_cross_tool_requirements()

        assert "not found" in caplog.text


class TestResolveScopes:
    def test_merges_scopes_from_referenced_tool(self, catalog: ToolCatalog) -> None:
        provider = _make_authed_tool("Provider", scopes=["email", "profile"])
        compound = _make_tool(
            "Compound",
            request_scopes_from=["TestToolkit.Provider"],
        )

        catalog.add_tool(provider, "TestToolkit")
        catalog.add_tool(compound, "TestToolkit")
        catalog.resolve_cross_tool_requirements()

        compound_def = catalog.get_tool_by_name("TestToolkit.Compound").definition
        assert compound_def.requirements.authorization is not None
        assert compound_def.requirements.authorization.oauth2 is not None
        scopes = set(compound_def.requirements.authorization.oauth2.scopes or [])
        assert scopes == {"email", "profile"}

    def test_merges_scopes_into_existing_auth(self, catalog: ToolCatalog) -> None:
        provider = _make_authed_tool("Provider", scopes=["email"])

        from arcade_tdk import tool
        from arcade_tdk.auth import Google

        @tool(
            name="Compound",
            requires_auth=Google(scopes=["calendar"]),
            request_scopes_from=["TestToolkit.Provider"],
        )
        def compound_func(context: ToolContext) -> str:
            """Compound tool with its own auth."""
            return "ok"

        catalog.add_tool(provider, "TestToolkit")
        catalog.add_tool(compound_func, "TestToolkit")
        catalog.resolve_cross_tool_requirements()

        compound_def = catalog.get_tool_by_name("TestToolkit.Compound").definition
        scopes = set(compound_def.requirements.authorization.oauth2.scopes or [])
        assert "calendar" in scopes
        assert "email" in scopes


class TestNoReferences:
    def test_tools_without_references_unchanged(self, catalog: ToolCatalog) -> None:
        plain = _make_tool("Plain", requires_secrets=["KEY"])
        catalog.add_tool(plain, "TestToolkit")
        catalog.resolve_cross_tool_requirements()

        defn = catalog.get_tool_by_name("TestToolkit.Plain").definition
        secret_keys = {s.key for s in defn.requirements.secrets or []}
        assert secret_keys == {"KEY"}
