import logging
from typing import Any

import pytest
from arcade_core import output as output_module
from arcade_core.output import ToolOutputFactory
from pydantic import BaseModel

_LEAK_MAGIC = "yes-i-accept-leaking-internals-to-the-agent"
_ENV_DEV_MSG = "ARCADE_DEBUG_EXPOSE_DEVELOPER_MESSAGE_IN_TOOL_ERROR_RESPONSES"
_ENV_STACKTRACE = "ARCADE_DEBUG_EXPOSE_STACKTRACE_IN_TOOL_ERROR_RESPONSES"


@pytest.fixture(autouse=True)
def _reset_leak_warn_state(monkeypatch):
    """Clear the per-process one-shot warning state so each test starts clean.

    The debug-leak flags emit a loud warning on first activation per process,
    and a separate warning when a truthy-but-non-magic value is rejected. Both
    are one-shot per flag. Without a reset, later tests in this module would
    silently lose coverage of either branch because the module-level tracking
    sets are already populated from earlier tests.
    """
    monkeypatch.delenv(_ENV_DEV_MSG, raising=False)
    monkeypatch.delenv(_ENV_STACKTRACE, raising=False)
    output_module._warned_rejected.clear()
    output_module._warned_activated.clear()
    yield
    output_module._warned_rejected.clear()
    output_module._warned_activated.clear()


@pytest.fixture
def output_factory():
    return ToolOutputFactory()


class SampleOutputModel(BaseModel):
    result: Any


@pytest.mark.parametrize(
    "data, expected_value",
    [
        (None, ""),
        ("success", "success"),
        ("", ""),
        (None, ""),
        (123, 123),
        (0, 0),
        (123.45, 123.45),
        (True, True),
        (False, False),
    ],
)
def test_success(output_factory, data, expected_value):
    data_obj = SampleOutputModel(result=data) if data is not None else None
    output = output_factory.success(data=data_obj)
    assert output.value == expected_value
    assert output.error is None


