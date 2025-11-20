"""Tests for automatic MCP tool loaders."""

import pytest
from arcade_evals import MCPToolRegistry
from arcade_evals.loaders import load_from_http, load_from_stdio

# ============================================================================
# load_from_stdio tests
# ============================================================================


def test_load_from_stdio_github_mcp():
    """Test loading tools from GitHub MCP server."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    assert len(tools) > 0, "Should load at least one tool"
    assert all("name" in tool for tool in tools), "All tools should have name"
    assert all("inputSchema" in tool for tool in tools), "All tools should have inputSchema"

    # Check for known GitHub tools
    tool_names = [t["name"] for t in tools]
    assert "list_issues" in tool_names, "Should have list_issues tool"
    assert "get_issue" in tool_names, "Should have get_issue tool"


def test_load_from_stdio_invalid_command():
    """Test that invalid command handles gracefully."""
    result = load_from_stdio(["nonexistent-command-xyz-123"])
    assert result == [], "Invalid command should return empty list"


def test_load_from_stdio_empty_command():
    """Test that empty command list handles gracefully."""
    # Empty command will cause Popen to fail, should return empty list
    result = load_from_stdio([])
    assert result == [], "Empty command should return empty list"


def test_load_from_stdio_custom_timeout():
    """Test load_from_stdio with custom timeout."""
    # Short timeout should still work for fast servers
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"], timeout=30)
    assert isinstance(tools, list), "Should return a list"


# ============================================================================
# Tool format validation tests
# ============================================================================


def test_loaded_tools_are_valid_mcp_format():
    """Test that loaded tools match MCP format."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        tool = tools[0]
        assert isinstance(tool, dict), "Tool should be a dictionary"
        assert "name" in tool, "Tool should have name field"
        assert isinstance(tool["name"], str), "Tool name should be a string"

        if "inputSchema" in tool:
            schema = tool["inputSchema"]
            assert isinstance(schema, dict), "inputSchema should be a dict"
            assert schema.get("type") == "object", "inputSchema type should be object"


def test_loaded_tools_have_descriptions():
    """Test that loaded tools have descriptions."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        # Most tools should have descriptions
        tools_with_desc = [t for t in tools if t.get("description")]
        assert len(tools_with_desc) > 0, "At least some tools should have descriptions"


def test_loaded_tools_have_properties():
    """Test that tool schemas have properties."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        # Find a tool with parameters
        tool_with_params = next(
            (t for t in tools if t.get("inputSchema", {}).get("properties")), None
        )
        assert tool_with_params is not None, "Should have at least one tool with parameters"

        properties = tool_with_params["inputSchema"]["properties"]
        assert isinstance(properties, dict), "Properties should be a dict"
        assert len(properties) > 0, "Should have at least one property"


# ============================================================================
# Integration tests with MCPToolRegistry
# ============================================================================


def test_loaded_tools_work_with_registry():
    """Test that loaded tools integrate with MCPToolRegistry."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        registry = MCPToolRegistry(tools)

        assert len(registry._tools) == len(tools), "Registry should have all tools"

        # Test tool name resolution
        first_tool_name = tools[0]["name"]
        resolved = registry.resolve_tool_name(first_tool_name)
        assert resolved == first_tool_name, "Should resolve to same name"

        # Test OpenAI format conversion
        openai_tools = registry.list_tools_for_model("openai")
        assert len(openai_tools) == len(tools), "Should convert all tools"

        # Verify strict mode is enabled
        assert all(t["function"].get("strict") for t in openai_tools), (
            "All tools should have strict mode enabled"
        )


def test_loaded_tools_have_valid_schemas_for_openai():
    """Test that loaded tools convert to valid OpenAI schemas."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        registry = MCPToolRegistry(tools)
        openai_tools = registry.list_tools_for_model("openai")

        for tool in openai_tools:
            # Check structure
            assert "type" in tool, "Tool should have type"
            assert tool["type"] == "function", "Type should be 'function'"

            func = tool["function"]
            assert "name" in func, "Function should have name"
            assert "parameters" in func, "Function should have parameters"
            assert "strict" in func, "Function should have strict field"

            params = func["parameters"]
            assert not params.get("additionalProperties"), "Should have additionalProperties=false"


# ============================================================================
# load_from_http tests
# ============================================================================


def test_load_from_http_requires_httpx():
    """Test that load_from_http raises error when httpx not available."""
    # Check if httpx is available
    import importlib.util

    if importlib.util.find_spec("httpx") is not None:
        pytest.skip("httpx is installed, can't test missing dependency")
    else:
        # httpx not available, should raise ImportError
        with pytest.raises(ImportError, match="httpx is required"):
            load_from_http("http://localhost:8000")


def test_load_from_http_handles_connection_error():
    """Test that load_from_http handles connection errors gracefully."""
    import importlib.util

    if importlib.util.find_spec("httpx") is None:
        pytest.skip("httpx not installed")

    # Try connecting to non-existent server (should return empty list)
    result = load_from_http("http://localhost:99999", timeout=1)
    assert result == [], "Connection error should return empty list"


def test_load_from_http_handles_invalid_url():
    """Test that load_from_http handles invalid URLs."""
    import importlib.util

    if importlib.util.find_spec("httpx") is None:
        pytest.skip("httpx not installed")

    result = load_from_http("not-a-valid-url", timeout=1)
    assert result == [], "Invalid URL should return empty list"


# ============================================================================
# Edge cases and error scenarios
# ============================================================================


def test_load_from_stdio_with_no_tools():
    """Test handling of MCP server that returns no tools."""
    # Most MCP servers will have tools, but handle edge case
    # This is difficult to test without a mock server, so we'll skip
    pytest.skip("Requires mock MCP server that returns no tools")


def test_multiple_concurrent_loads():
    """Test that multiple simultaneous loads don't interfere."""
    import concurrent.futures

    def load_tools():
        return load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    # Load from multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(load_tools) for _ in range(3)]
        results = [f.result() for f in futures]

    # All should succeed
    assert all(len(r) > 0 for r in results), "All loads should succeed"
    # All should get same number of tools
    assert len({len(r) for r in results}) == 1, "All loads should get same tools"


def test_load_preserves_tool_metadata():
    """Test that loading preserves all tool metadata fields."""
    tools = load_from_stdio(["npx", "-y", "@modelcontextprotocol/server-github"])

    if tools:
        tool = tools[0]

        # Check common metadata fields are preserved
        if "description" in tool:
            assert isinstance(tool["description"], str), "Description should be string"

        if "inputSchema" in tool:
            schema = tool["inputSchema"]
            if "properties" in schema:
                assert isinstance(schema["properties"], dict), "Properties should be dict"
            if "required" in schema:
                assert isinstance(schema["required"], list), "Required should be list"
