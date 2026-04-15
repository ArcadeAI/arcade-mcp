def test_basic_imports():
    """Test basic imports from arcade_mcp_server."""
    from arcade_mcp_server.context import Context
    from arcade_mcp_server.server import MCPServer

    # All imports should work
    assert MCPServer is not None
    assert Context is not None


def test_v2025_11_25_type_imports():
    """Test that all 2025-11-25 types are importable from the top-level package."""
    from arcade_mcp_server import (
        CancelTaskResult,
        CreateTaskResult,
        ElicitationCompleteNotification,
        ElicitRequestURLParams,
        GetTaskResult,
        Icon,
        LegacyTitledEnumSchema,
        ListTasksResult,
        Task,
        TaskStatus,
        TaskStatusNotification,
        TitledMultiSelectEnumSchema,
        TitledSingleSelectEnumSchema,
        ToolChoice,
        ToolExecution,
        ToolResultContent,
        ToolUseContent,
        URLElicitationRequiredError,
        UntitledMultiSelectEnumSchema,
        UntitledSingleSelectEnumSchema,
    )

    assert Icon is not None
    assert ToolUseContent is not None
    assert ToolResultContent is not None
    assert ToolChoice is not None
    assert ToolExecution is not None
    assert TaskStatus is not None
    assert Task is not None
    assert CreateTaskResult is not None
    assert GetTaskResult is not None
    assert CancelTaskResult is not None
    assert ListTasksResult is not None
    assert TaskStatusNotification is not None
    assert ElicitRequestURLParams is not None
    assert ElicitationCompleteNotification is not None
    assert URLElicitationRequiredError is not None
    assert UntitledSingleSelectEnumSchema is not None
    assert TitledSingleSelectEnumSchema is not None
    assert UntitledMultiSelectEnumSchema is not None
    assert TitledMultiSelectEnumSchema is not None
    assert LegacyTitledEnumSchema is not None


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
    test_v2025_11_25_type_imports()
    test_manager_imports()
    test_middleware_imports()
    test_transport_imports()
    print("All imports successful!")