@pytest.mark.parametrize(
    "data, expected_value",
    [
        # Dict types (simulating TypedDict at runtime)
        ({"name": "test", "value": 123}, {"name": "test", "value": 123}),
        ({}, {}),
        ({"nested": {"key": "value"}}, {"nested": {"key": "value"}}),
        # List types
        (["a", "b", "c"], ["a", "b", "c"]),
        ([1, 2, 3], [1, 2, 3]),
        ([], []),
        # List of dicts (simulating list[TypedDict])
        (
            [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
            [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
        ),
        ([{}], [{}]),
        # Mixed lists
        ([1, "two", 3.0, True], [1, "two", 3.0, True]),
    ],
)
def test_success_complex_types(output_factory, data, expected_value):
    """Test that dict and list types are properly handled by ToolOutputFactory."""
    data_obj = SampleOutputModel(result=data)
    output = output_factory.success(data=data_obj)
    assert output.value == expected_value
    assert output.error is None


def test_success_with_basemodel_direct(output_factory):
    """Test that BaseModel instances are converted to dict via model_dump()."""

    class TestModel(BaseModel):
        name: str
        value: int

    model = TestModel(name="test", value=42)
    output = output_factory.success(data=model)
    assert output.value == {"name": "test", "value": 42}
    assert output.error is None


def test_success_raw_dict(output_factory):
    """Test that raw dict values (not wrapped in model) are handled correctly."""
    raw_dict = {"key": "value", "number": 123}
    output = output_factory.success(data=raw_dict)
    assert output.value == raw_dict
    assert output.error is None


def test_success_raw_list(output_factory):
    """Test that raw list values (not wrapped in model) are handled correctly."""
    raw_list = [{"id": 1}, {"id": 2}, {"id": 3}]
    output = output_factory.success(data=raw_list)
    assert output.value == raw_list
    assert output.error is None


@pytest.mark.parametrize(
    "message, developer_message",
    [
        ("Error occurred", None),
        ("Error occurred", "Detailed error message"),
    ],
)
def test_fail(output_factory, message, developer_message):
    output = output_factory.fail(message=message, developer_message=developer_message)
    assert output.error is not None
    assert output.error.message == message
    assert output.error.developer_message == developer_message
    assert output.error.can_retry is False


def test_fail_empty_message_gets_default(output_factory):
    output = output_factory.fail(message="")
    assert output.error is not None
    assert output.error.message == "Unspecified error during tool execution"


def test_fail_whitespace_message_gets_default(output_factory):
    output = output_factory.fail(message="  ")
    assert output.error is not None
    assert output.error.message == "Unspecified error during tool execution"


def test_fail_nonempty_message_unchanged(output_factory):
    output = output_factory.fail(message="real error")
    assert output.error is not None
    assert output.error.message == "real error"


def test_fail_retry_empty_message_gets_default(output_factory):
    output = output_factory.fail_retry(message="")
    assert output.error is not None
    assert output.error.message == "Unspecified error during tool execution"


def test_fail_retry_whitespace_message_gets_default(output_factory):
    output = output_factory.fail_retry(message="   ")
    assert output.error is not None
    assert output.error.message == "Unspecified error during tool execution"


@pytest.mark.parametrize(
    "message, developer_message, additional_prompt_content, retry_after_ms",
    [
        ("Retry error", None, None, None),
        ("Retry error", "Retrying", "Please try again with this additional data: foobar", 1000),
    ],
)
def test_fail_retry(
    output_factory, message, developer_message, additional_prompt_content, retry_after_ms
):
    output = output_factory.fail_retry(
        message=message,
        developer_message=developer_message,
        additional_prompt_content=additional_prompt_content,
        retry_after_ms=retry_after_ms,
    )
    assert output.error is not None
    assert output.error.message == message
    assert output.error.developer_message == developer_message
    assert output.error.can_retry is True
    assert output.error.additional_prompt_content == additional_prompt_content
    assert output.error.retry_after_ms == retry_after_ms


# --- Debug-leak flag tests ----------------------------------------------------


def test_fail_no_leak_by_default(output_factory):
    """With both flags unset, message must not be augmented."""
    output = output_factory.fail(
        message="public error",
        developer_message="secret internals",
        stacktrace="Traceback...\n  line",
    )
    assert output.error is not None
    assert output.error.message == "public error"
    assert output.error.developer_message == "secret internals"
    assert output.error.stacktrace == "Traceback...\n  line"


@pytest.mark.parametrize("bad_value", ["true", "1", "yes", "on", "TRUE", "True"])
def test_fail_rejects_boolean_activation(output_factory, monkeypatch, caplog, bad_value):
    """Any truthy-looking value that isn't the magic string must be rejected."""
    monkeypatch.setenv(_ENV_DEV_MSG, bad_value)
    with caplog.at_level(logging.WARNING, logger="arcade_core.output"):
        output = output_factory.fail(
            message="public error",
            developer_message="secret internals",
        )
    assert output.error is not None
    assert output.error.message == "public error"
    assert any(
        "set to a truthy value but not to the required" in rec.message for rec in caplog.records
    )


def test_fail_rejects_random_non_magic_value(output_factory, monkeypatch, caplog):
    """A non-boolean-looking value that isn't the magic string is silently off."""
    monkeypatch.setenv(_ENV_DEV_MSG, "debug-please")
    with caplog.at_level(logging.WARNING, logger="arcade_core.output"):
        output = output_factory.fail(
            message="public error",
            developer_message="secret internals",
        )
    assert output.error is not None
    assert output.error.message == "public error"
    # No "truthy but not magic" warning for non-bool-looking values.
    assert not any(
        "set to a truthy value but not to the required" in rec.message for rec in caplog.records
    )


def test_fail_developer_message_flag_enabled(output_factory, monkeypatch, caplog):
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    with caplog.at_level(logging.WARNING, logger="arcade_core.output"):
        output = output_factory.fail(
            message="public error",
            developer_message="secret internals",
            stacktrace="trace",
        )
    assert output.error is not None
    assert "public error" in output.error.message
    assert "[DEBUG] developer_message: secret internals" in output.error.message
    # Stacktrace flag is off → stacktrace must NOT be in the message.
    assert "trace" not in output.error.message.replace("public error", "")
    # developer_message field is preserved regardless.
    assert output.error.developer_message == "secret internals"
    assert any("is ENABLED" in rec.message for rec in caplog.records)


def test_fail_stacktrace_flag_enabled(output_factory, monkeypatch):
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    output = output_factory.fail(
        message="public error",
        developer_message="secret internals",
        stacktrace="Traceback (most recent call last):\n  File ...",
    )
    assert output.error is not None
    assert "public error" in output.error.message
    assert "[DEBUG] stacktrace:" in output.error.message
    assert "File ..." in output.error.message
    # Developer-message flag off → dev message must NOT leak into message.
    assert "secret internals" not in output.error.message


def test_fail_both_flags_enabled(output_factory, monkeypatch):
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    output = output_factory.fail(
        message="public error",
        developer_message="dev info",
        stacktrace="trace info",
    )
    assert output.error is not None
    assert "[DEBUG] developer_message: dev info" in output.error.message
    assert "[DEBUG] stacktrace:\ntrace info" in output.error.message


def test_fail_flag_enabled_but_no_content_to_leak(output_factory, monkeypatch):
    """Flag on but developer_message/stacktrace are None → message unchanged."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    monkeypatch.setenv(_ENV_STACKTRACE, _LEAK_MAGIC)
    output = output_factory.fail(message="public error")
    assert output.error is not None
    assert output.error.message == "public error"


def test_fail_activation_warning_emitted_once_per_process(output_factory, monkeypatch, caplog):
    """Second call with the flag on must NOT emit another activation warning."""
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    with caplog.at_level(logging.WARNING, logger="arcade_core.output"):
        output_factory.fail(message="a", developer_message="dev")
        first_count = sum("is ENABLED" in r.message for r in caplog.records)
        output_factory.fail(message="b", developer_message="dev")
        second_count = sum("is ENABLED" in r.message for r in caplog.records)
    assert first_count == 1
    assert second_count == 1  # still one — one-shot per process.


def test_fail_rejection_does_not_suppress_later_activation_warning(
    output_factory, monkeypatch, caplog
):
    """Regression: once a truthy-but-non-magic value has been rejected for a
    flag, correcting the value to the magic string within the same process
    must still emit the critical "ENABLED ... DO NOT USE IN PRODUCTION"
    warning. Previously both paths shared one state set, so the activation
    warning was silently swallowed in this scenario.
    """
    with caplog.at_level(logging.WARNING, logger="arcade_core.output"):
        # 1. Misconfigure with a truthy value → rejection warning fires, flag OFF.
        monkeypatch.setenv(_ENV_DEV_MSG, "true")
        out_rejected = output_factory.fail(
            message="public error",
            developer_message="secret internals",
        )
        assert out_rejected.error is not None
        assert "[DEBUG]" not in out_rejected.error.message
        rejection_count = sum(
            "set to a truthy value but not to the required" in r.message
            for r in caplog.records
        )
        assert rejection_count == 1

        # 2. Correct to the magic string → activation warning MUST fire.
        monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
        out_activated = output_factory.fail(
            message="public error",
            developer_message="secret internals",
        )
        assert out_activated.error is not None
        assert "[DEBUG] developer_message: secret internals" in out_activated.error.message
        activation_count = sum("is ENABLED" in r.message for r in caplog.records)
        assert activation_count == 1, (
            "activation warning must fire even after the rejection warning "
            "has already been emitted for the same flag in this process"
        )


def test_fail_retry_honors_developer_message_flag(output_factory, monkeypatch):
    monkeypatch.setenv(_ENV_DEV_MSG, _LEAK_MAGIC)
    output = output_factory.fail_retry(
        message="retry error",
        developer_message="retry internals",
    )
    assert output.error is not None
    assert "[DEBUG] developer_message: retry internals" in output.error.message
    assert output.error.can_retry is True


def test_fail_magic_value_ignores_surrounding_whitespace(output_factory, monkeypatch):
    """Leading/trailing whitespace around the magic string still activates the flag."""
    monkeypatch.setenv(_ENV_DEV_MSG, f"  {_LEAK_MAGIC}  ")
    output = output_factory.fail(
        message="public error",
        developer_message="secret internals",
    )
    assert output.error is not None
    assert "[DEBUG] developer_message: secret internals" in output.error.message
