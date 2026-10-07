"""
Validation rules a tool author declares on a parameter must survive into the
input model that the catalog generates, and reach the executor.

Covers constraints (``Field(ge=...)``, bare ``annotated_types`` markers,
``StringConstraints``, constrained aliases like ``PositiveInt``, and
``= Field(...)`` defaults) and Pydantic validators. Field settings that affect
routing rather than validation (``alias``, ``exclude``) must not change the
published argument name or what the tool receives.

These rules are enforced on the generated input model only; they are not yet
carried into the published tool definition or MCP ``inputSchema``.
"""

import logging
from typing import Annotated, Optional

import pytest
from annotated_types import Ge
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ErrorKind
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool
from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PlainSerializer,
    PlainValidator,
    PositiveInt,
    Strict,
    StringConstraints,
    ValidationError,
    WrapSerializer,
    WrapValidator,
    conint,
)
from typing_extensions import TypedDict

SECRET = "sk-live-SUPERSECRET-9999"


def _require_odd(value: int) -> int:
    if value % 2 == 0:
        raise ValueError("Count must be odd")
    return value


def _raise_type_error(value: str) -> str:
    raise TypeError(f"cannot handle {value}")


class Window(TypedDict):
    start: int
    end: int


class Schedule(TypedDict):
    name: str
    window: Window


def _require_ordered(window: dict) -> dict:
    if window["start"] > window["end"]:
        raise ValueError("start must not be after end")
    return window


def _sort_window(window: dict) -> dict:
    low, high = sorted((window["start"], window["end"]))
    return {"start": low, "end": high}


def _require_non_empty(windows: list) -> list:
    if not all(isinstance(window, dict) for window in windows):
        raise ValueError("windows must be dicts")
    return windows


@tool
def bounded_count(value: Annotated[int, Field(ge=0, le=5), "Bounded count"]) -> int:
    """Return a count between 0 and 5."""
    return value


@tool
def optional_count(
    value: Annotated[Optional[int], Field(ge=0), "Optional count"] = None,
) -> int:
    """Return a non-negative count, or 0 when omitted."""
    return value or 0


@tool
def plain_count(value: Annotated[int, "Count"]) -> int:
    """Return a count."""
    return value


@tool
def strict_count(value: Annotated[int, Field(strict=True), "Strict count"]) -> int:
    """Return a count that must be sent as an integer."""
    return value


@tool
def short_code(value: Annotated[str, Field(max_length=3), "Short code"]) -> str:
    """Return a code of at most three characters."""
    return value


@tool
def odd_count(value: Annotated[int, AfterValidator(_require_odd), "Odd count"]) -> int:
    """Return an odd count."""
    return value


@tool
def failing_validator(value: Annotated[str, AfterValidator(_raise_type_error), "Value"]) -> str:
    """Return the value; its validator always raises TypeError."""
    return value


@tool
def ordered_window(value: Annotated[Window, AfterValidator(_require_ordered), "Window"]) -> int:
    """Return the window length."""
    return value["end"] - value["start"]


@tool
def sorted_window(value: Annotated[Window, AfterValidator(_sort_window), "Window"]) -> dict:
    """Return the window with its bounds sorted."""
    return dict(value)


@tool
def window_list(
    value: Annotated[list[Window], AfterValidator(_require_non_empty), "Windows"],
) -> int:
    """Return the number of windows."""
    return len(value)


catalog = ToolCatalog()
for fn in (
    bounded_count,
    optional_count,
    plain_count,
    strict_count,
    short_code,
    odd_count,
    failing_validator,
    ordered_window,
    sorted_window,
    window_list,
):
    catalog.add_tool(fn, "DeclaredValidation")


def _materialized(fn):
    td = catalog.find_tool_by_func(fn)
    return catalog.get_tool(td.get_fully_qualified_name())


def _probe(fn):
    """Register a tool in its own catalog and return the materialized tool."""
    local_catalog = ToolCatalog()
    local_catalog.add_tool(fn, "Probe")
    td = local_catalog.find_tool_by_func(fn)
    return local_catalog.get_tool(td.get_fully_qualified_name())


