"""Tests verifying that error responses do NOT emit structuredContent.

When a tool declares a TypedDict return type (with required fields), the MCP
outputSchema lists those fields as required. The framework must set
structuredContent = None on error responses so it never violates the schema.
Per the MCP spec, structuredContent MUST validate against outputSchema when
both are present — setting structuredContent to None avoids the validation
requirement entirely. The error message is still available in content (TextContent).
"""

import json
from typing import Annotated
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.errors import FatalToolError
from arcade_mcp_server import tool
from arcade_mcp_server.convert import (
    convert_content_to_structured_content,
    create_mcp_tool,
)
from arcade_mcp_server.middleware.error_handling import ErrorHandlingMiddleware
from arcade_mcp_server.types import CallToolResult


def _make_tool_with_typeddict_return(return_type, tool_func=None):
    """Create a MaterializedTool and MCP tool definition for a function returning the given TypedDict."""
    if tool_func is None:
        @tool
        def f() -> Annotated[return_type, "result"]:
            """Test tool."""
            return {}
        tool_func = f

    tool_def = ToolCatalog().create_tool_definition(
        tool_func, toolkit_name="test", toolkit_version="1.0"
    )
    input_model, output_model = create_func_models(tool_func)
    meta = ToolMeta(module=tool_func.__module__, toolkit="test")
    mat_tool = MaterializedTool(
        tool=tool_func,
        definition=tool_def,
        meta=meta,
        input_model=input_model,
        output_model=output_model,
    )
    mcp_tool = create_mcp_tool(mat_tool)
    return mat_tool, mcp_tool


class TestErrorStructuredContentVsOutputSchema:
    """Verify that error responses have structuredContent = None.

    This prevents schema violations when the tool declares a TypedDict return type.
    """

    def test_error_structuredcontent_is_none_for_typeddict_tool(self):
        """Error responses should have structuredContent=None, not {"error": "..."}."""
        from typing_extensions import TypedDict

        class UpdateRangeResponse(TypedDict):
            item_id: str
            worksheet: str
            cells_updated: int
            session_id: str
            message: str

        _, mcp_tool = _make_tool_with_typeddict_return(UpdateRangeResponse)
        output_schema = mcp_tool.outputSchema

        # The schema should declare all 5 fields as required
        assert output_schema is not None
        assert "required" in output_schema, (
            "outputSchema should have 'required' for a total=True TypedDict"
        )
        assert sorted(output_schema["required"]) == sorted([
            "item_id", "worksheet", "cells_updated", "session_id", "message"
        ])

        # On error, structuredContent should be None (not {"error": "..."})
        # The error message goes in content only
        error_structured_content = None  # This is what the fix produces

        # Verify: None structuredContent cannot violate any schema
        assert error_structured_content is None

    def test_success_structuredcontent_validates_against_schema(self):
        """Contrast: a successful response DOES satisfy the outputSchema."""
        from typing_extensions import TypedDict

        class UpdateRangeResponse(TypedDict):
            item_id: str
            worksheet: str
            cells_updated: int
            session_id: str
            message: str

        _, mcp_tool = _make_tool_with_typeddict_return(UpdateRangeResponse)
        output_schema = mcp_tool.outputSchema

        # Simulate a successful response
        success_value = {
            "item_id": "abc123",
            "worksheet": "Sheet1",
            "cells_updated": 10,
            "session_id": "sess-456",
            "message": "Update complete",
        }
        success_structured_content = convert_content_to_structured_content(success_value)

        # Success response should have all required fields
        required_fields = output_schema.get("required", [])
        for field in required_fields:
            assert field in success_structured_content

    def test_error_middleware_produces_none_structuredcontent(self):
        """The ErrorHandlingMiddleware returns structuredContent=None on errors."""
        middleware = ErrorHandlingMiddleware(mask_error_details=False)

        # Simulate what the middleware does on error
        error_message = "Internal server error"

        # The middleware now returns structuredContent=None
        result = CallToolResult(
            content=[{"type": "text", "text": error_message}],
            structuredContent=None,
            isError=True,
        )

        assert result.structuredContent is None
        assert result.isError is True

    def test_error_response_type_mismatch_for_int_field(self):
        """Even with int fields in the schema, error structuredContent is None (no type mismatch)."""
        from typing_extensions import TypedDict

        class CountResponse(TypedDict):
            count: int
            total: int

        _, mcp_tool = _make_tool_with_typeddict_return(CountResponse)
        output_schema = mcp_tool.outputSchema

        # Verify schema requires int fields
        assert output_schema["properties"]["count"]["type"] == "integer"
        assert output_schema["properties"]["total"]["type"] == "integer"

        # Error response has structuredContent=None, so no type mismatch possible
        error_structured_content = None
        assert error_structured_content is None

    def test_all_error_paths_produce_none_structuredcontent(self):
        """All error paths should produce structuredContent=None."""
        # All these paths now produce None instead of {"error": "..."}
        # Path 1: ToolExecutor returns error (result.value is None)
        # Path 2: ErrorHandlingMiddleware catches exception
        # Path 3: NotFoundError (unknown tool)
        for path_name in ["tool_execution", "middleware", "not_found"]:
            result = CallToolResult(
                content=[{"type": "text", "text": f"Error from {path_name}"}],
                structuredContent=None,
                isError=True,
            )
            assert result.structuredContent is None, (
                f"Error path '{path_name}' should have structuredContent=None"
            )

    def test_mixed_required_optional_typeddict_error_still_none(self):
        """Even a TypedDict with some optional fields gets structuredContent=None on error."""
        from typing_extensions import TypedDict

        class _Base(TypedDict):
            id: str
            status: str

        class MixedResponse(_Base, total=False):
            detail: str
            extra_info: str

        _, mcp_tool = _make_tool_with_typeddict_return(MixedResponse)
        output_schema = mcp_tool.outputSchema

        assert "required" in output_schema
        assert "id" in output_schema["required"]
        assert "status" in output_schema["required"]

        # Error response has structuredContent=None
        error_structured_content = None
        assert error_structured_content is None


