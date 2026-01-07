"""Unit tests for MCP tool loaders (no network / no external processes)."""

import sys
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
        assert "MCP SDK is required" in str(exc.value)
        assert "pip install" in str(exc.value)


def test_ensure_mcp_path_appends() -> None:
    assert loaders._ensure_mcp_path("http://localhost:8000") == "http://localhost:8000/mcp"
    assert loaders._ensure_mcp_path("http://localhost:8000/") == "http://localhost:8000/mcp"
    assert (
        loaders._ensure_mcp_path("http://localhost:8000?x=1")
        == "http://localhost:8000/mcp?x=1"
    )


def test_ensure_mcp_path_does_not_duplicate() -> None:
    assert loaders._ensure_mcp_path("http://localhost:8000/mcp") == "http://localhost:8000/mcp"
    assert (
        loaders._ensure_mcp_path("http://localhost:8000/mcp/?x=1")
        == "http://localhost:8000/mcp?x=1"
    )


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


def test_arcade_api_base_url_constant() -> None:
    """Verify the default Arcade API base URL is set correctly."""
    assert loaders.ARCADE_API_BASE_URL == "https://api.arcade.dev"