async def _run(fn, mt, **kwargs):
    return await ToolExecutor.run(
        func=fn,
        definition=mt.definition,
        input_model=mt.input_model,
        output_model=mt.output_model,
        context=ToolContext(),
        **kwargs,
    )


class TestFieldConstraintsEnforced:
    @pytest.mark.parametrize("value", [-1, 6])
    def test_out_of_range_value_rejected(self, value):
        mt = _materialized(bounded_count)
        with pytest.raises(ValidationError):
            mt.input_model(value=value)

    def test_in_range_value_accepted(self):
        mt = _materialized(bounded_count)
        assert mt.input_model(value=3).value == 3

    def test_bounds_present_on_internal_input_model(self):
        mt = _materialized(bounded_count)
        schema = mt.input_model.model_json_schema()["properties"]["value"]
        assert schema["minimum"] == 0
        assert schema["maximum"] == 5

    def test_optional_param_keeps_constraint_and_accepts_none(self):
        mt = _materialized(optional_count)
        assert mt.input_model().value is None
        assert mt.input_model(value=None).value is None
        assert mt.input_model(value=2).value == 2
        with pytest.raises(ValidationError):
            mt.input_model(value=-1)

    def test_string_length_constraint_enforced(self):
        mt = _materialized(short_code)
        assert mt.input_model(value="abc").value == "abc"
        with pytest.raises(ValidationError):
            mt.input_model(value="abcd")

    @pytest.mark.asyncio
    async def test_executor_surfaces_constraint_violation_as_bad_input(self):
        mt = _materialized(bounded_count)
        output = await _run(bounded_count, mt, value=6)
        assert output.error is not None
        assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE


class TestConstraintDeclarationForms:
    """Every way Pydantic lets an author declare a constraint is enforced."""

    def test_bare_annotated_types_marker(self):
        def probe(value: Annotated[int, Ge(0), "Count"]) -> int:
            """Probe."""
            return value

        mt = _probe(tool(probe))
        assert mt.input_model(value=0).value == 0
        with pytest.raises(ValidationError):
            mt.input_model(value=-1)

    def test_constrained_alias(self):
        def probe(value: Annotated[PositiveInt, "Count"]) -> int:
            """Probe."""
            return value

        mt = _probe(tool(probe))
        assert mt.input_model(value=1).value == 1
        with pytest.raises(ValidationError):
            mt.input_model(value=0)

    def test_conint(self):
        def probe(value: Annotated[conint(ge=0), "Count"]) -> int:  # type: ignore[valid-type]
            """Probe."""
            return value

        mt = _probe(tool(probe))
        with pytest.raises(ValidationError):
            mt.input_model(value=-1)

    def test_string_constraints(self):
        def probe(value: Annotated[str, StringConstraints(max_length=2), "Code"]) -> str:
            """Probe."""
            return value

        mt = _probe(tool(probe))
        assert mt.input_model(value="ab").value == "ab"
        with pytest.raises(ValidationError):
            mt.input_model(value="abc")

    def test_bare_strict_marker(self):
        def probe(value: Annotated[int, Strict(), "Count"]) -> int:
            """Probe."""
            return value

        mt = _probe(tool(probe))
        with pytest.raises(ValidationError):
            mt.input_model(value="5")

    def test_field_given_as_signature_default(self):
        def probe(value: Annotated[int, "Count"] = Field(3, ge=0)) -> int:
            """Probe."""
            return value

        mt = _probe(tool(probe))
        assert mt.input_model(value=1).value == 1
        with pytest.raises(ValidationError):
            mt.input_model(value=-1)


