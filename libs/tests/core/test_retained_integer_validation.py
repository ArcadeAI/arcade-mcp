from typing import Annotated

import pytest
from arcade_core.catalog import create_func_models
from pydantic import Field, ValidationError
from typing_extensions import TypedDict


def strict_count(value: Annotated[int, Field(strict=True, ge=0, le=5), "Bounded count"]) -> int:
    return value


class Reminder(TypedDict):
    minutes: int


def reminders(values: Annotated[list[Reminder], "Reminder minutes"]) -> int:
    return len(values)


@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 6])
def test_parameter_integer_constraints_survive_catalog_model(value):
    model, _ = create_func_models(strict_count)
    with pytest.raises(ValidationError):
        model(value=value)


@pytest.mark.parametrize("value", [True, "1", 1.0])
def test_nested_integer_input_does_not_coerce(value):
    model, _ = create_func_models(reminders)
    with pytest.raises(ValidationError):
        model(values=[{"minutes": value}])


def test_integer_control_and_rendered_bounds():
    model, _ = create_func_models(strict_count)
    assert model(value=3).value == 3
    schema = model.model_json_schema()["properties"]["value"]
    assert schema["minimum"] == 0 and schema["maximum"] == 5


@pytest.mark.parametrize("field", [Field(alias="count", ge=0), Field(exclude=True, ge=0)])
def test_validation_metadata_preserves_published_argument_routing(field):
    import asyncio

    from arcade_core.catalog import ToolCatalog
    from arcade_core.executor import ToolExecutor
    from arcade_core.schema import ToolContext
    from arcade_tdk import tool

    @tool
    def count(value: Annotated[int, field, "Count"]) -> int:
        """Return the published count."""
        return value

    catalog = ToolCatalog()
    catalog.add_tool(count, "Probe")
    entry = catalog.get_tool_by_name("Probe_Count", separator="_")
    result = asyncio.run(
        ToolExecutor.run(
            entry.tool,
            entry.definition,
            entry.input_model,
            entry.output_model,
            ToolContext(),
            value=2,
        )
    )
    assert [parameter.name for parameter in entry.definition.input.parameters] == ["value"]
    assert result.error is None and result.value == 2
    with pytest.raises(ValidationError):
        entry.input_model(value=-1)


@pytest.mark.parametrize("serializer_kind", ["plain", "wrap"])
def test_input_serializers_do_not_change_dispatched_integer(serializer_kind):
    import asyncio

    from arcade_core.catalog import ToolCatalog
    from arcade_core.executor import ToolExecutor
    from arcade_core.schema import ToolContext
    from arcade_tdk import tool
    from pydantic import PlainSerializer, WrapSerializer

    serializer = (
        PlainSerializer(str, return_type=str)
        if serializer_kind == "plain"
        else WrapSerializer(lambda value, handler: str(handler(value)), return_type=str)
    )

    @tool
    def kind(value: Annotated[int, serializer, "Count"]) -> str:
        """Observe the validated argument type."""
        return type(value).__name__

    catalog = ToolCatalog()
    catalog.add_tool(kind, "Probe")
    entry = catalog.get_tool_by_name("Probe_Kind", separator="_")
    result = asyncio.run(
        ToolExecutor.run(
            entry.tool,
            entry.definition,
            entry.input_model,
            entry.output_model,
            ToolContext(),
            value=2,
        )
    )
    assert result.error is None and result.value == "int"
