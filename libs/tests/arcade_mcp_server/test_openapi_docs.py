"""Test that MCP routes appear in OpenAPI documentation."""

from arcade_core import ToolCatalog
from arcade_core.toolkit import Toolkit
from arcade_mcp_server.settings import MCPSettings
from arcade_mcp_server.worker import create_arcade_mcp
from fastapi.testclient import TestClient


def test_mcp_routes_in_openapi(monkeypatch):
    """Test that MCP routes appear in FastAPI OpenAPI documentation."""
    # Set environment variables for settings
    monkeypatch.setenv("ARCADE_AUTH_DISABLED", "true")
    monkeypatch.setenv("ARCADE_WORKER_SECRET", "test")
    monkeypatch.setenv("MCP_SERVER_NAME", "test-mcp")
    monkeypatch.setenv("MCP_SERVER_VERSION", "0.1.0")

    # Create a simple catalog
    catalog = ToolCatalog()
    toolkit = Toolkit(name="test", package_name="test", version="0.1.0", description="Test toolkit")
    catalog.add_toolkit(toolkit)

    # Create MCP settings from environment
    mcp_settings = MCPSettings.from_env()

    # Create the app
    app = create_arcade_mcp(catalog, mcp_settings=mcp_settings)

    # Create test client
    client = TestClient(app)

    # Get OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()

    # Check that MCP paths are documented
    assert "/mcp/" in openapi_schema["paths"]

    mcp_path = openapi_schema["paths"]["/mcp/"]

    # Check POST endpoint
    assert "post" in mcp_path
    assert mcp_path["post"]["summary"] == "Send MCP message"
    assert "MCPRequest" in str(mcp_path["post"])
    assert "MCPResponse" in str(mcp_path["post"])

    # Check GET endpoint
    assert "get" in mcp_path
    assert mcp_path["get"]["summary"] == "Establish SSE stream"

    # Check DELETE endpoint
    assert "delete" in mcp_path
    assert mcp_path["delete"]["summary"] == "Terminate session"

    # Check that component schemas are defined
    components = openapi_schema.get("components", {}).get("schemas", {})
    assert "MCPRequest" in components
    assert "MCPResponse" in components

    # Verify MCPRequest schema
    mcp_request = components["MCPRequest"]
    assert "jsonrpc" in mcp_request["properties"]
    assert "method" in mcp_request["properties"]
    assert "params" in mcp_request["properties"]
    assert "id" in mcp_request["properties"]

    # Verify that the paths include the MCP tag
    assert "tags" in mcp_path["post"]
    assert "MCP Protocol" in mcp_path["post"]["tags"]

    # Verify the actual proxy is mounted (not routes)
    # The OpenAPI docs should exist but not interfere with the mount

    mounts = [route for route in app.routes if hasattr(route, "app") and hasattr(route, "path")]
    mcp_mounts = [m for m in mounts if m.path == "/mcp"]
    assert len(mcp_mounts) == 1, "Should have exactly one mount at /mcp"
