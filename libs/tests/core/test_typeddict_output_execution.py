"""
End-to-end tests for TypedDict output execution through the entire tool pipeline.
"""

from typing import Annotated, Optional

import pytest
from arcade_core.catalog import ToolCatalog, create_func_models
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool
from typing_extensions import TypedDict


# Define various TypedDict structures for testing
class SimpleDict(TypedDict):
    """A simple typed dictionary."""

    name: str
    value: int


class NestedDict(TypedDict):
    """A nested typed dictionary."""

    id: int
    info: SimpleDict
    tags: list[str]


class OptionalFieldsDict(TypedDict, total=False):
    """TypedDict with optional fields."""

    required_field: str
    optional_field: int


# Define test tools
@tool
def returns_typeddict() -> Annotated[SimpleDict, "Returns a simple TypedDict"]:
    """Tool that returns a TypedDict."""
    return SimpleDict(name="test", value=42)


@tool
def returns_list_of_typeddict() -> Annotated[list[SimpleDict], "Returns list of TypedDict"]:
    """Tool that returns a list of TypedDict."""
    return [
        SimpleDict(name="item1", value=1),
        SimpleDict(name="item2", value=2),
        SimpleDict(name="item3", value=3),
    ]


@tool
def returns_optional_typeddict(
    return_none: Annotated[bool, "Whether to return None"] = False,
) -> Annotated[Optional[SimpleDict], "Returns optional TypedDict"]:
    """Tool that returns an optional TypedDict."""
    if return_none:
        return None
    return SimpleDict(name="optional", value=100)


@tool
def returns_nested_typeddict() -> Annotated[NestedDict, "Returns nested TypedDict"]:
    """Tool that returns a nested TypedDict."""
    return NestedDict(id=1, info=SimpleDict(name="nested", value=99), tags=["tag1", "tag2", "tag3"])


@tool
def accepts_and_returns_typeddict(
    data: Annotated[SimpleDict, "Input TypedDict"],
) -> Annotated[SimpleDict, "Modified TypedDict"]:
    """Tool that accepts and returns a TypedDict."""
    return SimpleDict(name=f"Modified: {data['name']}", value=data["value"] * 2)


@tool
def returns_dict_list() -> Annotated[list[dict], "Returns list of dicts"]:
    """Tool that returns a list of dictionaries including TypedDicts."""
    return [
        {"type": "plain", "value": 42},
        {"name": "string", "data": "test"},
        SimpleDict(name="typed", value=99),
    ]


class MixedRequiredDict(TypedDict):
    """Base TypedDict with required fields."""

    name: str


class MixedOptionalDict(MixedRequiredDict, total=False):
    """TypedDict with both required and optional fields."""

    optional_field: str


@tool
def returns_partial_optional_typeddict() -> Annotated[
    OptionalFieldsDict, "Returns partial optional TypedDict"
]:
    """Tool that returns a TypedDict with some fields omitted."""
    return {"required_field": "hello"}  # optional_field intentionally omitted


@tool
def returns_mixed_typeddict() -> Annotated[MixedOptionalDict, "Returns mixed TypedDict"]:
    """Tool that returns a TypedDict with required + optional fields, omitting optional."""
    return {"name": "hello"}  # optional_field intentionally omitted


