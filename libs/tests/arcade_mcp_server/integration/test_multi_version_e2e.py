"""End-to-end multi-version integration tests (Phase 9).

Tests the full MCP protocol flow for both 2025-06-18 and 2025-11-25 sessions,
including version negotiation, capability gating, task lifecycle, sampling,
elicitation, transport compliance, and authorization-context isolation.

All tests operate at the server.handle_message() + session layer — no HTTP
or ASGI plumbing — except transport-compliance tests which call the helpers
from http_session_manager directly.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from arcade_mcp_server.resource_server.base import ResourceOwner
from arcade_mcp_server.server import INSUFFICIENT_SCOPE_ERROR_CODE, MCPServer
from arcade_mcp_server.session import InitializationState, ServerSession
from arcade_mcp_server.types import (
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_msg(version: str, *, msg_id: int = 1, capabilities: dict[str, Any] | None = None) -> dict:
    """Build a JSON-RPC initialize request."""
    caps = capabilities if capabilities is not None else {"tools": {}, "sampling": {}}
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": caps,
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }


def _notification_initialized() -> dict:
    return {"jsonrpc": "2.0", "method": "notifications/initialized"}


def _list_tools_msg(msg_id: int = 2) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/list", "params": {}}


def _call_tool_msg(
    name: str,
    arguments: dict | None = None,
    *,
    msg_id: int = 3,
    task: dict | None = None,
    meta: dict | None = None,
) -> dict:
    params: dict[str, Any] = {"name": name, "arguments": arguments or {}}
    if task is not None:
        params["task"] = task
    if meta is not None:
        params["_meta"] = meta
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call", "params": params}


def _ping_msg(msg_id: int = 10) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": "ping"}


def _tasks_get_msg(task_id: str, msg_id: int = 20) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tasks/get",
        "params": {"taskId": task_id},
    }


def _tasks_result_msg(task_id: str, msg_id: int = 21) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tasks/result",
        "params": {"taskId": task_id},
    }


def _tasks_list_msg(msg_id: int = 22) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "method": "tasks/list", "params": {}}


def _tasks_cancel_msg(task_id: str, msg_id: int = 23) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tasks/cancel",
        "params": {"taskId": task_id},
    }


def _make_resource_owner(
    user_id: str,
    *,
    client_id: str = "test-client",
    issuer: str = "https://issuer.example.com",
    scopes: str = "",
) -> ResourceOwner:
    """Create a ResourceOwner for test isolation checks."""
    claims: dict[str, Any] = {"iss": issuer, "sub": user_id}
    if scopes:
        claims["scope"] = scopes
    return ResourceOwner(user_id=user_id, client_id=client_id, claims=claims)


async def _init_session(
    server: MCPServer,
    session: ServerSession,
    version: str,
    *,
    capabilities: dict[str, Any] | None = None,
    resource_owner: ResourceOwner | None = None,
) -> dict[str, Any]:
    """Send initialize + notifications/initialized, return init result."""
    resp = await server.handle_message(
        _init_msg(version, capabilities=capabilities), session, resource_owner=resource_owner
    )
    assert resp is not None
    result = resp.result if hasattr(resp, "result") else None
    assert result is not None, f"Initialize failed: {resp}"

    # Send initialized notification
    await server.handle_message(_notification_initialized(), session)
    assert session.initialization_state == InitializationState.INITIALIZED

    if hasattr(result, "model_dump"):
        return result.model_dump(exclude_none=True, by_alias=True)
    return dict(result)  # type: ignore[arg-type]


def _make_session(
    server: MCPServer,
    *,
    stateless: bool = False,
) -> ServerSession:
    """Create a fresh session with mock streams."""
    write_stream = AsyncMock()
    write_stream.send = AsyncMock()
    read_stream = AsyncMock()
    return ServerSession(
        server=server,
        read_stream=read_stream,
        write_stream=write_stream,
        stateless=stateless,
    )


# ---------------------------------------------------------------------------
# TestE2EVersion2025_06_18
# ---------------------------------------------------------------------------


class TestE2EVersion2025_06_18:
    """Full integration test simulating a 2025-06-18 client."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mcp_server: MCPServer) -> None:
        """
        1. Initialize with 2025-06-18
        2. Assert protocolVersion=2025-06-18, no tasks cap, no icons/description/websiteUrl
        3. tools/list -> success, no icons on tools
        4. tasks/get -> -32601
        5. tools/call -> normal CallToolResult
        6. ping -> success
        """
        session = _make_session(mcp_server)
        result = await _init_session(mcp_server, session, "2025-06-18")

        # protocolVersion
        assert result["protocolVersion"] == "2025-06-18"

        # No tasks capability
        caps = result.get("capabilities", {})
        assert "tasks" not in caps

        # Server info: no icons/description/websiteUrl
        server_info = result.get("serverInfo", {})
        assert "icons" not in server_info
        assert "description" not in server_info
        assert "websiteUrl" not in server_info
        # But has name/version/title
        assert "name" in server_info
        assert "version" in server_info

        # tools/list -- no icons on tools
        tools_resp = await mcp_server.handle_message(_list_tools_msg(), session)
        assert tools_resp is not None
        tools_result = tools_resp.result
        tool_list = (
            tools_result.tools
            if hasattr(tools_result, "tools")
            else tools_result.get("tools", [])
        )
        for t in tool_list:
            if isinstance(t, dict):
                t_dict = t
            elif hasattr(t, "model_dump"):
                t_dict = t.model_dump(exclude_none=True, by_alias=True)
            else:
                t_dict = {}
            assert "icons" not in t_dict, f"Tool {t_dict.get('name')} has icons on 2025-06-18"
            # execution should also be stripped for legacy clients
            assert "execution" not in t_dict

        # tasks/get -> -32601 (capability gated)
        tasks_resp = await mcp_server.handle_message(
            _tasks_get_msg("nonexistent", msg_id=5), session
        )
        assert tasks_resp is not None
        assert hasattr(tasks_resp, "error")
        assert tasks_resp.error["code"] == -32601

        # tools/call -> normal result
        call_resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "hello"}, msg_id=6),
            session,
        )
        assert call_resp is not None
        assert hasattr(call_resp, "result")
        call_result = call_resp.result
        # Should be a CallToolResult, not a CreateTaskResult
        if hasattr(call_result, "model_dump"):
            cr = call_result.model_dump(exclude_none=True, by_alias=True)
        else:
            cr = dict(call_result)
        assert "task" not in cr, "Legacy call should not return CreateTaskResult"
        assert "content" in cr

        # ping -> success
        ping_resp = await mcp_server.handle_message(_ping_msg(msg_id=7), session)
        assert ping_resp is not None
        assert hasattr(ping_resp, "result")

    @pytest.mark.asyncio
    async def test_existing_tools_work_unchanged(self, mcp_server: MCPServer) -> None:
        """All tool calling behavior is identical to pre-change behavior."""
        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-06-18")

        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "world"}),
            session,
        )
        assert resp is not None
        result = resp.result
        if hasattr(result, "model_dump"):
            rd = result.model_dump(exclude_none=True, by_alias=True)
        else:
            rd = dict(result)
        assert "content" in rd
        # Content should contain the echoed text
        content_items = rd["content"]
        assert any("world" in str(c) for c in content_items)

    @pytest.mark.asyncio
    async def test_sampling_has_no_tool_fields(self, mcp_server: MCPServer) -> None:
        """Sampling requests to 2025-06-18 sessions never include tools/toolChoice."""
        session = _make_session(mcp_server)
        await _init_session(
            mcp_server,
            session,
            "2025-06-18",
            capabilities={"sampling": {}, "tools": {}},
        )

        # Mock the request manager to capture what is sent
        mock_request_manager = AsyncMock()
        mock_request_manager.send_request = AsyncMock(
            return_value={"role": "assistant", "content": {"type": "text", "text": "hi"}, "model": "test"}
        )
        session._request_manager = mock_request_manager

        await session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hello"}}],
            max_tokens=100,
            tools=[{"name": "some_tool", "inputSchema": {}}],
            tool_choice={"type": "auto"},
        )

        # Check the params sent
        sent_params = mock_request_manager.send_request.call_args[0][1]
        assert "tools" not in sent_params, "tools should be stripped for 2025-06-18"
        assert "toolChoice" not in sent_params, "toolChoice should be stripped for 2025-06-18"