class TestMisappliedConstraintsDropped:
    """A constraint that does not apply to the parameter's type is dropped with a
    warning when the tool is registered, rather than failing every call."""

    def test_numeric_bound_on_string_is_dropped(self, caplog):
        def probe(value: Annotated[str, Field(gt=0), "Value"]) -> str:
            """Probe."""
            return value

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            mt = _probe(tool(probe))
        assert mt.input_model(value=SECRET).value == SECRET
        assert any("gt" in record.getMessage() for record in caplog.records)

    def test_applicable_constraint_beside_misapplied_one_is_kept(self, caplog):
        def probe(value: Annotated[str, Field(gt=0, max_length=3), "Value"]) -> str:
            """Probe."""
            return value

        with caplog.at_level(logging.WARNING, logger="arcade_core.catalog"):
            mt = _probe(tool(probe))
        assert mt.input_model(value="abc").value == "abc"
        with pytest.raises(ValidationError):
            mt.input_model(value="abcd")

    @pytest.mark.asyncio
    async def test_valid_call_succeeds_through_executor(self):
        def probe(value: Annotated[str, Field(gt=0), "Value"]) -> str:
            """Probe."""
            return value

        fn = tool(probe)
        mt = _probe(fn)
        output = await _run(fn, mt, value="anything")
        assert output.error is None
        assert output.value == "anything"


class TestIntegerCoercionUnchanged:
    """Keeping declared rules must not make integer inputs strict by default."""

    @pytest.mark.parametrize("value", ["3", 3.0])
    def test_plain_int_still_coerces_lossless_input(self, value):
        mt = _materialized(plain_count)
        assert mt.input_model(value=value).value == 3

    def test_bounded_int_coerces_then_checks_bounds(self):
        mt = _materialized(bounded_count)
        assert mt.input_model(value="3").value == 3
        with pytest.raises(ValidationError):
            mt.input_model(value="9")

    @pytest.mark.parametrize("value", ["1", 1.0, True])
    def test_declared_strict_rejects_non_integers(self, value):
        mt = _materialized(strict_count)
        with pytest.raises(ValidationError):
            mt.input_model(value=value)

    def test_declared_strict_accepts_integer(self):
        mt = _materialized(strict_count)
        assert mt.input_model(value=1).value == 1


class TestDeclaredValidatorsEnforced:
    @pytest.mark.asyncio
    async def test_after_validator_runs_in_executor(self):
        mt = _materialized(odd_count)
        rejected = await _run(odd_count, mt, value=2)
        assert rejected.error is not None
        assert rejected.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE

        accepted = await _run(odd_count, mt, value=3)
        assert accepted.error is None
        assert accepted.value == 3

    @pytest.mark.asyncio
    async def test_validator_message_reaches_agent_as_written(self):
        mt = _materialized(odd_count)
        output = await _run(odd_count, mt, value=2)
        assert "Count must be odd" in output.error.message

    @pytest.mark.asyncio
    async def test_validator_raising_other_exception_is_sanitized_bad_input(self):
        mt = _materialized(failing_validator)
        output = await _run(failing_validator, mt, value=SECRET)
        assert output.error is not None
        assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE
        assert "TypeError" in (output.error.developer_message or "")
        assert output.error.stacktrace is None
        assert SECRET not in output.model_dump_json()


class TestValidatorsOnTypedDictParams:
    """Validators on a TypedDict parameter see the dict the author declared,
    even though the catalog validates TypedDicts through a generated model."""

    @pytest.mark.asyncio
    async def test_validator_receives_dict_and_accepts_valid_input(self):
        mt = _materialized(ordered_window)
        output = await _run(ordered_window, mt, value={"start": 1, "end": 4})
        assert output.error is None
        assert output.value == 3

    @pytest.mark.asyncio
    async def test_validator_rejection_is_bad_input(self):
        mt = _materialized(ordered_window)
        output = await _run(ordered_window, mt, value={"start": 4, "end": 1})
        assert output.error is not None
        assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE
        assert "start must not be after end" in output.error.message

    @pytest.mark.asyncio
    async def test_validator_return_value_reaches_tool(self):
        mt = _materialized(sorted_window)
        output = await _run(sorted_window, mt, value={"start": 9, "end": 2})
        assert output.error is None
        assert output.value == {"start": 2, "end": 9}

    def test_validator_result_still_forbids_unknown_keys(self):
        mt = _materialized(ordered_window)
        with pytest.raises(ValidationError):
            mt.input_model(value={"start": 1, "end": 2, "extra": 3})

    @pytest.mark.asyncio
    async def test_validator_on_list_of_typeddicts_receives_dicts(self):
        mt = _materialized(window_list)
        output = await _run(window_list, mt, value=[{"start": 1, "end": 2}])
        assert output.error is None
        assert output.value == 1

    @pytest.mark.parametrize(
        "validator",
        [
            BeforeValidator(lambda window: window),
            PlainValidator(lambda window: window),
            WrapValidator(lambda window, handler: handler(window)),
        ],
        ids=["before", "plain", "wrap"],
    )
    @pytest.mark.asyncio
    async def test_other_validator_modes_keep_dict_contract(self, validator):
        def probe(value: Annotated[Window, validator, "Window"]) -> dict:
            """Probe."""
            assert isinstance(value, dict)
            return dict(value)

        fn = tool(probe)
        mt = _probe(fn)
        output = await _run(fn, mt, value={"start": 1, "end": 2})
        assert output.error is None
        assert output.value == {"start": 1, "end": 2}


