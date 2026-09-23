"""Tests for the startup warning about tool secrets (``_check_and_warn_missing_secrets``).

``TestMissingSecretsWarnings`` in ``test_server.py`` covers when the warning
fires. These tests cover what it says.

The runtime error for a missing secret tells the developer how to fix it; the
startup warning for the same condition used to say only that the secret "is
not set" and "will return an error if called". These tests pin the startup
warning to the same fix instructions.

Reserved framework credentials (``ARCADE_API_KEY``, ``ARCADE_WORKER_SECRET``)
are never exposed to tools, so the runtime reports them as reserved rather than
missing. The startup check used to treat them as ordinary secrets: silent when
the variable was set (the call still fails), and advising the developer to set
it when it was not (which cannot help).
"""

import logging
from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_mcp_server import tool
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings

MISSING_KEY = "STARTUP_WARNING_TEST_MISSING_SECRET"
OTHER_MISSING_KEY = "STARTUP_WARNING_TEST_OTHER_SECRET"


@tool(requires_secrets=[MISSING_KEY])
def needs_missing_secret() -> Annotated[str, "Result"]:
    """Tool that declares a secret nobody set."""
    return "ok"


@tool(requires_secrets=[MISSING_KEY, OTHER_MISSING_KEY])
def needs_two_missing_secrets() -> Annotated[str, "Result"]:
    """Tool that declares two unset secrets."""
    return "ok"


@tool(requires_secrets=["ARCADE_API_KEY"])
def needs_reserved_secret() -> Annotated[str, "Result"]:
    """Tool that declares a reserved framework credential."""
    return "ok"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Worker routes skip the check entirely; make sure they are off.
    monkeypatch.delenv("ARCADE_WORKER_SECRET", raising=False)
    monkeypatch.delenv(MISSING_KEY, raising=False)
    monkeypatch.delenv(OTHER_MISSING_KEY, raising=False)


async def _startup_warnings(caplog, *tools) -> list[str]:
    catalog = ToolCatalog()
    for func in tools:
        catalog.add_tool(func, "StartupToolkit")
    server = MCPServer(
        catalog=catalog,
        name="Startup Warning Server",
        version="0.0.0",
        settings=MCPSettings(),
    )
    with caplog.at_level(logging.WARNING, logger="arcade.mcp"):
        await server.start()
        try:
            return [r.getMessage() for r in caplog.records if r.name == "arcade.mcp"]
        finally:
            await server.stop()


def _only(warnings: list[str], needle: str) -> str:
    matching = [w for w in warnings if needle in w]
    assert len(matching) == 1, f"expected one warning mentioning {needle!r}, got: {warnings!r}"
    return matching[0]


class TestMissingSecretWarning:
    @pytest.mark.asyncio
    async def test_gives_env_file_and_export_fix(self, caplog):
        """The same two fixes the runtime error offers."""
        warning = _only(await _startup_warnings(caplog, needs_missing_secret), MISSING_KEY)
        assert "NeedsMissingSecret" in warning
        assert "To fix" in warning
        assert ".env" in warning
        assert f"{MISSING_KEY}=your_value_here" in warning
        assert f"export {MISSING_KEY}=your_value_here" in warning
        assert "restart the server" in warning

    @pytest.mark.asyncio
    async def test_lists_every_missing_secret(self, caplog):
        warning = _only(await _startup_warnings(caplog, needs_two_missing_secrets), MISSING_KEY)
        assert f"export {MISSING_KEY}=" in warning
        assert f"export {OTHER_MISSING_KEY}=" in warning
        assert "secrets" in warning


class TestReservedSecretWarning:
    @pytest.mark.asyncio
    async def test_reported_even_when_variable_is_set(self, caplog, monkeypatch):
        """The variable being present does not help: tools never receive it."""
        monkeypatch.setenv("ARCADE_API_KEY", "an-api-key")
        warning = _only(await _startup_warnings(caplog, needs_reserved_secret), "ARCADE_API_KEY")
        assert "reserved" in warning.lower()

    @pytest.mark.asyncio
    async def test_advises_removal_not_setting(self, caplog, monkeypatch):
        monkeypatch.delenv("ARCADE_API_KEY", raising=False)
        warning = _only(await _startup_warnings(caplog, needs_reserved_secret), "ARCADE_API_KEY")
        assert "remove" in warning.lower()
        assert "export ARCADE_API_KEY" not in warning
        assert "ARCADE_API_KEY=your_value_here" not in warning

    @pytest.mark.asyncio
    async def test_never_logs_the_reserved_value(self, caplog, monkeypatch):
        monkeypatch.setenv("ARCADE_API_KEY", "SENTINEL_RESERVED_VALUE_DO_NOT_LOG")
        warnings = await _startup_warnings(caplog, needs_reserved_secret)
        assert not [w for w in warnings if "SENTINEL_RESERVED_VALUE_DO_NOT_LOG" in w]
