def test_basic_imports():
    """Test basic imports from arcade_mcp_server."""
    from arcade_mcp_server.context import Context
    from arcade_mcp_server.server import MCPServer

    # All imports should work
    assert MCPServer is not None
    assert Context is not None


def test_manager_imports():
    """Test manager imports."""
    from arcade_mcp_server.managers.prompt import PromptManager
    from arcade_mcp_server.managers.resource import ResourceManager
    from arcade_mcp_server.managers.tool import ToolManager

    assert ToolManager is not None
    assert ResourceManager is not None
    assert PromptManager is not None


def test_middleware_imports():
    """Test middleware imports."""
    from arcade_mcp_server.middleware.base import Middleware
    from arcade_mcp_server.middleware.error_handling import ErrorHandlingMiddleware
    from arcade_mcp_server.middleware.logging import LoggingMiddleware

    assert Middleware is not None
    assert ErrorHandlingMiddleware is not None
    assert LoggingMiddleware is not None


def test_transport_imports():
    """Test transport imports."""
    from arcade_mcp_server.transports.http_session_manager import HTTPSessionManager
    from arcade_mcp_server.transports.http_streamable import HTTPStreamableTransport
    from arcade_mcp_server.transports.stdio import StdioTransport

    assert StdioTransport is not None
    assert HTTPStreamableTransport is not None
    assert HTTPSessionManager is not None


if __name__ == "__main__":
    test_basic_imports()
    test_manager_imports()
    test_middleware_imports()
    test_transport_imports()
    print("All imports successful!")
