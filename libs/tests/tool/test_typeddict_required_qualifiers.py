"""TypedDict fields marked Required or NotRequired load, with the requiredness they declare."""

import typing
from typing import Annotated

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog
from arcade_core.schema import ValueSchema
from arcade_tdk import tool
from pydantic import ValidationError
from typing_extensions import NotRequired, Required, TypedDict


class Address(TypedDict):
    city: str


class Attachment(TypedDict):
    source: str
    """URI locating the file's bytes."""

    filename: NotRequired[str]
    """Display filename the recipient sees."""

    nickname: NotRequired[str | None]

    sender_address: NotRequired[Address]


class Filter(TypedDict, total=False):
    key: Required[str]
    """The field to filter on."""

    value: str


@tool
def func_takes_qualified_typeddicts(
    attachment: Annotated[Attachment, "The file to attach"],
    filter: Annotated[Filter, "The filter to apply"],
) -> str:
    """Attach a file that matches a filter."""
    return "attached"


class EventResult(TypedDict):
    event_id: str
    location: NotRequired[str]


@tool
def func_returns_event_without_location() -> Annotated[EventResult, "The event"]:
    """Return an event with no location."""
    return EventResult(event_id="event-1")


class StdlibAttachment(typing.TypedDict):
    source: str
    filename: NotRequired[str]


class StdlibFilter(typing.TypedDict, total=False):
    key: Required[str]
    value: str


@tool
def func_takes_stdlib_typeddicts(
    attachment: Annotated[StdlibAttachment, "The file to attach"],
    filter: Annotated[StdlibFilter, "The filter to apply"],
) -> str:
    """Attach a file that matches a filter."""
    return "attached"


catalog = ToolCatalog()
catalog.add_tool(func_takes_qualified_typeddicts, "QualifierToolkit")
catalog.add_tool(func_returns_event_without_location, "QualifierToolkit")
catalog.add_tool(func_takes_stdlib_typeddicts, "QualifierToolkit")


def _materialized(fn) -> MaterializedTool:
    tool_def = catalog.find_tool_by_func(fn)
    return catalog.get_tool(tool_def.get_fully_qualified_name())


def test_qualified_fields_get_the_requiredness_and_description_they_declare():
    tool_def = ToolCatalog.create_tool_definition(func_takes_qualified_typeddicts, "1.0")
    attachment, filter_ = (param.value_schema for param in tool_def.input.parameters)

    assert attachment.required_keys == ["source"]
    assert attachment.properties is not None
    assert attachment.properties["filename"] == ValueSchema(
        val_type="string", description="Display filename the recipient sees."
    )
    assert attachment.properties["nickname"] == ValueSchema(val_type="string", nullable=True)
    assert attachment.properties["sender_address"] == ValueSchema(
        val_type="json",
        properties={"city": ValueSchema(val_type="string")},
        required_keys=["city"],
    )
    assert filter_.required_keys == ["key"]
    assert filter_.properties is not None
    assert filter_.properties["key"] == ValueSchema(
        val_type="string", description="The field to filter on."
    )


def test_not_required_field_may_be_left_out_of_the_input():
    input_model = _materialized(func_takes_qualified_typeddicts).input_model

    validated = input_model.model_validate({
        "attachment": {"source": "file:///tmp/report.pdf", "sender_address": {"city": "Oslo"}},
        "filter": {"key": "status"},
    })

    assert validated.model_dump()["attachment"] == {
        "source": "file:///tmp/report.pdf",
        "sender_address": {"city": "Oslo"},
    }


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(
            {"attachment": {"filename": "report.pdf"}, "filter": {"key": "status"}},
            id="missing_required_key",
        ),
        pytest.param(
            {"attachment": {"source": "file:///tmp/report.pdf"}, "filter": {"value": "open"}},
            id="missing_key_marked_required_in_total_false_class",
        ),
    ],
)
def test_required_key_left_out_of_the_input_is_refused(arguments):
    input_model = _materialized(func_takes_qualified_typeddicts).input_model

    with pytest.raises(ValidationError):
        input_model.model_validate(arguments)


def test_stdlib_typeddict_gets_the_requiredness_its_qualifiers_declare():
    """typing.TypedDict on Python 3.10 leaves both qualifiers out of __required_keys__."""
    tool_def = ToolCatalog.create_tool_definition(func_takes_stdlib_typeddicts, "1.0")
    attachment, filter_ = (param.value_schema for param in tool_def.input.parameters)

    assert attachment.required_keys == ["source"]
    assert filter_.required_keys == ["key"]

    input_model = _materialized(func_takes_stdlib_typeddicts).input_model
    input_model.model_validate({
        "attachment": {"source": "file:///tmp/report.pdf"},
        "filter": {"key": "status"},
    })
    with pytest.raises(ValidationError):
        input_model.model_validate({
            "attachment": {"source": "file:///tmp/report.pdf"},
            "filter": {"value": "open"},
        })


def test_output_with_not_required_field_left_out_validates():
    materialized = _materialized(func_returns_event_without_location)

    assert materialized.definition.output.value_schema.required_keys == ["event_id"]
    output = materialized.output_model.model_validate({"result": {"event_id": "event-1"}})
    assert output.model_dump()["result"] == {"event_id": "event-1"}
