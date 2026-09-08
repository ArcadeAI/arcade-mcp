"""A tool definition's ``_meta`` must serialize exactly as it goes on the wire.

The alias is the wire contract: a caller decodes ``_meta``, so a value emitted
under the Python name, or dropped between a dump and a validate, is a break.
"""

from arcade_core.schema import (
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
)

POINTER = {"ui": {"resourceUri": "ui://Math/0.1.0/sum-list.html"}}


def _definition(**overrides) -> ToolDefinition:
    fields = {
        "name": "SumList",
        "fully_qualified_name": "Math.SumList",
        "description": "Sum a list of numbers",
        "toolkit": ToolkitDefinition(name="Math", version="0.1.0"),
        "input": ToolInput(parameters=[]),
        "output": ToolOutput(),
        "requirements": ToolRequirements(),
    }
    fields.update(overrides)
    return ToolDefinition(**fields)


def test_meta_serializes_under_the_underscore_key():
    dumped = _definition(meta=POINTER).model_dump(by_alias=True, exclude_none=True)

    assert dumped["_meta"] == POINTER
    assert "meta" not in dumped


def test_meta_is_read_from_the_underscore_key():
    definition = ToolDefinition.model_validate({
        **_definition().model_dump(exclude_none=True),
        "_meta": POINTER,
    })

    assert definition.meta == POINTER


def test_meta_survives_a_dump_and_validate_round_trip():
    """``model_dump()`` emits the Python name, so validation has to accept it too."""
    definition = _definition(meta=POINTER)

    round_tripped = ToolDefinition.model_validate(definition.model_dump())

    assert round_tripped.meta == POINTER


def test_meta_is_absent_until_something_sets_it():
    definition = _definition()

    dumped = definition.model_dump(by_alias=True, exclude_none=True)

    assert definition.meta is None
    assert "_meta" not in dumped
    assert "meta" not in dumped
