"""Tests for the actionable guidance attached to invalid-tool-input errors.

An input validation failure used to state only what was wrong ("age: Input
should be a valid integer") without saying what the tool actually expects, so
the caller had to go re-read the schema to self-correct. These tests pin the
appended "Expected:" block, and — just as importantly — pin that it is built
from the tool's *declared schema* and never from the rejected values, which may
contain secrets or PII.
"""

from typing import Annotated, Literal, Optional

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.executor import ToolExecutor, _expected_shape_guidance
from arcade_core.schema import ToolContext
from arcade_tdk import tool

catalog = ToolCatalog()


@tool
def weather_tool(
    city: Annotated[str, "The city to look up"],
    units: Annotated[Optional[Literal["c", "f"]], "Temperature units"] = "c",
    days: Annotated[Optional[int], "Number of forecast days"] = 1,
) -> Annotated[str, "forecast"]:
    """Look up a forecast."""
    return f"{city} {units} {days}"


@tool
def tags_tool(
    tags: Annotated[list[str], "A list of tags"],
) -> Annotated[str, "output"]:
    """Tool taking a list."""
    return ",".join(tags)


catalog.add_tool(weather_tool, "GuidanceToolkit")
catalog.add_tool(tags_tool, "GuidanceToolkit")


async def _run(func, **kwargs):
    definition = catalog.find_tool_by_func(func)
    materialized = catalog.get_tool(definition.get_fully_qualified_name())
    return await ToolExecutor.run(
        func=func,
        definition=definition,
        input_model=materialized.input_model,
        output_model=materialized.output_model,
        context=ToolContext(),
        **kwargs,
    )


class TestExpectedShapeGuidance:
    @pytest.mark.asyncio
    async def test_missing_required_field_reports_expected_shape(self):
        output = await _run(weather_tool)  # omit required 'city'

        assert output.error is not None
        msg = output.error.message
        # The existing "what went wrong" half is preserved.
        assert "Invalid input:" in msg
        assert "city" in msg
        # The new "what is expected" half.
        assert "Expected:" in msg
        assert "string" in msg
        assert "required" in msg

    @pytest.mark.asyncio
    async def test_guidance_includes_parameter_description(self):
        output = await _run(weather_tool)

        assert output.error is not None
        assert "The city to look up" in output.error.message

    @pytest.mark.asyncio
    async def test_guidance_lists_allowed_values_for_enums(self):
        output = await _run(weather_tool, city="Paris", units="kelvin")

        assert output.error is not None
        msg = output.error.message
        assert "units" in msg
        # The closed set is the single most actionable fact for an enum.
        assert "c" in msg and "f" in msg

    @pytest.mark.asyncio
    async def test_guidance_describes_only_rejected_fields(self):
        """The client already has the full schema from tools/list; repeating it
        on every failure is noise. Only the fields that were actually rejected
        get described."""
        output = await _run(weather_tool, city="Paris", days="not-an-int")

        assert output.error is not None
        msg = output.error.message
        assert "days" in msg
        # 'city' validated fine, so it must not appear in the Expected block.
        expected_block = msg.split("Expected:", 1)[1]
        assert "city" not in expected_block

    @pytest.mark.asyncio
    async def test_guidance_renders_array_element_type(self):
        output = await _run(tags_tool, tags="not-a-list")

        assert output.error is not None
        msg = output.error.message
        assert "tags" in msg
        assert "array" in msg

    @pytest.mark.asyncio
    async def test_guidance_tells_the_caller_what_to_do_next(self):
        output = await _run(weather_tool)

        assert output.error is not None
        assert "call the tool again" in output.error.message.lower()


