"""Rejected tool inputs are reported as structured ``input_errors``: a declared
parameter and a reason code from the closed ``InputErrorReason`` set, so
consumers such as the Arcade Engine need not parse ``developer_message``."""

from typing import Annotated, Any

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import (
    ErrorKind,
    InputErrorDetail,
    InputErrorReason,
    ToolInputError,
)
from arcade_core.executor import ToolExecutor, _input_error_reason
from arcade_core.schema import ToolCallOutput, ToolContext
from arcade_tdk import tool
from pydantic import Field, field_validator


@tool
def send_mail(
    to: Annotated[str, "Recipient"],
    cc: Annotated[list[str], "CC recipients"],
    limit: Annotated[int, "Max results"] = 10,
) -> Annotated[str, "Result"]:
    """Send mail."""
    return "ok"


@tool
def sum_list(numbers: Annotated[list[int], "Numbers"]) -> Annotated[int, "Sum"]:
    """Sum numbers."""
    return sum(numbers)


@tool
def bounded(
    count: Annotated[int, Field(ge=1, le=5), "Count"],
    code: Annotated[str, Field(pattern=r"^[A-Z]+$"), "Code"],
) -> Annotated[int, "Count"]:
    """Bounded inputs."""
    return count


class _Boom(Exception):
    pass


@tool
def validated(value: Annotated[str, "Value"]) -> Annotated[str, "Value"]:
    """Tool whose input model gets a custom validator below."""
    return value


catalog = ToolCatalog()
for _func in (send_mail, sum_list, bounded, validated):
    catalog.add_tool(_func, "test_toolkit")


async def _run(func: Any, **inputs: Any) -> ToolCallOutput:
    definition = catalog.find_tool_by_func(func)
    full_tool = catalog.get_tool(definition.get_fully_qualified_name())
    return await ToolExecutor.run(
        func=func,
        definition=definition,
        input_model=full_tool.input_model,
        output_model=full_tool.output_model,
        context=ToolContext(),
        **inputs,
    )


def _details(output: ToolCallOutput) -> list[InputErrorDetail] | None:
    assert output.error is not None
    assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE
    return output.error.input_errors


@pytest.mark.asyncio
async def test_reports_each_rejected_parameter_with_reason():
    output = await _run(send_mail, to="a@example.com", cc="jane@example.com", limit="ten")
    assert _details(output) == [
        InputErrorDetail(parameter="cc", reason=InputErrorReason.EXPECTED_ARRAY),
        InputErrorDetail(parameter="limit", reason=InputErrorReason.EXPECTED_INTEGER),
    ]


@pytest.mark.asyncio
async def test_missing_parameter():
    output = await _run(send_mail, cc=[])
    assert _details(output) == [
        InputErrorDetail(parameter="to", reason=InputErrorReason.MISSING),
    ]


@pytest.mark.asyncio
async def test_undeclared_key_is_reported_without_its_name():
    output = await _run(send_mail, to="a", cc=[], jane_doe_ssn="123")
    details = _details(output)
    assert details == [InputErrorDetail(parameter=None, reason=InputErrorReason.UNEXPECTED)]
    assert "jane_doe_ssn" not in output.model_dump_json(include={"error": {"input_errors"}})


@pytest.mark.asyncio
async def test_nested_failures_collapse_to_one_entry_per_parameter_and_reason():
    output = await _run(sum_list, numbers=["a", 2, "b", "c"])
    assert _details(output) == [
        InputErrorDetail(
            parameter="numbers", reason=InputErrorReason.EXPECTED_INTEGER, nested=True
        ),
    ]


@pytest.mark.asyncio
async def test_declared_constraints_map_to_reasons():
    output = await _run(bounded, count=9, code="abc")
    assert _details(output) == [
        InputErrorDetail(parameter="count", reason=InputErrorReason.OUT_OF_RANGE),
        InputErrorDetail(parameter="code", reason=InputErrorReason.PATTERN_MISMATCH),
    ]


@pytest.mark.asyncio
async def test_input_errors_carry_no_input_values():
    output = await _run(send_mail, to="a", cc="jane@example.com", limit="secret-token")
    wire = output.model_dump_json(include={"error": {"input_errors"}})
    assert "jane@example.com" not in wire
    assert "secret-token" not in wire


@pytest.mark.asyncio
async def test_worker_payload_serializes_input_errors():
    output = await _run(send_mail, to="a", cc="x")
    payload = output.model_dump(mode="json")
    assert payload["error"]["input_errors"] == [
        {"parameter": "cc", "reason": "expected_array", "nested": False}
    ]


@pytest.mark.asyncio
async def test_valid_inputs_have_no_error():
    output = await _run(send_mail, to="a", cc=["b"])
    assert output.error is None


@pytest.mark.asyncio
async def test_validator_raising_unexpected_exception_reports_validator_failed():
    definition = catalog.find_tool_by_func(validated)
    full_tool = catalog.get_tool(definition.get_fully_qualified_name())

    class Model(full_tool.input_model):  # type: ignore[name-defined,misc]
        @field_validator("value")
        @classmethod
        def _explode(cls, v: str) -> str:
            raise _Boom(v)

    output = await ToolExecutor.run(
        func=validated,
        definition=definition,
        input_model=Model,
        output_model=full_tool.output_model,
        context=ToolContext(),
        value="x",
    )
    assert _details(output) == [InputErrorDetail(reason=InputErrorReason.VALIDATOR_FAILED)]


@pytest.mark.parametrize(
    ("pydantic_type", "reason"),
    [
        ("missing", InputErrorReason.MISSING),
        ("extra_forbidden", InputErrorReason.UNEXPECTED),
        ("string_type", InputErrorReason.EXPECTED_STRING),
        ("int_parsing", InputErrorReason.EXPECTED_INTEGER),
        ("float_parsing", InputErrorReason.EXPECTED_NUMBER),
        ("bool_parsing", InputErrorReason.EXPECTED_BOOLEAN),
        ("list_type", InputErrorReason.EXPECTED_ARRAY),
        ("dict_type", InputErrorReason.EXPECTED_OBJECT),
        ("model_type", InputErrorReason.EXPECTED_OBJECT),
        ("literal_error", InputErrorReason.NOT_ALLOWED),
        ("enum", InputErrorReason.NOT_ALLOWED),
        ("string_too_short", InputErrorReason.TOO_SHORT),
        ("too_long", InputErrorReason.TOO_LONG),
        ("greater_than_equal", InputErrorReason.OUT_OF_RANGE),
        ("string_pattern_mismatch", InputErrorReason.PATTERN_MISMATCH),
        ("datetime_parsing", InputErrorReason.INVALID_FORMAT),
        ("uuid_parsing", InputErrorReason.INVALID_FORMAT),
        ("url_scheme", InputErrorReason.INVALID_FORMAT),
        ("value_error", InputErrorReason.VALIDATOR_FAILED),
        ("assertion_error", InputErrorReason.VALIDATOR_FAILED),
        ("some_future_code", InputErrorReason.INVALID),
    ],
)
def test_pydantic_codes_map_onto_closed_set(pydantic_type, reason):
    assert _input_error_reason(pydantic_type) is reason


def test_tool_input_error_payload_includes_input_errors():
    err = ToolInputError(
        "Invalid input",
        input_errors=[InputErrorDetail(parameter="cc", reason=InputErrorReason.EXPECTED_ARRAY)],
    )
    assert err.to_payload()["input_errors"] == [
        {"parameter": "cc", "reason": "expected_array", "nested": False}
    ]
    assert "input_errors" not in ToolInputError("Invalid input").to_payload()