# ---------------------------------------------------------------------------
# TestE2EVersion2025_11_25
# ---------------------------------------------------------------------------


class TestE2EVersion2025_11_25:
    """Full integration test simulating a 2025-11-25 client."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mcp_server: MCPServer) -> None:
        """
        1. Initialize with 2025-11-25
        2. Assert protocolVersion=2025-11-25 + tasks cap with nested requests
        3. tools/list -> returns execution field
        4. tools/call with task metadata -> CreateTaskResult
        5. tasks/get -> working
        6. tasks/result -> blocks -> returns result
        7. tasks/list includes the task
        8. Create + cancel another task
        """
        session = _make_session(mcp_server)
        result = await _init_session(mcp_server, session, "2025-11-25")

        assert result["protocolVersion"] == "2025-11-25"

        # tasks capability with nested structure
        caps = result.get("capabilities", {})
        assert "tasks" in caps
        tasks_cap = caps["tasks"]
        assert "requests" in tasks_cap
        assert "tools" in tasks_cap["requests"]
        assert "call" in tasks_cap["requests"]["tools"]

        # tools/list -> execution field present on tools that have it
        tools_resp = await mcp_server.handle_message(_list_tools_msg(), session)
        assert tools_resp is not None
        tool_list = tools_resp.result.tools if hasattr(tools_resp.result, "tools") else tools_resp.result.get("tools", [])
        # At least the test_tool should have execution
        tool_names_with_execution = []
        for t in tool_list:
            if isinstance(t, dict):
                td = t
            elif hasattr(t, "model_dump"):
                td = t.model_dump(exclude_none=True, by_alias=True)
            else:
                td = {}
            if td.get("execution"):
                tool_names_with_execution.append(td.get("name"))
        assert len(tool_names_with_execution) > 0, "Expected at least one tool with execution field"

        # tools/call with task metadata -> CreateTaskResult
        call_resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "async"}, task={"ttl": 60000}, msg_id=5),
            session,
        )
        assert call_resp is not None
        cr = call_resp.result
        if hasattr(cr, "model_dump"):
            cr_dict = cr.model_dump(exclude_none=True, by_alias=True)
        else:
            cr_dict = dict(cr)
        assert "task" in cr_dict, "Expected CreateTaskResult with task field"
        task_id = cr_dict["task"]["taskId"]

        # tasks/get -> returns task state
        get_resp = await mcp_server.handle_message(_tasks_get_msg(task_id, msg_id=6), session)
        assert get_resp is not None
        assert hasattr(get_resp, "result")
        get_result = get_resp.result
        if hasattr(get_result, "model_dump"):
            gr = get_result.model_dump(exclude_none=True, by_alias=True)
        else:
            gr = dict(get_result)
        assert gr["taskId"] == task_id

        # tasks/result -> blocks until done, then returns tool result
        # Give the background task a moment to complete
        await asyncio.sleep(0.3)
        result_resp = await mcp_server.handle_message(
            _tasks_result_msg(task_id, msg_id=7), session
        )
        assert result_resp is not None
        assert hasattr(result_resp, "result")

        # tasks/list -> includes this task
        list_resp = await mcp_server.handle_message(_tasks_list_msg(msg_id=8), session)
        assert list_resp is not None
        list_result = list_resp.result
        if hasattr(list_result, "model_dump"):
            lr = list_result.model_dump(exclude_none=True, by_alias=True)
        else:
            lr = dict(list_result)
        tasks_in_list = lr.get("tasks", [])
        assert any(t.get("taskId") == task_id for t in tasks_in_list)

        # Create + cancel another task
        call2_resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.slow_tool", {}, task={"ttl": 60000}, msg_id=9),
            session,
        )
        assert call2_resp is not None
        cr2 = call2_resp.result
        if hasattr(cr2, "model_dump"):
            cr2_dict = cr2.model_dump(exclude_none=True, by_alias=True)
        else:
            cr2_dict = dict(cr2)
        task2_id = cr2_dict["task"]["taskId"]

        cancel_resp = await mcp_server.handle_message(
            _tasks_cancel_msg(task2_id, msg_id=10), session
        )
        assert cancel_resp is not None
        assert hasattr(cancel_resp, "result")
        cancel_result = cancel_resp.result
        if hasattr(cancel_result, "model_dump"):
            crd = cancel_result.model_dump(exclude_none=True, by_alias=True)
        else:
            crd = dict(cancel_result)
        assert crd["status"] in ("cancelled", "CANCELLED", TaskStatus.CANCELLED.value)

    @pytest.mark.asyncio
    async def test_task_augmented_tool_full_lifecycle(self, mcp_server: MCPServer) -> None:
        """tools/call with task -> tasks/get (poll) -> tasks/result (block) -> verify."""
        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-11-25")

        # Start task-augmented call
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "lifecycle"}, task={}, msg_id=5),
            session,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        task_id = cr["task"]["taskId"]

        # Poll with tasks/get
        await asyncio.sleep(0.3)
        get_resp = await mcp_server.handle_message(_tasks_get_msg(task_id, msg_id=6), session)
        gr = get_resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(get_resp.result, "model_dump") else dict(get_resp.result)
        # Task should be terminal by now (fast tool)
        assert gr["status"] in ("completed", "COMPLETED", TaskStatus.COMPLETED.value)

        # tasks/result -> underlying tool result
        result_resp = await mcp_server.handle_message(_tasks_result_msg(task_id, msg_id=7), session)
        assert hasattr(result_resp, "result")
        rr = result_resp.result
        if hasattr(rr, "model_dump"):
            rrd = rr.model_dump(exclude_none=True, by_alias=True)
        else:
            rrd = dict(rr) if isinstance(rr, dict) else rr
        # The underlying result is a CallToolResult with content
        if isinstance(rrd, dict):
            assert "content" in rrd or "_meta" in rrd

    @pytest.mark.asyncio
    async def test_task_cancel_stops_background_execution(self, mcp_server: MCPServer) -> None:
        """tasks/cancel on a running task-augmented tool call cancels the bg task."""
        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-11-25")

        # Start slow tool as task
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.slow_tool", {}, task={"ttl": 60000}, msg_id=5),
            session,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        task_id = cr["task"]["taskId"]

        # Brief pause so background task starts
        await asyncio.sleep(0.05)

        # Cancel
        cancel_resp = await mcp_server.handle_message(
            _tasks_cancel_msg(task_id, msg_id=6), session
        )
        cancel_result = cancel_resp.result
        if hasattr(cancel_result, "model_dump"):
            crd = cancel_result.model_dump(exclude_none=True, by_alias=True)
        else:
            crd = dict(cancel_result)
        assert crd["status"] in ("cancelled", "CANCELLED", TaskStatus.CANCELLED.value)

        # Verify tasks/get also shows cancelled
        await asyncio.sleep(0.1)
        get_resp = await mcp_server.handle_message(_tasks_get_msg(task_id, msg_id=7), session)
        gr = get_resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(get_resp.result, "model_dump") else dict(get_resp.result)
        assert gr["status"] in ("cancelled", "CANCELLED", TaskStatus.CANCELLED.value)

    @pytest.mark.asyncio
    async def test_task_status_notification_sent(self, mcp_server: MCPServer) -> None:
        """notifications/tasks/status is sent when task completes."""
        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-11-25")

        # Start task
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "notify"}, task={}, msg_id=5),
            session,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        task_id = cr["task"]["taskId"]

        # Wait for background execution to complete and notification to be sent
        await asyncio.sleep(0.5)

        # Check write_stream.send was called with a task status notification
        calls = session.write_stream.send.call_args_list
        notification_found = False
        for call in calls:
            raw = call[0][0] if call[0] else None
            if raw is None:
                continue
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if msg.get("method") == "notifications/tasks/status":
                params = msg.get("params", {})
                if params.get("taskId") == task_id:
                    notification_found = True
                    break
        assert notification_found, "Expected notifications/tasks/status for completed task"

    @pytest.mark.asyncio
    async def test_sampling_with_tools(self, mcp_server: MCPServer) -> None:
        """Server sends sampling request with tools to 2025-11-25 session declaring sampling.tools."""
        session = _make_session(mcp_server)
        await _init_session(
            mcp_server,
            session,
            "2025-11-25",
            capabilities={"sampling": {"tools": {}}, "tools": {}},
        )

        # Mock request manager to capture the sent params
        mock_rm = AsyncMock()
        mock_rm.send_request = AsyncMock(
            return_value={"role": "assistant", "content": {"type": "text", "text": "ok"}, "model": "test"}
        )
        session._request_manager = mock_rm

        tools = [{"name": "helper", "inputSchema": {"type": "object"}}]
        tool_choice = {"type": "auto"}

        await session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "do stuff"}}],
            max_tokens=200,
            tools=tools,
            tool_choice=tool_choice,
        )

        sent_params = mock_rm.send_request.call_args[0][1]
        assert "tools" in sent_params, "tools should be included for 2025-11-25 with sampling.tools"
        assert sent_params["tools"] == tools
        assert "toolChoice" in sent_params
        assert sent_params["toolChoice"] == tool_choice

    @pytest.mark.asyncio
    async def test_url_mode_elicitation(self, mcp_server: MCPServer) -> None:
        """Server sends URL-mode elicitation with elicitationId to 2025-11-25 client."""
        session = _make_session(mcp_server)
        await _init_session(
            mcp_server,
            session,
            "2025-11-25",
            capabilities={"elicitation": {"url": True}, "tools": {}},
        )

        mock_rm = AsyncMock()
        mock_rm.send_request = AsyncMock(
            return_value={"action": "accept"}
        )
        session._request_manager = mock_rm

        result = await session.elicit(
            message="Please authenticate",
            mode="url",
            url="https://example.com/auth",
            elicitation_id="elicit-123",
        )

        sent_method = mock_rm.send_request.call_args[0][0]
        sent_params = mock_rm.send_request.call_args[0][1]
        assert sent_method == "elicitation/create"
        assert sent_params.get("mode") == "url"
        assert sent_params.get("url") == "https://example.com/auth"
        assert sent_params.get("elicitationId") == "elicit-123"

    @pytest.mark.asyncio
    async def test_elicitation_complete_notification(self, mcp_server: MCPServer) -> None:
        """send_elicitation_complete writes notification to session write stream."""
        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-11-25")

        await session.send_elicitation_complete("elicit-456")

        calls = session.write_stream.send.call_args_list
        notification_found = False
        for call in calls:
            raw = call[0][0] if call[0] else None
            if raw is None:
                continue
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if msg.get("method") == "notifications/elicitation/complete":
                assert msg["params"]["elicitationId"] == "elicit-456"
                notification_found = True
                break
        assert notification_found, "Expected notifications/elicitation/complete"


# ---------------------------------------------------------------------------
# TestE2EVersionNegotiation
# ---------------------------------------------------------------------------


class TestE2EVersionNegotiation:

    @pytest.mark.asyncio
    async def test_future_client_gets_latest_supported(self, mcp_server: MCPServer) -> None:
        """Client with protocolVersion=2030-01-01 gets 2025-11-25."""
        session = _make_session(mcp_server)
        result = await _init_session(mcp_server, session, "2030-01-01")
        assert result["protocolVersion"] == "2025-11-25"

    @pytest.mark.asyncio
    async def test_two_concurrent_sessions_different_versions(self, mcp_server: MCPServer) -> None:
        """Two sessions with different versions coexist correctly."""
        session_old = _make_session(mcp_server)
        session_new = _make_session(mcp_server)

        result_old = await _init_session(mcp_server, session_old, "2025-06-18")
        result_new = await _init_session(mcp_server, session_new, "2025-11-25")

        assert result_old["protocolVersion"] == "2025-06-18"
        assert result_new["protocolVersion"] == "2025-11-25"

        # Different negotiated versions
        assert session_old.negotiated_version == "2025-06-18"
        assert session_new.negotiated_version == "2025-11-25"

        # Capability views differ: old has no tasks, new does
        assert "tasks" not in result_old.get("capabilities", {})
        assert "tasks" in result_new.get("capabilities", {})

        # tools/list differs: old has no execution field
        tools_old_resp = await mcp_server.handle_message(_list_tools_msg(msg_id=10), session_old)
        tools_new_resp = await mcp_server.handle_message(_list_tools_msg(msg_id=11), session_new)
        old_tools = tools_old_resp.result.tools if hasattr(tools_old_resp.result, "tools") else []
        new_tools = tools_new_resp.result.tools if hasattr(tools_new_resp.result, "tools") else []

        for t in old_tools:
            td = t if isinstance(t, dict) else t.model_dump(exclude_none=True, by_alias=True) if hasattr(t, "model_dump") else {}
            assert "execution" not in td
        # At least some new tools should have execution
        has_execution = False
        for t in new_tools:
            td = t if isinstance(t, dict) else t.model_dump(exclude_none=True, by_alias=True) if hasattr(t, "model_dump") else {}
            if td.get("execution"):
                has_execution = True
                break
        assert has_execution, "2025-11-25 tools/list should include execution field"


# ---------------------------------------------------------------------------
# TestE2EAuthContextTaskIsolation
# ---------------------------------------------------------------------------


class TestE2EAuthContextTaskIsolation:
    """Integration tests for authorization-context-based task isolation."""

    @pytest.mark.asyncio
    async def test_same_user_different_sessions_share_tasks(self, mcp_server: MCPServer) -> None:
        """Two sessions authenticated as the same user can see each other's tasks."""
        owner = _make_resource_owner("alice")

        session1 = _make_session(mcp_server)
        session2 = _make_session(mcp_server)
        await _init_session(mcp_server, session1, "2025-11-25", resource_owner=owner)
        await _init_session(mcp_server, session2, "2025-11-25", resource_owner=owner)

        # Create a task via session1
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "shared"}, task={}, msg_id=5),
            session1,
            resource_owner=owner,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        task_id = cr["task"]["taskId"]

        await asyncio.sleep(0.3)

        # Session2 (same user) can see the task
        list_resp = await mcp_server.handle_message(
            _tasks_list_msg(msg_id=6), session2, resource_owner=owner
        )
        lr = list_resp.result
        if hasattr(lr, "model_dump"):
            lrd = lr.model_dump(exclude_none=True, by_alias=True)
        else:
            lrd = dict(lr)
        task_ids = [t.get("taskId") for t in lrd.get("tasks", [])]
        assert task_id in task_ids

    @pytest.mark.asyncio
    async def test_different_users_cannot_see_each_others_tasks(self, mcp_server: MCPServer) -> None:
        """Tasks created by user A are invisible to user B."""
        owner_a = _make_resource_owner("alice")
        owner_b = _make_resource_owner("bob")

        session_a = _make_session(mcp_server)
        session_b = _make_session(mcp_server)
        await _init_session(mcp_server, session_a, "2025-11-25", resource_owner=owner_a)
        await _init_session(mcp_server, session_b, "2025-11-25", resource_owner=owner_b)

        # Alice creates a task
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "alice"}, task={}, msg_id=5),
            session_a,
            resource_owner=owner_a,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        alice_task_id = cr["task"]["taskId"]

        await asyncio.sleep(0.3)

        # Bob cannot see Alice's task
        list_resp = await mcp_server.handle_message(
            _tasks_list_msg(msg_id=6), session_b, resource_owner=owner_b
        )
        lr = list_resp.result
        if hasattr(lr, "model_dump"):
            lrd = lr.model_dump(exclude_none=True, by_alias=True)
        else:
            lrd = dict(lr)
        task_ids = [t.get("taskId") for t in lrd.get("tasks", [])]
        assert alice_task_id not in task_ids

    @pytest.mark.asyncio
    async def test_stdio_sessions_isolated_by_session_id(self, mcp_server: MCPServer) -> None:
        """Unauthenticated stdio sessions fall back to session-based isolation."""
        session1 = _make_session(mcp_server)
        session2 = _make_session(mcp_server)
        await _init_session(mcp_server, session1, "2025-11-25")
        await _init_session(mcp_server, session2, "2025-11-25")

        # Different session IDs
        assert session1.session_id != session2.session_id

        # Session1 creates a task (no resource_owner -> stdio isolation)
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "s1"}, task={}, msg_id=5),
            session1,
        )
        cr = resp.result.model_dump(exclude_none=True, by_alias=True) if hasattr(resp.result, "model_dump") else dict(resp.result)
        s1_task_id = cr["task"]["taskId"]

        await asyncio.sleep(0.3)

        # Session2 cannot see session1's task
        list_resp = await mcp_server.handle_message(
            _tasks_list_msg(msg_id=6), session2
        )
        lr = list_resp.result
        if hasattr(lr, "model_dump"):
            lrd = lr.model_dump(exclude_none=True, by_alias=True)
        else:
            lrd = dict(lr)
        task_ids = [t.get("taskId") for t in lrd.get("tasks", [])]
        assert s1_task_id not in task_ids


