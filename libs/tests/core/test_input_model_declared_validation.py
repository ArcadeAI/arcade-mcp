"""
Validation rules a tool author declares on a parameter must survive into the
input model that the catalog generates, and reach the executor.

Covers ``Field`` constraints (``ge``, ``le``, ``max_length``, ``strict``) and
Pydantic validators carried in the parameter's ``Annotated`` metadata. Field
settings that affect routing rather than validation (``alias``, ``exclude``)
must not change the published argument name or what the tool receives.
"""

from typing import Annotated, Optional

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ErrorKind
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool
from pydantic import AfterValidator, Field, PlainSerializer, ValidationError, WrapSerializer


def _require_odd(value: int) -> int:
    if value % 2 == 0:
        raise ValueError("Count must be odd")
    return value


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


catalog = ToolCatalog()
for fn in (bounded_count, optional_count, plain_count, strict_count, short_code, odd_count):
    catalog.add_tool(fn, "DeclaredValidation")


def _materialized(fn):
    td = catalog.find_tool_by_func(fn)
    return catalog.get_tool(td.get_fully_qualified_name())


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

    def test_bounds_rendered_in_input_schema(self):
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
