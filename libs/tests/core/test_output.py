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
