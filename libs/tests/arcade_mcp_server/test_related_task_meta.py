"""Tests for io.modelcontextprotocol/related-task _meta injection on outbound
requests and notifications originating from background task execution.

Covers the deviations previously noted:
- ProgressNotificationParams._meta wire injection (progress notifications)
- Context.task_id auto-forwarding into outbound sampling/elicitation _meta

All task-related outbound requests/notifications MUST include
io.modelcontextprotocol/related-task in their _meta field.
"""

from __future__ import annotations

from typing import Any

import pytest
from arcade_mcp_server.context import Context
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import (
    ClientCapabilities,
    CreateMessageResult,
    ElicitResult,
    ProgressNotification,
    ProgressNotificationParams,
    TextContent,
)

RELATED_TASK_META_KEY = "io.modelcontextprotocol/related-task"


# -----------------------------------------------------------------------------
# Types: verify _meta field on progress / sampling / elicit params round-trips
# -----------------------------------------------------------------------------


class TestProgressNotificationMetaField:
    """ProgressNotificationParams gains _meta (2025-11-25 schema.ts:586).

    Backward-compatible: unused in 2025-06-18 (omitted via exclude_none).
    """

    def test_progress_notification_params_accepts_meta(self) -> None:
        params = ProgressNotificationParams(
            progressToken="tok",
            progress=0.5,
            meta={RELATED_TASK_META_KEY: {"taskId": "t-1"}},
        )
        dumped = params.model_dump(by_alias=True, exclude_none=True)
        assert dumped["_meta"][RELATED_TASK_META_KEY]["taskId"] == "t-1"

    def test_progress_notification_params_roundtrip(self) -> None:
        params = ProgressNotificationParams.model_validate({
            "progressToken": 1,
            "progress": 0.25,
            "_meta": {RELATED_TASK_META_KEY: {"taskId": "t-2"}},
        })
        assert params.meta is not None
        assert params.meta[RELATED_TASK_META_KEY]["taskId"] == "t-2"

    def test_progress_notification_params_meta_omitted_when_none(self) -> None:
        params = ProgressNotificationParams(progressToken="tok", progress=0.5)
        dumped = params.model_dump(by_alias=True, exclude_none=True)
        assert "_meta" not in dumped

    def test_progress_notification_serializes_meta_onto_wire(self) -> None:
        notif = ProgressNotification(
            params=ProgressNotificationParams(
                progressToken="tok",
                progress=1.0,
                meta={RELATED_TASK_META_KEY: {"taskId": "task-xyz"}},
            )
        )
        wire = notif.model_dump(by_alias=True, exclude_none=True)
        assert wire["params"]["_meta"][RELATED_TASK_META_KEY]["taskId"] == "task-xyz"


# -----------------------------------------------------------------------------
# Session: outbound create_message / elicit attach _meta
# -----------------------------------------------------------------------------


class _FakeRequestManager:
    """Captures send_request calls for inspection."""

    def __init__(self, fake_response: dict[str, Any]) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None, float]] = []
        self._response = fake_response

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None,
        timeout: float,
    ) -> Any:
        self.calls.append((method, params, timeout))
        return self._response


def _make_session_with_fake_manager(
    fake_response: dict[str, Any],
) -> tuple[ServerSession, _FakeRequestManager]:
    session = ServerSession.__new__(ServerSession)
    session._closed = object()  # type: ignore[attr-defined]
    session.negotiated_version = "2025-11-25"
    session._client_capabilities = ClientCapabilities(sampling={}, elicitation={"form": {}})
    session.initialization_state = __import__(
        "arcade_mcp_server.session", fromlist=["InitializationState"]
    ).InitializationState.INITIALIZED
    fake = _FakeRequestManager(fake_response)
    session._request_manager = fake  # type: ignore[assignment]
    return session, fake


