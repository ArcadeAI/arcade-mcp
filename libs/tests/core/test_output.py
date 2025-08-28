from typing import Any

import pytest
from arcade_core.output import ToolOutputFactory
from pydantic import BaseModel


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