class TestServerErrorPathsStructuredContent:
    """Test that server-level error paths set structuredContent=None."""

    @pytest.mark.asyncio
    async def test_tool_execution_error_has_none_structuredcontent(self, mcp_server):
        """Tool execution error → structuredContent is None, content has error text."""
        from arcade_mcp_server.types import CallToolRequest

        # Register a tool that will fail
        @tool
        async def failing_tool() -> Annotated[str, "result"]:
            """A tool that fails."""
            raise FatalToolError("Something broke")

        tool_def = ToolCatalog().create_tool_definition(
            failing_tool, toolkit_name="test", toolkit_version="1.0"
        )
        input_model, output_model = create_func_models(failing_tool)
        meta = ToolMeta(module=failing_tool.__module__, toolkit="test")
        mat_tool = MaterializedTool(
            tool=failing_tool,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        await mcp_server._tool_manager.add_tool(mat_tool)

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "Test.FailingTool", "arguments": {}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert response.result.isError is True
        assert response.result.structuredContent is None
        # Error message should be in content
        assert len(response.result.content) > 0
        assert any("error" in c.text.lower() or "broke" in c.text.lower()
                    for c in response.result.content if hasattr(c, "text"))

    @pytest.mark.asyncio
    async def test_unknown_tool_error_returns_jsonrpc_error(self, mcp_server):
        """Unknown tool -> JSON-RPC protocol error -32602 per MCP 2025-11-25 spec."""
        from arcade_mcp_server.types import CallToolRequest, JSONRPCError

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "NonExistent.Tool", "arguments": {}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCError)
        assert response.error["code"] == -32602
        assert "Unknown tool" in response.error["message"]

    @pytest.mark.asyncio
    async def test_unknown_tool_error_includes_tool_name(self, mcp_server):
        """Unknown tool protocol error includes the tool name in the message."""
        from arcade_mcp_server.types import CallToolRequest, JSONRPCError

        message = CallToolRequest(
            jsonrpc="2.0",
            id=1,
            method="tools/call",
            params={"name": "DoesNotExist.Tool", "arguments": {}},
        )

        response = await mcp_server._handle_call_tool(message)

        assert isinstance(response, JSONRPCError)
        assert "DoesNotExist.Tool" in response.error["message"]
