"""Tests for context tool composition: call_raw, _call_remote, _handle_remote_auth, execute paths."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from arcade_core.errors import RetryableToolError, ToolResponseExtractionError
from arcade_core.structuring import OnMissing
from arcade_mcp_server.context import (
    Context,
    _ContextComponent,
    _has_null_fields,
    _make_empty,
    _raise_tool_error,
)
from arcade_mcp_server.types import CallToolResult, JSONRPCError, JSONRPCResponse, TextContent
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Helpers / Models
# ---------------------------------------------------------------------------


class SimpleModel(BaseModel):
    name: str
    value: int


class NestedModel(BaseModel):
    inner: SimpleModel
    tag: str


class ListModel(BaseModel):
    items: list[SimpleModel]


def _raw_result(
    text: str, structured: dict | None = None, is_error: bool = False
) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=structured,
        isError=is_error,
    )


# ---------------------------------------------------------------------------
# _ContextComponent._require_session
# ---------------------------------------------------------------------------


class TestContextComponent:
    def test_require_session_raises_when_none(self, mcp_server):
        ctx = Context(server=mcp_server)
        component = _ContextComponent(ctx)
        with pytest.raises(ValueError, match="Session not available"):
            component._require_session()

    def test_require_session_returns_session(self, mcp_server):
        ctx = Context(server=mcp_server)
        session = Mock()
        ctx.set_session(session)
        component = _ContextComponent(ctx)
        assert component._require_session() is session


# ---------------------------------------------------------------------------
# Context.set_request_id / set_tool_context / session_id
# ---------------------------------------------------------------------------


class TestContextMutators:
    def test_set_request_id(self, mcp_server):
        ctx = Context(server=mcp_server)
        assert ctx.request_id is None
        ctx.set_request_id("req-42")
        assert ctx.request_id == "req-42"

    def test_set_tool_context(self, mcp_server):
        from arcade_core.schema import ToolContext

        ctx = Context(server=mcp_server)
        tc = ToolContext(user_id="user@example.com")
        ctx.set_tool_context(tc)
        assert ctx.user_id == "user@example.com"

    def test_session_id_with_session(self, mcp_server):
        ctx = Context(server=mcp_server)
        session = Mock()
        session.session_id = "sess-123"
        ctx.set_session(session)
        assert ctx.session_id == "sess-123"


# ---------------------------------------------------------------------------
# Notifications — exception suppression in _flush_notifications
# ---------------------------------------------------------------------------


class TestFlushNotifications:
    @pytest.mark.asyncio
    async def test_exception_suppressed(self, mcp_server):
        ctx = Context(server=mcp_server)
        session = Mock()
        session.session_id = "sess-1"
        ctx.set_session(session)

        # Queue a notification
        await ctx.notifications.tools.list_changed()
        assert "notifications/tools/list_changed" in ctx._notification_queue

        # Make notification manager raise
        nm = Mock()
        nm.notify_tool_list_changed = AsyncMock(side_effect=RuntimeError("boom"))
        nm.notify_resource_list_changed = AsyncMock()
        mcp_server.notification_manager = nm

        # Should not raise — exception is suppressed
        await ctx._flush_notifications()
        # Queue is NOT cleared on exception (preserved for retry)
        assert "notifications/tools/list_changed" in ctx._notification_queue


# ---------------------------------------------------------------------------
# Resources — get, list, list_templates
# ---------------------------------------------------------------------------


class TestResources:
    @pytest.mark.asyncio
    async def test_get_returns_first_content(self, mcp_server):
        mcp_server._mcp_read_resource = AsyncMock(
            return_value=[{"uri": "file://a.txt", "text": "content A"}]
        )
        ctx = Context(server=mcp_server)
        result = await ctx.resources.get("file://a.txt")
        assert result["text"] == "content A"

    @pytest.mark.asyncio
    async def test_get_raises_when_empty(self, mcp_server):
        mcp_server._mcp_read_resource = AsyncMock(return_value=[])
        ctx = Context(server=mcp_server)
        with pytest.raises(ValueError, match="Resource not found"):
            await ctx.resources.get("file://missing.txt")

    @pytest.mark.asyncio
    async def test_list(self, mcp_server):
        resource = Mock()
        resource.uri = "file://a.txt"
        resource.name = "A"
        mcp_server._resource_manager.list_resources = AsyncMock(return_value=[resource])
        ctx = Context(server=mcp_server)
        roots = await ctx.resources.list()
        assert len(roots) == 1
        assert roots[0].name == "A"

    @pytest.mark.asyncio
    async def test_list_templates(self, mcp_server):
        tpl = Mock()
        tpl.uri_template = "file://{path}"
        mcp_server._resource_manager.list_resource_templates = AsyncMock(return_value=[tpl])
        ctx = Context(server=mcp_server)
        templates = await ctx.resources.list_templates()
        assert len(templates) == 1


# ---------------------------------------------------------------------------
# UI._validate_elicitation_schema
# ---------------------------------------------------------------------------


class TestElicitationSchemaValidation:
    def _ctx(self, mcp_server):
        return Context(server=mcp_server)

    def test_not_a_dict(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(TypeError, match="Schema must be a dictionary"):
            ctx.ui._validate_elicitation_schema("not a dict")

    def test_wrong_type(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(ValueError, match="type 'object'"):
            ctx.ui._validate_elicitation_schema({"type": "array"})

    def test_properties_not_dict(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(TypeError, match="properties must be a dictionary"):
            ctx.ui._validate_elicitation_schema({"type": "object", "properties": "bad"})

    def test_property_schema_not_dict(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(TypeError, match="Property 'x' schema must be a dictionary"):
            ctx.ui._validate_elicitation_schema({
                "type": "object",
                "properties": {"x": "not_a_dict"},
            })

    def test_unsupported_type(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(ValueError, match="unsupported type 'array'"):
            ctx.ui._validate_elicitation_schema({
                "type": "object",
                "properties": {"x": {"type": "array"}},
            })

    def test_unsupported_string_format(self, mcp_server):
        ctx = self._ctx(mcp_server)
        with pytest.raises(ValueError, match="unsupported format"):
            ctx.ui._validate_elicitation_schema({
                "type": "object",
                "properties": {"x": {"type": "string", "format": "ipv4"}},
            })


# ---------------------------------------------------------------------------
# Tools.call_raw — JSONRPCError path
# ---------------------------------------------------------------------------


class TestCallRaw:
    @pytest.mark.asyncio
    async def test_jsonrpc_error_returns_error_result(self, mcp_server):
        ctx = Context(server=mcp_server)
        error_response = JSONRPCError(
            id="req-1",
            error={"code": -32000, "message": "Internal error"},
        )
        mcp_server._handle_call_tool = AsyncMock(return_value=error_response)

        result = await ctx.tools.call_raw("SomeTool", {})
        assert result.isError is True
        assert "Internal error" in result.content[0].text

    @pytest.mark.asyncio
    async def test_fallback_to_arcade_cloud_when_tool_not_found(self, mcp_server):
        ctx = Context(server=mcp_server)

        # Local tool returns not-found
        not_found_result = CallToolResult(
            content=[TextContent(type="text", text="not found")],
            structuredContent={"_tool_not_found": True, "error": "not found"},
            isError=True,
        )
        local_response = JSONRPCResponse(id="req-1", result=not_found_result)
        mcp_server._handle_call_tool = AsyncMock(return_value=local_response)

        # Set up Arcade Cloud
        mcp_server.arcade = AsyncMock()
        remote_output = Mock()
        remote_output.value = {"key": "value"}
        remote_output.error = None
        remote_response = Mock()
        remote_response.success = True
        remote_response.output = remote_output
        mcp_server.arcade.tools.execute = AsyncMock(return_value=remote_response)

        result = await ctx.tools.call_raw("Remote_Tool", {})
        assert result.isError is False
        assert result.structuredContent == {"key": "value"}


# ---------------------------------------------------------------------------
# Tools._call_remote
# ---------------------------------------------------------------------------


class TestCallRemote:
    @pytest.mark.asyncio
    async def test_success_string_output(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        output = Mock()
        output.value = "hello world"
        output.error = None
        response = Mock()
        response.success = True
        response.output = output
        mcp_server.arcade.tools.execute = AsyncMock(return_value=response)

        result = await ctx.tools._call_remote("Test.Tool", {})
        assert result.isError is False
        assert result.content[0].text == "hello world"
        assert result.structuredContent == {"result": "hello world"}

    @pytest.mark.asyncio
    async def test_success_dict_output(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        output = Mock()
        output.value = {"temp": 72, "unit": "F"}
        output.error = None
        response = Mock()
        response.success = True
        response.output = output
        mcp_server.arcade.tools.execute = AsyncMock(return_value=response)

        result = await ctx.tools._call_remote("Weather.Get", {})
        assert result.isError is False
        assert result.structuredContent == {"temp": 72, "unit": "F"}

    @pytest.mark.asyncio
    async def test_failure_response(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        output = Mock()
        output.value = None
        output.error = "Permission denied"
        response = Mock()
        response.success = False
        response.output = output
        mcp_server.arcade.tools.execute = AsyncMock(return_value=response)

        result = await ctx.tools._call_remote("Tool.Fail", {})
        assert result.isError is True
        assert "Permission denied" in result.content[0].text

    @pytest.mark.asyncio
    async def test_403_auth_required(self, mcp_server):
        from arcadepy import APIStatusError

        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        error = APIStatusError(
            message="Forbidden",
            response=Mock(status_code=403),
            body={"error": "tool_authorization_required"},
        )
        error.status_code = 403
        error.body = {"error": "tool_authorization_required"}
        mcp_server.arcade.tools.execute = AsyncMock(side_effect=error)

        # Mock _handle_remote_auth
        ctx.tools._handle_remote_auth = AsyncMock(
            return_value=CallToolResult(
                content=[TextContent(type="text", text="auth needed")],
                isError=True,
            )
        )

        result = await ctx.tools._call_remote("Tool.NeedsAuth", {})
        assert result.isError is True
        ctx.tools._handle_remote_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_generic_exception(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()
        mcp_server.arcade.tools.execute = AsyncMock(side_effect=RuntimeError("network error"))

        result = await ctx.tools._call_remote("Tool.Bad", {})
        assert result.isError is True
        assert "network error" in result.content[0].text


# ---------------------------------------------------------------------------
# Tools._handle_remote_auth
# ---------------------------------------------------------------------------


class TestHandleRemoteAuth:
    @pytest.mark.asyncio
    async def test_already_completed(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        auth_response = Mock()
        auth_response.status = "completed"
        mcp_server.arcade.tools.authorize = AsyncMock(return_value=auth_response)

        result = await ctx.tools._handle_remote_auth("Tool.X", "user@test.com")
        assert result.isError is True
        assert "already complete" in result.content[0].text

    @pytest.mark.asyncio
    async def test_pending_authorization(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()

        auth_response = Mock()
        auth_response.status = "pending"
        auth_response.url = "https://auth.example.com/authorize?token=abc"
        mcp_server.arcade.tools.authorize = AsyncMock(return_value=auth_response)

        result = await ctx.tools._handle_remote_auth("Tool.X", "user@test.com")
        assert result.isError is True
        assert "Authorization required" in result.content[0].text
        assert "https://auth.example.com" in result.content[0].text
        assert result.structuredContent["authorization_url"] == auth_response.url

    @pytest.mark.asyncio
    async def test_authorize_exception(self, mcp_server):
        ctx = Context(server=mcp_server)
        mcp_server.arcade = AsyncMock()
        mcp_server.arcade.tools.authorize = AsyncMock(side_effect=RuntimeError("timeout"))

        result = await ctx.tools._handle_remote_auth("Tool.X", "user@test.com")
        assert result.isError is True
        assert "Failed to authorize" in result.content[0].text


# ---------------------------------------------------------------------------
# Tools.execute — error and fallback paths
# ---------------------------------------------------------------------------


class TestExecutePaths:
    @pytest.mark.asyncio
    async def test_raises_on_tool_error(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result(
                "error occurred",
                structured={"error": "bad input"},
                is_error=True,
            )
        )

        with pytest.raises(ToolResponseExtractionError, match="bad input"):
            await ctx.tools.execute(SimpleModel, "Tool.X", {})

    @pytest.mark.asyncio
    async def test_sampling_fails_returns_tier12_result(self, mcp_server):
        """When sampling fails (non-capability error) and tier 1-2 had a partial result."""
        ctx = Context(server=mcp_server)
        # Tier 1-2 returns partial (name present, value missing → null with ALLOW_NULL)
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result("data", structured={"name": "test"})
        )
        # Sampling available but fails with a generic error
        ctx.tools._extract_via_sampling = AsyncMock(side_effect=RuntimeError("LLM error"))

        result = await ctx.tools.execute(
            SimpleModel, "Tool.X", {}, options={"on_missing": OnMissing.ALLOW_NULL}
        )
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_sampling_fails_no_tier12_allow_null_returns_empty(self, mcp_server):
        """When sampling fails and no tier 1-2 result, ALLOW_NULL returns empty model."""
        ctx = Context(server=mcp_server)
        # No structured content → no tier 1-2 result
        ctx.tools.call_raw = AsyncMock(return_value=_raw_result("raw text only"))
        ctx.tools._extract_via_sampling = AsyncMock(side_effect=RuntimeError("LLM error"))

        result = await ctx.tools.execute(
            SimpleModel, "Tool.X", {}, options={"on_missing": OnMissing.ALLOW_NULL}
        )
        assert result.name is None  # type: ignore[comparison-overlap]

    @pytest.mark.asyncio
    async def test_retryable_tool_error_retries(self, mcp_server):
        """RetryableToolError should be retried up to max_retries."""
        ctx = Context(server=mcp_server)
        call_count = 0

        async def _call_raw_side_effect(name, params):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableToolError("transient")
            return _raw_result("ok", structured={"name": "done", "value": 42})

        ctx.tools.call_raw = AsyncMock(side_effect=_call_raw_side_effect)

        result = await ctx.tools.execute(
            SimpleModel, "Tool.X", {}, options={"max_retries": 3, "retry_delay_seconds": 0.01}
        )
        assert result.name == "done"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_extraction_error_raises_immediately(self, mcp_server):
        """ToolResponseExtractionError should not be retried."""
        ctx = Context(server=mcp_server)
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result("error", structured={"error": "bad"}, is_error=True)
        )

        with pytest.raises(ToolResponseExtractionError):
            await ctx.tools.execute(SimpleModel, "Tool.X", {}, options={"max_retries": 3})

    @pytest.mark.asyncio
    async def test_validation_error_retries_and_exhausts(self, mcp_server):
        """ValidationError should retry and eventually raise ToolResponseExtractionError."""
        ctx = Context(server=mcp_server)
        # Returns data that passes tool call but fails Pydantic validation
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result("bad", structured={"wrong_key": "x"})
        )
        # Sampling always returns bad JSON
        ctx.tools._extract_via_sampling = AsyncMock(side_effect=json.JSONDecodeError("bad", "", 0))

        with pytest.raises(ToolResponseExtractionError, match="Failed to extract"):
            await ctx.tools.execute(
                SimpleModel,
                "Tool.X",
                {},
                options={"max_retries": 1, "retry_delay_seconds": 0.01},
            )


# ---------------------------------------------------------------------------
# _extract_via_sampling — additional paths
# ---------------------------------------------------------------------------


class TestExtractViaSamplingPaths:
    @pytest.mark.asyncio
    async def test_structured_content_preferred(self, mcp_server):
        """When structuredContent is available, it's used as raw_text."""
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        response_text = '{"name": "test", "value": 42}'
        text_content = TextContent(type="text", text=response_text)
        mock_session.create_message = AsyncMock(return_value=MagicMock(content=text_content))
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result("text", structured={"name": "test", "value": 42})
        result = await ctx.tools._extract_via_sampling(SimpleModel, raw, OnMissing.FAIL)
        assert result.name == "test"
        assert result.value == 42

    @pytest.mark.asyncio
    async def test_allow_null_instruction_included(self, mcp_server):
        """When on_missing is ALLOW_NULL, the null instruction is in the prompt."""
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        response_text = '{"name": "test", "value": 0}'
        text_content = TextContent(type="text", text=response_text)
        mock_session.create_message = AsyncMock(return_value=MagicMock(content=text_content))
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result("data")
        await ctx.tools._extract_via_sampling(SimpleModel, raw, OnMissing.ALLOW_NULL)

        # Verify the system prompt includes the null instruction
        call_kwargs = mock_session.create_message.call_args[1]
        assert "null" in call_kwargs.get("system_prompt", "").lower()

    @pytest.mark.asyncio
    async def test_unexpected_sampling_error_raises_extraction_error(self, mcp_server):
        """Non-capability sampling errors raise ToolResponseExtractionError."""
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        mock_session.create_message = AsyncMock(
            side_effect=RuntimeError("Unexpected internal error")
        )
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result("data")
        with pytest.raises(ToolResponseExtractionError, match="sampling failed unexpectedly"):
            await ctx.tools._extract_via_sampling(SimpleModel, raw, OnMissing.FAIL)

    @pytest.mark.asyncio
    async def test_result_with_content_attribute(self, mcp_server):
        """When sampling returns object with .content that is TextContent."""
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        text_content = TextContent(type="text", text='{"name": "x", "value": 1}')
        result_obj = MagicMock()
        result_obj.content = text_content
        mock_session.create_message = AsyncMock(return_value=result_obj)
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result("data")
        result = await ctx.tools._extract_via_sampling(SimpleModel, raw, OnMissing.FAIL)
        assert result.name == "x"

    @pytest.mark.asyncio
    async def test_result_fallback_to_str(self, mcp_server):
        """When sampling returns unknown type, falls back to str()."""
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        # Return something that isn't TextContent and doesn't have .content as TextContent
        result_obj = '{"name": "x", "value": 1}'
        mock_session.create_message = AsyncMock(return_value=result_obj)
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result("data")
        result = await ctx.tools._extract_via_sampling(SimpleModel, raw, OnMissing.FAIL)
        assert result.name == "x"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestModuleHelpers:
    def test_make_empty(self):
        result = _make_empty(SimpleModel)
        assert result.name is None  # type: ignore[comparison-overlap]
        assert result.value is None  # type: ignore[comparison-overlap]

    def test_raise_tool_error_with_llm_instructions(self):
        raw = _raw_result(
            "error",
            structured={
                "error": "generic error",
                "llm_instructions": "Please authorize at https://example.com",
            },
            is_error=True,
        )
        with pytest.raises(ToolResponseExtractionError, match=r"authorize at https://example\.com"):
            _raise_tool_error("Tool.X", raw)

    def test_raise_tool_error_falls_back_to_error_key(self):
        raw = _raw_result(
            "error",
            structured={"error": "Something broke"},
            is_error=True,
        )
        with pytest.raises(ToolResponseExtractionError, match="Something broke"):
            _raise_tool_error("Tool.X", raw)

    def test_raise_tool_error_no_structured_content(self):
        raw = _raw_result("error", is_error=True)
        with pytest.raises(ToolResponseExtractionError, match="Unknown error"):
            _raise_tool_error("Tool.X", raw)

    def test_has_null_fields_with_none(self):
        class M(BaseModel):
            a: str | None = None
            b: int = 1

        m = M(a=None)
        assert _has_null_fields(m) is True

    def test_has_null_fields_nested_model(self):
        class Inner(BaseModel):
            x: str | None = None

        class Outer(BaseModel):
            inner: Inner
            name: str = "ok"

        m = Outer(inner=Inner(x=None))
        assert _has_null_fields(m) is True

    def test_has_null_fields_in_list(self):
        class Item(BaseModel):
            val: str | None = None

        class Container(BaseModel):
            items: list[Item]

        m = Container(items=[Item(val=None)])
        assert _has_null_fields(m) is True