class TestSessionForwardsMetaOnOutboundRequests:
    @pytest.mark.asyncio
    async def test_create_message_attaches_meta(self) -> None:
        session, fake = _make_session_with_fake_manager(
            {"role": "assistant", "content": {"type": "text", "text": "ok"}, "model": "m"}
        )
        meta = {RELATED_TASK_META_KEY: {"taskId": "task-42"}}
        await session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
            max_tokens=8,
            _meta=meta,
        )
        assert len(fake.calls) == 1
        method, params, _ = fake.calls[0]
        assert method == "sampling/createMessage"
        assert params is not None
        assert params["_meta"][RELATED_TASK_META_KEY]["taskId"] == "task-42"

    @pytest.mark.asyncio
    async def test_create_message_without_meta_does_not_attach_meta(self) -> None:
        session, fake = _make_session_with_fake_manager(
            {"role": "assistant", "content": {"type": "text", "text": "ok"}, "model": "m"}
        )
        await session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": "hi"}}],
            max_tokens=8,
        )
        _, params, _ = fake.calls[0]
        assert params is not None
        assert "_meta" not in params

    @pytest.mark.asyncio
    async def test_elicit_attaches_meta(self) -> None:
        session, fake = _make_session_with_fake_manager(
            {"action": "accept", "content": {"name": "alice"}}
        )
        meta = {RELATED_TASK_META_KEY: {"taskId": "task-99"}}
        await session.elicit(
            message="Enter",
            requested_schema={"type": "object", "properties": {}},
            _meta=meta,
        )
        assert len(fake.calls) == 1
        method, params, _ = fake.calls[0]
        assert method == "elicitation/create"
        assert params is not None
        assert params["_meta"][RELATED_TASK_META_KEY]["taskId"] == "task-99"

    @pytest.mark.asyncio
    async def test_elicit_without_meta_does_not_attach_meta(self) -> None:
        session, fake = _make_session_with_fake_manager(
            {"action": "accept", "content": {}}
        )
        await session.elicit(
            message="Enter", requested_schema={"type": "object", "properties": {}}
        )
        _, params, _ = fake.calls[0]
        assert params is not None
        assert "_meta" not in params


# -----------------------------------------------------------------------------
# Context layer: auto-injection of related-task _meta when task_id is set
# -----------------------------------------------------------------------------


