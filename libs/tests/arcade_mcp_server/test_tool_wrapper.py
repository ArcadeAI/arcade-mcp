"""Tests for the MCP-aware ``@tool`` wrapper in ``arcade_mcp_server.decorators``.

The wrapper exists to keep MCP-specific concepts (``execution`` /
``taskSupport``) out of ``arcade_tdk``. arcade-tdk stays protocol-agnostic;
this wrapper layers MCP semantics on top by writing ``__tool_execution__``
on the decorated callable and forwarding every other kwarg to
``arcade_tdk.tool``.
"""

from __future__ import annotations

import inspect

import pytest
from arcade_core.metadata import ToolMetadata
from arcade_tdk import tool as _arcade_tdk_tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import ToolRuntimeError

from arcade_mcp_server.decorators import tool
from arcade_mcp_server.types import ToolExecution


class TestBareAndParameterizedForms:
    def test_bare_form_decorates_function(self):
        @tool
        def my_tool() -> str:
            return "hello"

        assert callable(my_tool)
        assert my_tool.__tool_name__ == "MyTool"
        assert my_tool() == "hello"

    def test_parameterized_form_with_no_kwargs(self):
        @tool()
        def my_tool() -> str:
            return "hello"

        assert callable(my_tool)
        assert my_tool.__tool_name__ == "MyTool"
        assert my_tool() == "hello"


class TestKwargPassthrough:
    """Every arcade-tdk kwarg must reach the underlying decorator unchanged."""

    def test_passthrough_name(self):
        @tool(name="custom_name")
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_name__ == "custom_name"

    def test_passthrough_desc(self):
        @tool(desc="overridden description")
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_description__ == "overridden description"

    def test_passthrough_requires_auth(self):
        provider = OAuth2(id="my_auth", scopes=["scope_a"])

        @tool(requires_auth=provider)
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_requires_auth__ is provider

    def test_passthrough_requires_secrets(self):
        @tool(requires_secrets=["API_KEY", "OTHER"])
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_requires_secrets__ == ["API_KEY", "OTHER"]

    def test_passthrough_requires_metadata(self):
        @tool(requires_metadata=["tenant_id"])
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_requires_metadata__ == ["tenant_id"]

    def test_passthrough_metadata(self):
        meta = ToolMetadata(extras={"idp": "entraID"})

        @tool(metadata=meta)
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_metadata__ is meta


class TestExecutionKwarg:
    def test_execution_kwarg_sets_dunder(self):
        execution = ToolExecution(taskSupport="optional")

        @tool(execution=execution)
        def my_tool() -> str:
            return "x"

        assert my_tool.__tool_execution__ is execution

    def test_execution_dunder_is_none_when_kwarg_omitted(self):
        @tool
        def my_tool() -> str:
            return "x"

        # Behavior parity with arcade-tdk before this refactor: the
        # attribute exists and equals None when execution= is not passed.
        # Pinned so the wire-conversion path's ``getattr(..., None)``
        # contract continues to hold for tools registered without an
        # explicit task-augmentation policy.
        assert getattr(my_tool, "__tool_execution__", "<missing>") is None

    def test_execution_dunder_is_none_when_parameterized_form_omits_kwarg(self):
        @tool()
        def my_tool() -> str:
            return "x"

        assert getattr(my_tool, "__tool_execution__", "<missing>") is None

    def test_execution_kwarg_typed_as_tool_execution(self):
        sig = inspect.signature(tool)
        annotation = sig.parameters["execution"].annotation
        # The annotation should reference ToolExecution, NOT Any.
        # `inspect.signature` returns the annotation as-written, which
        # for ``ToolExecution | None`` resolves to a typing.Optional /
        # types.UnionType depending on Python version. The text form is
        # the durable contract we pin here.
        annotation_text = str(annotation)
        assert "ToolExecution" in annotation_text
        assert annotation_text != "typing.Any"

    def test_execution_dunder_survives_error_handler_wrap(self):
        execution = ToolExecution(taskSupport="required")

        @tool(execution=execution)
        def my_tool() -> str:
            raise ValueError("boom")

        # The returned callable is arcade-tdk's error-handler-wrapped
        # function. The dunder must be readable on that wrapper -- the
        # downstream ``getattr(materialized_tool.tool, "__tool_execution__",
        # None)`` reads from this exact object.
        assert my_tool.__tool_execution__ is execution

        with pytest.raises(ToolRuntimeError):
            my_tool()