class TestGuidanceNeverLeaksInputValues:
    """The guidance is built from the declared schema, so adding it must not
    reintroduce the value-echo that the executor deliberately avoids."""

    @pytest.mark.asyncio
    async def test_rejected_values_absent_from_message_and_developer_message(self):
        sentinel = "SENTINEL_TOKEN_DO_NOT_LEAK_99"
        output = await _run(weather_tool, city=sentinel, days=sentinel)

        assert output.error is not None
        assert sentinel not in output.error.message
        assert output.error.developer_message is not None
        assert sentinel not in output.error.developer_message

    @pytest.mark.asyncio
    async def test_enum_guidance_does_not_echo_the_rejected_value(self):
        sentinel = "SENTINEL_UNIT_VALUE_77"
        output = await _run(weather_tool, city="Paris", units=sentinel)

        assert output.error is not None
        assert sentinel not in output.error.message


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_message_still_starts_with_invalid_input_summary(self):
        """Callers (and existing tests) match on the leading
        ``Invalid input: <field>: <reason>`` summary; guidance is appended
        after it, never spliced into it."""
        output = await _run(tags_tool, tags="not-a-list")

        assert output.error is not None
        head = output.error.message.split("Expected:", 1)[0]
        assert "Invalid input: tags:" in head

    @pytest.mark.asyncio
    async def test_developer_message_shape_unchanged(self):
        output = await _run(tags_tool, tags="not-a-list")

        assert output.error is not None
        assert output.error.developer_message is not None
        assert "Pydantic validation failed:" in output.error.developer_message

    @pytest.mark.asyncio
    async def test_no_definition_degrades_gracefully(self):
        """``_serialize_input`` must still work without a definition (it is an
        optional enrichment, not a new requirement)."""
        definition = catalog.find_tool_by_func(tags_tool)
        materialized = catalog.get_tool(definition.get_fully_qualified_name())

        from arcade_core.errors import ToolInputError

        with pytest.raises(ToolInputError) as exc_info:
            await ToolExecutor._serialize_input(materialized.input_model, tags="not-a-list")

        assert "Invalid input: tags:" in str(exc_info.value)


class TestGuidanceHelperDegradesQuietly:
    """The helper is best-effort: when it cannot describe anything it returns an
    empty string so callers can append unconditionally, rather than raising and
    turning a validation error into a crash."""

    def test_no_definition_returns_empty(self):
        assert _expected_shape_guidance(None, ["city"]) == ""

    def test_no_rejected_fields_returns_empty(self):
        definition = catalog.find_tool_by_func(weather_tool)
        assert _expected_shape_guidance(definition, []) == ""

    def test_definition_without_parameters_returns_empty(self):
        """A definition whose ``input`` does not expose ``parameters`` (a
        partially-built or foreign definition) must not raise."""

        class _NoParams:
            input = object()

        assert _expected_shape_guidance(_NoParams(), ["city"]) == ""

    def test_unknown_rejected_field_is_skipped(self):
        """An extra argument that maps to no declared parameter has no shape to
        describe; the declared ones are still reported."""
        definition = catalog.find_tool_by_func(weather_tool)
        guidance = _expected_shape_guidance(definition, ["not_a_parameter", "city"])

        assert "city" in guidance
        assert "not_a_parameter" not in guidance

    def test_only_unknown_fields_returns_empty(self):
        definition = catalog.find_tool_by_func(weather_tool)
        assert _expected_shape_guidance(definition, ["nope", "also_nope"]) == ""


class TestModelLevelValidationErrors:
    @pytest.mark.asyncio
    async def test_error_without_a_field_location_is_handled(self):
        """Model-level validators report an empty ``loc``. That maps onto no
        single parameter, so it must be skipped when collecting rejected field
        names instead of indexing off the end."""
        from pydantic import BaseModel, model_validator

        from arcade_core.errors import ToolInputError

        class _WholeModelRejects(BaseModel):
            value: str = "ok"

            @model_validator(mode="after")
            def _always_fails(self):
                raise ValueError("the whole model is unacceptable")

        with pytest.raises(ToolInputError) as exc_info:
            await ToolExecutor._serialize_input(_WholeModelRejects, None, value="x")

        message = str(exc_info.value)
        assert "Invalid input:" in message
        # No parameter could be named, so no Expected block is appended.
        assert "Expected:" not in message
