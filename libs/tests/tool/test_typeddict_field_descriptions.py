"""A TypedDict field's docstring becomes its description in the tool schema."""

from collections.abc import Callable
from typing import Annotated, Literal

from arcade_core.catalog import ToolCatalog
from arcade_core.schema import ValueSchema
from arcade_tdk import tool
from typing_extensions import TypedDict


def _input_schema(func: Callable) -> ValueSchema:
    tool_def = ToolCatalog.create_tool_definition(func, "1.0")
    return tool_def.input.parameters[0].value_schema


def _descriptions(schema: ValueSchema) -> dict[str, str | None]:
    assert schema.properties is not None
    return {name: prop.description for name, prop in schema.properties.items()}


class AttachmentWithClassDocstring(TypedDict, total=False):
    """A file to attach.

    ``filename`` and ``mime_type`` default to what the ``data:`` URI says.
    """

    filename: str
    """Display filename the recipient sees."""

    mime_type: str
    """Media type in type/subtype form."""


@tool
def func_takes_attachment_with_class_docstring(
    attachment: Annotated[AttachmentWithClassDocstring, "The file to attach"],
) -> str:
    """Attach a file."""
    return "attached"


def test_class_docstring_does_not_swallow_the_first_field():
    """A class docstring whose last line holds ``word:`` leaves the next field described."""
    assert _descriptions(_input_schema(func_takes_attachment_with_class_docstring)) == {
        "filename": "Display filename the recipient sees.",
        "mime_type": "Media type in type/subtype form.",
    }


class _AttachmentRequired(TypedDict):
    source: str
    """URI locating the file's bytes."""


class Attachment(_AttachmentRequired, total=False):
    filename: str
    """Display filename the recipient sees."""


@tool
def func_takes_attachment(attachment: Annotated[Attachment, "The file to attach"]) -> str:
    """Attach a file."""
    return "attached"


def test_inherited_input_field_keeps_its_docstring():
    schema = _input_schema(func_takes_attachment)

    assert _descriptions(schema) == {
        "source": "URI locating the file's bytes.",
        "filename": "Display filename the recipient sees.",
    }
    assert schema.required_keys == ["source"]


class _EventOptional(TypedDict, total=False):
    location: str
    """Where the event takes place, when it has a location."""


class Event(_EventOptional):
    event_id: str
    """The event's unique identifier."""


@tool
def func_returns_event() -> Annotated[Event, "The event"]:
    """Return an event."""
    return Event(event_id="event-1")


def test_output_schema_describes_only_fields_its_own_class_declares():
    tool_def = ToolCatalog.create_tool_definition(func_returns_event, "1.0")

    assert _descriptions(tool_def.output.value_schema) == {
        "location": None,
        "event_id": "The event's unique identifier.",
    }


class MimeType(TypedDict):
    mime_type: str
    """Media type in type/subtype form.

    Omitting it derives the type from the file.
    """


@tool
def func_takes_mime_type(value: Annotated[MimeType, "The media type"]) -> str:
    """Take a media type."""
    return "taken"


def test_multiline_docstring_is_dedented():
    assert _descriptions(_input_schema(func_takes_mime_type)) == {
        "mime_type": "Media type in type/subtype form.\n\nOmitting it derives the type from the file.",
    }


class Source(TypedDict):
    kind: Literal["file", "link"]
    """What the "source" field points at."""


@tool
def func_takes_source(value: Annotated[Source, "The source"]) -> str:
    """Take a source."""
    return "taken"


def test_docstring_with_double_quotes_on_a_literal_field():
    assert _descriptions(_input_schema(func_takes_source)) == {
        "kind": 'What the "source" field points at.',
    }


class PartlyDocumented(TypedDict):
    undocumented: str
    documented: str
    """Only this field has a docstring."""


@tool
def func_takes_partly_documented(value: Annotated[PartlyDocumented, "The value"]) -> str:
    """Take a value."""
    return "taken"


def test_docstring_describes_only_the_field_above_it():
    assert _descriptions(_input_schema(func_takes_partly_documented)) == {
        "undocumented": None,
        "documented": "Only this field has a docstring.",
    }