class TestValidatorShapesOnTypedDictParams:
    @pytest.mark.parametrize(
        "validator",
        [
            AfterValidator(lambda window, info: window),
            PlainValidator(lambda window, info: window),
            WrapValidator(lambda window, handler, info: handler(window)),
        ],
        ids=["after", "plain", "wrap"],
    )
    @pytest.mark.asyncio
    async def test_validators_taking_info_receive_it(self, validator):
        def probe(value: Annotated[Window, validator, "Window"]) -> dict:
            """Probe."""
            return dict(value)

        fn = tool(probe)
        mt = _probe(fn)
        output = await _run(fn, mt, value={"start": 1, "end": 2})
        assert output.error is None
        assert output.value == {"start": 1, "end": 2}

    @pytest.mark.asyncio
    async def test_builtin_callable_as_validator(self):
        def probe(value: Annotated[Window, AfterValidator(dict), "Window"]) -> dict:
            """Probe."""
            return dict(value)

        fn = tool(probe)
        mt = _probe(fn)
        output = await _run(fn, mt, value={"start": 1, "end": 2})
        assert output.error is None
        assert output.value == {"start": 1, "end": 2}

    def test_constraint_on_list_of_nested_typeddicts(self):
        def probe(value: Annotated[list[Schedule], Field(max_length=1), "Schedules"]) -> int:
            """Probe."""
            return len(value)

        mt = _probe(tool(probe))
        schedule = {"name": "a", "window": {"start": 1, "end": 2}}
        assert len(mt.input_model(value=[schedule]).value) == 1
        with pytest.raises(ValidationError):
            mt.input_model(value=[schedule, schedule])


class TestRoutingSettingsIgnored:
    @pytest.mark.parametrize("field", [Field(alias="count", ge=0), Field(exclude=True, ge=0)])
    @pytest.mark.asyncio
    async def test_alias_and_exclude_do_not_change_published_argument(self, field):
        @tool
        def count(value: Annotated[int, field, "Count"]) -> int:
            """Return the count."""
            return value

        local_catalog = ToolCatalog()
        local_catalog.add_tool(count, "Probe")
        mt = local_catalog.get_tool_by_name("Probe_Count", separator="_")

        assert [p.name for p in mt.definition.input.parameters] == ["value"]
        result = await _run(count, mt, value=2)
        assert result.error is None
        assert result.value == 2
        with pytest.raises(ValidationError):
            mt.input_model(value=-1)

    @pytest.mark.parametrize("serializer_kind", ["plain", "wrap"])
    @pytest.mark.asyncio
    async def test_serializers_do_not_change_dispatched_value(self, serializer_kind):
        serializer = (
            PlainSerializer(str, return_type=str)
            if serializer_kind == "plain"
            else WrapSerializer(lambda value, handler: str(handler(value)), return_type=str)
        )

        @tool
        def kind(value: Annotated[int, serializer, "Count"]) -> str:
            """Return the type name of the received argument."""
            return type(value).__name__

        local_catalog = ToolCatalog()
        local_catalog.add_tool(kind, "Probe")
        mt = local_catalog.get_tool_by_name("Probe_Kind", separator="_")

        result = await _run(kind, mt, value=2)
        assert result.error is None
        assert result.value == "int"