class TestDeprecatedForwarding:
    def test_tool_deprecated_attribute_forwarded(self):
        # The wrapper exposes the same ``deprecated`` attribute object
        # that arcade-tdk hangs off its ``tool`` callable, so callers
        # can use ``@tool.deprecated("msg")`` via either import path.
        assert tool.deprecated is _arcade_tdk_tool.deprecated

    def test_deprecated_decorator_works_via_wrapper(self):
        @tool.deprecated("use my_new_tool instead")
        def my_old_tool() -> str:
            return "x"

        assert my_old_tool.__tool_deprecation_message__ == "use my_new_tool instead"


class TestSignatureMirror:
    def test_signature_mirrors_arcade_tdk_plus_execution(self):
        wrapper_params = set(inspect.signature(tool).parameters.keys())
        tdk_params = set(inspect.signature(_arcade_tdk_tool).parameters.keys())
        # Every arcade-tdk kwarg must be available on the wrapper.
        # arcade-tdk growing a new kwarg the wrapper does not mirror is
        # a real drift bug; this catches it.
        missing = tdk_params - wrapper_params
        assert missing == set(), (
            f"Wrapper missing arcade-tdk kwargs: {missing}. Mirror them in "
            f"arcade_mcp_server.decorators.tool."
        )
        # The wrapper must expose ``execution`` (its reason to exist).
        assert "execution" in wrapper_params
        # Beyond ``execution``, the wrapper must not silently add new
        # MCP-specific kwargs without a corresponding test asserting
        # the kwarg's behavior.
        unexpected_extras = wrapper_params - tdk_params - {"execution"}
        assert unexpected_extras == set(), (
            f"Wrapper has undocumented extra kwargs: {unexpected_extras}"
        )


class TestErrorHandlerNotDoubleWrapped:
    def test_wrapper_does_not_double_wrap_error_handler(self):
        # arcade-tdk's @tool wraps the function in an error adapter
        # chain that converts arbitrary exceptions to ToolRuntimeError.
        # If the wrapper accidentally re-decorated (e.g. by passing the
        # already-decorated callable back through arcade-tdk's tool a
        # second time), exceptions would be converted twice -- the
        # second pass would see the already-translated ToolRuntimeError
        # and short-circuit, but the cause chain would show a doubled
        # depth. We assert exactly one translation hop occurred.
        @tool
        def my_tool() -> str:
            raise ValueError("boom")

        with pytest.raises(ToolRuntimeError) as exc_info:
            my_tool()

        # Single translation: the caught ToolRuntimeError's __cause__ is
        # the original ValueError, not another ToolRuntimeError.
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "boom"


class TestRelocatedFromArcadeTdk:
    """Tests originally at libs/tests/sdk/test_tool_decorator.py:215-242,
    relocated to live alongside the MCP-typed wrapper that owns the
    ``execution`` kwarg. arcade-tdk no longer accepts ``execution=``;
    these tests now exercise the same contract through the wrapper.
    """

    def test_tool_without_execution_defaults_none(self):
        @tool
        def my_tool() -> str:
            return "hello"

        assert getattr(my_tool, "__tool_execution__", None) is None

    def test_tool_with_execution_parameter(self):
        execution = ToolExecution(taskSupport="optional")

        @tool(execution=execution)
        def my_tool() -> str:
            return "hello"

        assert my_tool.__tool_execution__ is execution

    @pytest.mark.parametrize(
        "task_support",
        ["optional", "required", "forbidden"],
    )
    def test_tool_with_execution_parametrized(self, task_support):
        execution = ToolExecution(taskSupport=task_support)

        @tool(execution=execution)
        def my_tool() -> str:
            return "hello"

        assert my_tool.__tool_execution__.taskSupport == task_support