class TestTypeDictOutputExecution:
    """Test TypedDict outputs through the full execution pipeline."""

    @pytest.fixture
    def catalog(self):
        return ToolCatalog()

    @pytest.fixture
    def context(self):
        return ToolContext()

    @pytest.mark.asyncio
    async def test_returns_typeddict(self, catalog, context):
        """Test executing a tool that returns a TypedDict."""
        # Create tool definition
        definition = catalog.create_tool_definition(
            returns_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )

        # Create models
        input_model, output_model = create_func_models(returns_typeddict)

        # Execute tool
        result = await ToolExecutor.run(
            func=returns_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        # Verify result
        assert result.error is None
        assert result.value == {"name": "test", "value": 42}

    @pytest.mark.asyncio
    async def test_returns_list_of_typeddict(self, catalog, context):
        """Test executing a tool that returns a list of TypedDict."""
        definition = catalog.create_tool_definition(
            returns_list_of_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )

        input_model, output_model = create_func_models(returns_list_of_typeddict)

        result = await ToolExecutor.run(
            func=returns_list_of_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        assert result.value == [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
            {"name": "item3", "value": 3},
        ]

    @pytest.mark.asyncio
    async def test_returns_optional_typeddict(self, catalog, context):
        """Test executing a tool that returns an optional TypedDict."""
        definition = catalog.create_tool_definition(
            returns_optional_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )

        input_model, output_model = create_func_models(returns_optional_typeddict)

        # Test returning a value
        result = await ToolExecutor.run(
            func=returns_optional_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
            return_none=False,
        )

        assert result.error is None
        assert result.value == {"name": "optional", "value": 100}

        # Test returning None
        result_none = await ToolExecutor.run(
            func=returns_optional_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
            return_none=True,
        )

        assert result_none.error is None
        assert result_none.value == ""  # None is converted to empty string

    @pytest.mark.asyncio
    async def test_returns_nested_typeddict(self, catalog, context):
        """Test executing a tool that returns a nested TypedDict."""
        definition = catalog.create_tool_definition(
            returns_nested_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )

        input_model, output_model = create_func_models(returns_nested_typeddict)

        result = await ToolExecutor.run(
            func=returns_nested_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        assert result.value == {
            "id": 1,
            "info": {"name": "nested", "value": 99},
            "tags": ["tag1", "tag2", "tag3"],
        }

    @pytest.mark.asyncio
    async def test_accepts_and_returns_typeddict(self, catalog, context):
        """Test executing a tool that accepts and returns TypedDict."""
        definition = catalog.create_tool_definition(
            accepts_and_returns_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )

        input_model, output_model = create_func_models(accepts_and_returns_typeddict)

        result = await ToolExecutor.run(
            func=accepts_and_returns_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
            data={"name": "input", "value": 21},
        )

        assert result.error is None
        assert result.value == {"name": "Modified: input", "value": 42}

    @pytest.mark.asyncio
    async def test_returns_dict_list(self, catalog, context):
        """Test executing a tool that returns a list of dicts."""
        definition = catalog.create_tool_definition(
            returns_dict_list, toolkit_name="test", toolkit_version="1.0.0"
        )

        input_model, output_model = create_func_models(returns_dict_list)

        result = await ToolExecutor.run(
            func=returns_dict_list,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        assert result.value == [
            {"type": "plain", "value": 42},
            {"name": "string", "data": "test"},
            {"name": "typed", "value": 99},  # TypedDict becomes regular dict at runtime
        ]

    @pytest.mark.asyncio
    async def test_total_false_typeddict_omits_absent_fields(self, catalog, context):
        """When a total=False TypedDict omits a field, it must not appear as None in output.

        Reproduces: model_dump() without exclude_none reintroduces None for absent
        optional fields, which then fails JSON Schema validation against the outputSchema
        (the schema declares "type": "string", not ["string", "null"]).
        """
        definition = catalog.create_tool_definition(
            returns_partial_optional_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )
        input_model, output_model = create_func_models(returns_partial_optional_typeddict)

        result = await ToolExecutor.run(
            func=returns_partial_optional_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        # The absent optional field must NOT be present with a None value
        assert result.value == {"required_field": "hello"}
        assert "optional_field" not in result.value

    @pytest.mark.asyncio
    async def test_mixed_required_optional_typeddict_omits_absent_fields(self, catalog, context):
        """A TypedDict inheriting required fields + total=False optional fields.

        When the tool omits the optional field, the output must contain only the
        required field. None values for absent optional fields corrupt the MCP
        structuredContent because they don't match the schema type.
        """
        definition = catalog.create_tool_definition(
            returns_mixed_typeddict, toolkit_name="test", toolkit_version="1.0.0"
        )
        input_model, output_model = create_func_models(returns_mixed_typeddict)

        result = await ToolExecutor.run(
            func=returns_mixed_typeddict,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        assert result.value == {"name": "hello"}
        assert "optional_field" not in result.value

    @pytest.mark.asyncio
    async def test_exclude_unset_omits_absent_but_keeps_explicit_none(self, catalog, context):
        """TypedDict with total=False absent field AND total=True str|None field set to None.

        The absent field must be excluded, but the explicitly-set None must be kept.
        This validates exclude_unset (not exclude_none) semantics.
        """

        class _Required(TypedDict):
            name: str
            note: str | None  # total=True, explicitly nullable

        class _WithOptional(_Required, total=False):
            tag: str  # total=False, will be absent

        @tool
        def returns_mixed_nullable() -> Annotated[_WithOptional, "Mixed nullable output"]:
            """Tool with both nullable required and absent optional fields."""
            return {"name": "hello", "note": None}  # tag intentionally absent

        definition = catalog.create_tool_definition(
            returns_mixed_nullable, toolkit_name="test", toolkit_version="1.0.0"
        )
        input_model, output_model = create_func_models(returns_mixed_nullable)

        result = await ToolExecutor.run(
            func=returns_mixed_nullable,
            definition=definition,
            input_model=input_model,
            output_model=output_model,
            context=context,
        )

        assert result.error is None
        # Explicit None must be kept (exclude_unset preserves it)
        assert result.value == {"name": "hello", "note": None}
        # Absent total=False field must NOT appear
        assert "tag" not in result.value