class TestContextAutoInjectsRelatedTaskMeta:
    """Verifies that Context.sampling.create_message and Context.ui.elicit
    auto-inject io.modelcontextprotocol/related-task _meta when running
    inside a task context (task_id set on Context)."""

    @pytest.mark.asyncio
    async def test_sampling_in_task_context_injects_related_task_meta(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._client_capabilities = ClientCapabilities(sampling={})
        initialized_server_session.check_client_capability = lambda cap: True  # type: ignore[method-assign]

        captured: dict[str, Any] = {}

        async def fake_create_message(*, _meta=None, **kwargs):
            captured["_meta"] = _meta
            return CreateMessageResult(
                role="assistant",
                content=TextContent(type="text", text="ok"),
                model="test-model",
            )

        initialized_server_session.create_message = fake_create_message  # type: ignore[method-assign]

        ctx = Context(
            server=mcp_server,
            session=initialized_server_session,
            task_id="task-sampling-1",
        )

        await ctx.sampling.create_message(messages=[{"role": "user", "content": "hi"}])

        assert captured["_meta"] is not None
        assert (
            captured["_meta"][RELATED_TASK_META_KEY]["taskId"] == "task-sampling-1"
        )

    @pytest.mark.asyncio
    async def test_sampling_without_task_context_does_not_inject_meta(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._client_capabilities = ClientCapabilities(sampling={})
        initialized_server_session.check_client_capability = lambda cap: True  # type: ignore[method-assign]

        captured: dict[str, Any] = {}

        async def fake_create_message(*, _meta=None, **kwargs):
            captured["_meta"] = _meta
            return CreateMessageResult(
                role="assistant",
                content=TextContent(type="text", text="ok"),
                model="test-model",
            )

        initialized_server_session.create_message = fake_create_message  # type: ignore[method-assign]

        ctx = Context(server=mcp_server, session=initialized_server_session)

        await ctx.sampling.create_message(messages=[{"role": "user", "content": "hi"}])

        assert captured["_meta"] is None

    @pytest.mark.asyncio
    async def test_elicit_in_task_context_injects_related_task_meta(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._client_capabilities = ClientCapabilities(
            elicitation={"form": {}}
        )

        captured: dict[str, Any] = {}

        async def fake_elicit(*, _meta=None, **kwargs):
            captured["_meta"] = _meta
            return ElicitResult(action="accept", content={})

        initialized_server_session.elicit = fake_elicit  # type: ignore[method-assign]

        ctx = Context(
            server=mcp_server,
            session=initialized_server_session,
            task_id="task-elicit-1",
        )

        await ctx.ui.elicit(
            "Enter value",
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )

        assert captured["_meta"] is not None
        assert captured["_meta"][RELATED_TASK_META_KEY]["taskId"] == "task-elicit-1"

    @pytest.mark.asyncio
    async def test_elicit_without_task_context_does_not_inject_meta(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"
        initialized_server_session._client_capabilities = ClientCapabilities(
            elicitation={"form": {}}
        )

        captured: dict[str, Any] = {}

        async def fake_elicit(*, _meta=None, **kwargs):
            captured["_meta"] = _meta
            return ElicitResult(action="accept", content={})

        initialized_server_session.elicit = fake_elicit  # type: ignore[method-assign]

        ctx = Context(server=mcp_server, session=initialized_server_session)

        await ctx.ui.elicit(
            "Enter value",
            schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )

        assert captured["_meta"] is None


# -----------------------------------------------------------------------------
# Progress notifications: verify Progress.report sends _meta on wire
# -----------------------------------------------------------------------------


class TestProgressReportOnWireIncludesRelatedTaskMeta:
    """Progress.report must include io.modelcontextprotocol/related-task in the
    notification's _meta on the wire when running inside a task context."""

    @pytest.mark.asyncio
    async def test_progress_report_in_task_context_writes_meta_to_wire(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"

        sent: list[str] = []

        async def fake_send(msg: str) -> None:
            sent.append(msg)

        initialized_server_session.write_stream = type(
            "W", (), {"send": staticmethod(fake_send)}
        )()

        from arcade_mcp_server.managers.task_manager import TaskManager
        from arcade_mcp_server.request_context import reset_request_meta, set_request_meta

        tm = TaskManager()
        task = await tm.create_task(context_key="session:test", ttl=60000)
        tok = set_request_meta({"progressToken": "p-1"})
        try:
            ctx = Context(
                server=mcp_server,
                session=initialized_server_session,
                task_id=task.taskId,
                task_manager=tm,
            )
            await ctx.progress.report(progress=0.5, total=1.0, message="halfway")
        finally:
            reset_request_meta(tok)

        assert len(sent) == 1
        import json

        payload = json.loads(sent[0])
        assert payload["method"] == "notifications/progress"
        assert (
            payload["params"]["_meta"][RELATED_TASK_META_KEY]["taskId"]
            == task.taskId
        )
        assert payload["params"]["progressToken"] == "p-1"

    @pytest.mark.asyncio
    async def test_progress_report_outside_task_context_omits_meta(
        self, mcp_server, initialized_server_session
    ) -> None:
        initialized_server_session.negotiated_version = "2025-11-25"

        sent: list[str] = []

        async def fake_send(msg: str) -> None:
            sent.append(msg)

        initialized_server_session.write_stream = type(
            "W", (), {"send": staticmethod(fake_send)}
        )()

        from arcade_mcp_server.request_context import reset_request_meta, set_request_meta

        tok = set_request_meta({"progressToken": "p-2"})
        try:
            ctx = Context(server=mcp_server, session=initialized_server_session)
            await ctx.progress.report(progress=0.5)
        finally:
            reset_request_meta(tok)

        assert len(sent) == 1
        import json

        payload = json.loads(sent[0])
        assert payload["method"] == "notifications/progress"
        # When no task_id is set, _meta must not carry related-task
        meta = payload["params"].get("_meta") or {}
        assert RELATED_TASK_META_KEY not in meta