# ---------------------------------------------------------------------------
# TestE2ECapabilityNegotiation
# ---------------------------------------------------------------------------


class TestE2ECapabilityNegotiation:
    """Integration tests for capability-gated behavior."""

    @pytest.mark.asyncio
    async def test_stateless_2025_11_25_session_has_no_tasks_capability(
        self, mcp_server: MCPServer
    ) -> None:
        """Stateless HTTP mode excludes tasks from capabilities (AD 13)."""
        # Test via _build_capabilities directly
        caps = mcp_server._build_capabilities("2025-11-25", stateless=True)
        assert "tasks" not in caps

        # Also test that tasks/get returns -32601 on such a session
        session = _make_session(mcp_server, stateless=True)
        await _init_session(mcp_server, session, "2025-11-25")

        # tasks/get should be rejected by capability gate
        resp = await mcp_server.handle_message(_tasks_get_msg("anything", msg_id=5), session)
        assert resp is not None
        assert hasattr(resp, "error")
        assert resp.error["code"] == -32601

    @pytest.mark.asyncio
    async def test_stateless_capability_omission_ignores_task_metadata(
        self, mcp_server: MCPServer
    ) -> None:
        """In stateless mode, tools/call with task metadata processes normally
        (ignores task metadata per capability fallback)."""
        session = _make_session(mcp_server, stateless=True)
        await _init_session(mcp_server, session, "2025-11-25")

        # tools/call with task metadata — should NOT return CreateTaskResult
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.test_tool", {"text": "stateless"}, task={}, msg_id=5),
            session,
        )
        assert resp is not None
        assert hasattr(resp, "result")
        cr = resp.result
        if hasattr(cr, "model_dump"):
            crd = cr.model_dump(exclude_none=True, by_alias=True)
        else:
            crd = dict(cr)
        # Should be a normal CallToolResult, not a CreateTaskResult
        assert "content" in crd, "Expected normal CallToolResult"
        assert "task" not in crd, "Should not return CreateTaskResult in stateless mode"


