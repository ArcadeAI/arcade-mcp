"""Unit tests for MCP tool loaders (no network / no external processes)."""

import sys
from typing import Literal
from unittest.mock import AsyncMock, patch

import arcade_evals.loaders as loaders
import pytest


def test_module_imports_without_mcp_installed() -> None:
    """Importing the module must not require the optional MCP SDK."""
    # If this import fails, the whole optional-dependency design breaks.
    import arcade_evals.loaders  # noqa: F401


def test_require_mcp_raises_helpful_error_when_missing() -> None:
    """Calling _require_mcp should raise a helpful ImportError if MCP isn't available."""
    with patch.dict(sys.modules, {"mcp": None}):
        with pytest.raises(ImportError) as exc:
            loaders._require_mcp()
        assert "MCP SDK not installed" in str(exc.value)
        assert "pip install" in str(exc.value)


def test_ensure_mcp_path_appends() -> None:
    assert loaders._ensure_mcp_path("http://localhost:8000") == "http://localhost:8000/mcp"
    assert loaders._ensure_mcp_path("http://localhost:8000/") == "http://localhost:8000/mcp"


def test_ensure_mcp_path_does_not_duplicate() -> None:
    assert loaders._ensure_mcp_path("http://localhost:8000/mcp") == "http://localhost:8000/mcp"


@pytest.mark.asyncio
async def test_stdio_arcade_sets_env_and_calls_stdio_loader() -> None:
    """load_stdio_arcade_async should map auth into env vars and call load_from_stdio_async."""
    with patch.object(loaders, "load_from_stdio_async", new_callable=AsyncMock) as mock_stdio:
        mock_stdio.return_value = []

        await loaders.load_stdio_arcade_async(
            ["python", "server.py"],
            arcade_api_key="k",
            arcade_user_id="u",
            tool_secrets={"S": "1"},
        )

        _, kwargs = mock_stdio.call_args
        assert kwargs["env"]["ARCADE_API_KEY"] == "k"
        assert kwargs["env"]["ARCADE_USER_ID"] == "u"
        assert kwargs["env"]["S"] == "1"


@pytest.mark.asyncio
async def test_backend_switching_can_route_to_internal_loader() -> None:
    """We can swap the wired loader implementation (official remains default)."""
    original: Literal["official", "internal"] = loaders.get_mcp_loader_backend()
    try:
        loaders.set_mcp_loader_backend("internal")
        assert loaders.get_mcp_loader_backend() == "internal"

        # Avoid requiring httpx/subprocess behavior by patching the internal helper.
        with patch.object(loaders, "_internal_load_from_http_sync") as mock_internal_http:
            mock_internal_http.return_value = [{"name": "t", "description": "", "inputSchema": {}}]
            result = await loaders.load_from_http_async("http://localhost:8000")
            assert result and result[0]["name"] == "t"
    finally:
        loaders.set_mcp_loader_backend(original)