# ---------------------------------------------------------------------------
# TestE2ETransportCompliance
# ---------------------------------------------------------------------------


class TestE2ETransportCompliance:
    """Integration tests for HTTP transport spec compliance.

    These test the transport validation helper functions directly (simplified
    from full HTTP-level tests for robustness, following test_phase7_transport.py
    patterns).
    """

    def test_origin_enforcement_rejects_invalid_origin(self) -> None:
        """HTTP transport rejects requests with invalid Origin header."""
        from arcade_mcp_server.transports.http_session_manager import _validate_origin
        from starlette.requests import Request as StarletteRequest

        def _make_req(headers: dict[str, str]) -> StarletteRequest:
            raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
            scope = {
                "type": "http",
                "method": "POST",
                "headers": raw_headers,
                "path": "/mcp",
                "query_string": b"",
                "root_path": "",
            }
            return StarletteRequest(scope)

        # Invalid origin with an allowlist
        req = _make_req({"origin": "https://evil.com"})
        result = _validate_origin(req, ["https://good.example.com"])
        assert result is not None
        assert result.status_code == 403

        # No allowlist configured + origin present -> reject
        result2 = _validate_origin(req, None)
        assert result2 is not None
        assert result2.status_code == 403

    def test_stateful_header_mismatch_returns_400(self) -> None:
        """Stateful session: MCP-Protocol-Version header mismatch -> 400."""
        from arcade_mcp_server.transports.http_session_manager import (
            _validate_protocol_version_header,
        )
        from starlette.requests import Request as StarletteRequest

        def _make_req(headers: dict[str, str]) -> StarletteRequest:
            raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
            scope = {
                "type": "http",
                "method": "POST",
                "headers": raw_headers,
                "path": "/mcp",
                "query_string": b"",
                "root_path": "",
            }
            return StarletteRequest(scope)

        # Simulate a session with negotiated version
        mock_session = Mock()
        mock_session.negotiated_version = "2025-06-18"

        req = _make_req({"mcp-protocol-version": "2025-11-25"})
        error, _ = _validate_protocol_version_header(req, session=mock_session)
        assert error is not None
        assert error.status_code == 400

    def test_stateless_header_required(self) -> None:
        """Stateless mode: MCP-Protocol-Version header is required (400 if absent)."""
        from arcade_mcp_server.transports.http_session_manager import (
            _validate_protocol_version_header,
        )
        from starlette.requests import Request as StarletteRequest

        def _make_req(headers: dict[str, str]) -> StarletteRequest:
            raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
            scope = {
                "type": "http",
                "method": "POST",
                "headers": raw_headers,
                "path": "/mcp",
                "query_string": b"",
                "root_path": "",
            }
            return StarletteRequest(scope)

        # No header in stateless mode -> 400
        req = _make_req({})
        error, _ = _validate_protocol_version_header(req, is_stateless=True)
        assert error is not None
        assert error.status_code == 400

    @pytest.mark.asyncio
    async def test_insufficient_scope_returns_403(self, mcp_server: MCPServer) -> None:
        """Tool call with valid token but insufficient scopes returns -32043 error
        with _transport.http_status=403."""
        owner = _make_resource_owner(
            "alice", scopes="some.other.scope"
        )

        session = _make_session(mcp_server)
        await _init_session(mcp_server, session, "2025-11-25", resource_owner=owner)

        # Call scoped_tool which requires files:read files:write
        resp = await mcp_server.handle_message(
            _call_tool_msg("TestToolkit.scoped_tool", {"text": "test"}, msg_id=5),
            session,
            resource_owner=owner,
        )
        assert resp is not None
        assert hasattr(resp, "error"), f"Expected error response, got: {resp}"
        error = resp.error
        assert error["code"] == INSUFFICIENT_SCOPE_ERROR_CODE
        assert error["data"]["_transport"]["http_status"] == 403
        assert set(error["data"]["required_scopes"]) == {"files:read", "files:write"}
