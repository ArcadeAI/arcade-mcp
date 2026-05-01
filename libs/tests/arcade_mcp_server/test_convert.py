"""Tests for MCP content conversion utilities."""

import base64
import json
from typing import Annotated

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.schema import (
    InputParameter,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)
from arcade_mcp_server import tool
from arcade_mcp_server.convert import (
    convert_content_to_structured_content,
    convert_to_mcp_content,
    create_mcp_tool,
)
from arcade_mcp_server.types import ToolExecution

# Small PNG header (1x1 transparent pixel) used for byte-image param tests
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"


class TestConvertToMCPContent:
    """Test convert_to_mcp_content function."""

    @pytest.mark.parametrize(
        "value, expect_empty, decode_b64, expect_text",
        [
            ("Hello, world!", False, False, "Hello, world!"),
            (42, False, False, "42"),
            (3.14159, False, False, "3.14159"),
            (1234567890, False, False, "1234567890"),
            (True, False, False, "True"),
            (False, False, False, "False"),
            ("single", False, False, None),  # covers list wrapping behavior
            ("Hello\nWorld\t🌍", False, False, "Hello\nWorld\t🌍"),
            ("", False, False, ""),
            (b"Hello, binary world!", False, True, None),
            (PNG_BYTES, False, True, None),
            (None, True, False, None),
            ({}, False, False, "{}"),
            ([], False, False, "[]"),
        ],
    )
    def test_convert_primitives_and_bytes(self, value, expect_empty, decode_b64, expect_text):
        """Parameterize primitives/bytes/empties/special cases."""
        result = convert_to_mcp_content(value)

        if expect_empty:
            assert result == []
            return

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        text = result[0].text

        if decode_b64:
            decoded = base64.b64decode(text)
            assert decoded == value

        if expect_text is not None:
            assert text == expect_text

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "Alice", "age": 30, "active": True},
            [1, 2, "three", {"four": 4}],
            {
                "users": [
                    {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
                    {"id": 2, "name": "Bob", "tags": ["user"]},
                ],
                "metadata": {"version": "1.0", "count": 2},
            },
        ],
    )
    def test_convert_json_roundtrip(self, data):
        """Parameterize JSON-serializable structures and assert round-trip equality."""
        result = convert_to_mcp_content(data)
        assert len(result) == 1
        assert result[0].type == "text"

        parsed = json.loads(result[0].text)
        assert parsed == data

    def test_convert_circular_reference(self):
        """Test handling circular references in objects."""
        # Create circular reference
        obj = {"a": 1}
        obj["self"] = obj

        # Should handle gracefully (implementation dependent)
        # Most JSON encoders will raise an error
        with pytest.raises(Exception):
            convert_to_mcp_content(obj)

    def test_convert_custom_objects(self):
        """Test converting custom objects."""

        class CustomObject:
            def __str__(self):
                return "CustomObject instance"

            def __repr__(self):
                return "<CustomObject>"

        obj = CustomObject()
        result = convert_to_mcp_content(obj)

        # Should use string representation
        assert "CustomObject" in result[0].text


class TestCreateMCPTool:
    """Test create_mcp_tool function."""

    @pytest.fixture
    def sample_tool_def(self):
        """Create a sample tool definition."""
        return ToolDefinition(
            name="calculate",
            fully_qualified_name="MathToolkit.calculate",
            description="Perform a calculation",
            toolkit=ToolkitDefinition(
                name="MathToolkit",
                description="Math tools",
                version="1.0.0",
            ),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="expression",
                        required=True,
                        description="Math expression to evaluate",
                        value_schema=ValueSchema(val_type="string"),
                    ),
                    InputParameter(
                        name="precision",
                        required=False,
                        description="Decimal precision",
                        value_schema=ValueSchema(val_type="integer"),
                    ),
                ]
            ),
            output=ToolOutput(
                description="Calculation result",
                value_schema=ValueSchema(val_type="number"),
            ),
            requirements=ToolRequirements(),
        )

    @pytest.fixture
    def materialized_tool(self, sample_tool_def):
        """Create a materialized tool."""

        @tool
        def calculate(
            expression: Annotated[str, "Math expression"] = "1 + 1",
            precision: Annotated[int, "Decimal precision"] = 2,
        ) -> Annotated[float, "Calculation result"]:
            """Perform a calculation."""
            return round(eval(expression), precision)  # noqa: S307

        input_model, output_model = create_func_models(calculate)
        meta = ToolMeta(module=calculate.__module__, toolkit=sample_tool_def.toolkit.name)
        return MaterializedTool(
            tool=calculate,
            definition=sample_tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

    def test_create_basic_tool(self, materialized_tool):
        """Test creating basic MCP tool."""
        mcp_tool = create_mcp_tool(materialized_tool)

        assert mcp_tool.name == "MathToolkit_calculate"
        # ensure input schema present
        assert isinstance(mcp_tool.inputSchema, dict)

    def test_tool_input_schema(self, materialized_tool):
        """Test tool input schema generation."""
        mcp_tool = create_mcp_tool(materialized_tool)
        schema = mcp_tool.inputSchema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "expression" in schema["properties"]
        assert "precision" in schema["properties"]

        # Required may or may not be present depending on defaults
        if "required" in schema:
            assert "expression" in schema["required"]

    def _create_tool_def_with_type(self, param_type: str) -> ToolDefinition:
        return ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="param",
                        required=True,
                        description="Test param",
                        value_schema=ValueSchema(val_type=param_type),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

    @pytest.mark.parametrize(
        "arcade_type,json_type",
        [
            ("string", "string"),
            ("integer", "integer"),
            ("number", "number"),
            ("boolean", "boolean"),
            ("array", "array"),
            ("json", "object"),
        ],
    )
    def test_parameter_types(self, arcade_type, json_type):
        """Test different parameter type conversions (parameterized)."""
        tool_def = self._create_tool_def_with_type(arcade_type)

        @tool
        def f(param: Annotated[str, "Test param"]):
            return param

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        param_schema = mcp_tool.inputSchema["properties"]["param"]
        assert param_schema["type"] == json_type

    def test_array_parameter(self):
        """Test array parameter with inner type."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="items",
                        required=True,
                        description="List of items",
                        value_schema=ValueSchema(
                            val_type="array",
                            inner_val_type="string",
                        ),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f(items: Annotated[list[str], "List of items"]):
            return items

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        param_schema = mcp_tool.inputSchema["properties"]["items"]

        assert param_schema["type"] == "array"
        assert param_schema["items"]["type"] == "string"

    def test_enum_parameter(self):
        """Test enum parameter values."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="color",
                        required=True,
                        description="Color choice",
                        value_schema=ValueSchema(
                            val_type="string",
                            enum=["red", "green", "blue"],
                        ),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f(color: Annotated[str, "Color choice"]):
            return color

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        param_schema = mcp_tool.inputSchema["properties"]["color"]

        assert param_schema["type"] == "string"
        assert param_schema["enum"] == ["red", "green", "blue"]

    def test_enum_on_json_object_parameter(self):
        """Test that enum is preserved on json/object type parameters."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="config",
                        required=True,
                        description="Config choice",
                        value_schema=ValueSchema(
                            val_type="json",
                            enum=["preset_a", "preset_b"],
                        ),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f(config: Annotated[str, "Config choice"]):
            return config

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        param_schema = mcp_tool.inputSchema["properties"]["config"]

        assert param_schema["type"] == "object"
        assert param_schema["enum"] == ["preset_a", "preset_b"]

    def test_no_parameters(self):
        """Test tool with no parameters."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f() -> Annotated[str, "result"]:
            return "result"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        schema = mcp_tool.inputSchema

        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema.get("required", []) in ([], None)

    def test_output_schema_included(self, materialized_tool):
        """Test that output schema is included when definition has one."""
        mcp_tool = create_mcp_tool(materialized_tool)

        # The fixture's output has value_schema=ValueSchema(val_type="number").
        # Per MCP spec, outputSchema.type must be "object"; non-object return
        # types are wrapped in {"result": <inner>}.
        assert mcp_tool.outputSchema is not None
        assert mcp_tool.outputSchema["type"] == "object"
        assert mcp_tool.outputSchema["properties"]["result"]["type"] == "number"

    def _make_tool_with_output(self, value_schema: ValueSchema):
        """Helper to create a materialized tool with a given output ValueSchema."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(
                description="Test output",
                value_schema=value_schema,
            ),
            requirements=ToolRequirements(),
        )

        @tool
        def f() -> Annotated[str, "result"]:
            return "result"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        return create_mcp_tool(mat_tool)

    @pytest.mark.parametrize(
        "val_type",
        ["string", "integer", "number", "boolean"],
    )
    def test_output_schema_primitive_types_wrapped_as_object(self, val_type):
        """Primitive output types must be wrapped so outputSchema.type == 'object'."""
        mcp_tool = self._make_tool_with_output(ValueSchema(val_type=val_type))
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        expected_json_type = {
            "string": "string",
            "integer": "integer",
            "number": "number",
            "boolean": "boolean",
        }[val_type]
        assert schema["properties"]["result"]["type"] == expected_json_type

    def test_output_schema_array_type_wrapped_as_object(self):
        """Array output type must be wrapped so outputSchema.type == 'object'."""
        mcp_tool = self._make_tool_with_output(
            ValueSchema(val_type="array", inner_val_type="string")
        )
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        result_prop = schema["properties"]["result"]
        assert result_prop["type"] == "array"
        assert result_prop["items"]["type"] == "string"

    def test_output_schema_enum_preserved_in_wrapper(self):
        """Enum values must be preserved inside the wrapped result property."""
        mcp_tool = self._make_tool_with_output(
            ValueSchema(val_type="string", enum=["a", "b", "c"])
        )
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        assert schema["properties"]["result"]["enum"] == ["a", "b", "c"]

    def test_output_schema_json_type_not_wrapped(self):
        """Object (json) output types are already type 'object', not wrapped."""
        mcp_tool = self._make_tool_with_output(
            ValueSchema(
                val_type="json",
                properties={
                    "name": ValueSchema(val_type="string", description="A name"),
                    "count": ValueSchema(val_type="integer"),
                },
            )
        )
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        assert "result" not in schema.get("properties", {})
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["name"]["description"] == "A name"
        assert schema["properties"]["count"]["type"] == "integer"

    def test_output_schema_json_type_without_properties(self):
        """Object (json) output type with no properties is a bare object schema."""
        mcp_tool = self._make_tool_with_output(ValueSchema(val_type="json"))
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" not in schema

    def test_output_schema_nested_object(self):
        """Test that nested object properties are recursively expanded in outputSchema."""
        nested_props = {
            "id": ValueSchema(val_type="integer"),
            "name": ValueSchema(val_type="string"),
        }
        outer_props = {
            "data": ValueSchema(val_type="json", properties=nested_props),
            "status": ValueSchema(val_type="string"),
        }
        mcp_tool = self._make_tool_with_output(
            ValueSchema(val_type="json", properties=outer_props)
        )
        output_schema = mcp_tool.outputSchema

        assert output_schema is not None
        assert output_schema["type"] == "object"
        assert "data" in output_schema["properties"]
        data_schema = output_schema["properties"]["data"]
        assert data_schema["type"] == "object"
        assert "properties" in data_schema
        assert data_schema["properties"]["id"]["type"] == "integer"
        assert data_schema["properties"]["name"]["type"] == "string"
        assert output_schema["properties"]["status"]["type"] == "string"

    def test_input_schema_nested_object(self):
        """Test that nested object properties are recursively expanded in inputSchema."""
        # Two levels deep: payload.info.count — requires recursion
        deeply_nested_props = {
            "count": ValueSchema(val_type="integer"),
        }
        nested_props = {
            "id": ValueSchema(val_type="integer"),
            "info": ValueSchema(val_type="json", properties=deeply_nested_props),
        }
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="payload",
                        required=True,
                        description="Nested payload",
                        value_schema=ValueSchema(val_type="json", properties=nested_props),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f(payload: Annotated[str, "Nested payload"]):
            return payload

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        payload_schema = mcp_tool.inputSchema["properties"]["payload"]

        assert payload_schema["type"] == "object"
        assert "properties" in payload_schema
        assert payload_schema["properties"]["id"]["type"] == "integer"
        info_schema = payload_schema["properties"]["info"]
        assert info_schema["type"] == "object"
        assert "properties" in info_schema
        assert info_schema["properties"]["count"]["type"] == "integer"

    def test_output_schema_non_object_wrapped_in_object(self):
        """Non-object output types get wrapped in {type: object, properties: {result: ...}}."""
        mcp_tool = self._make_tool_with_output(ValueSchema(val_type="string"))
        output_schema = mcp_tool.outputSchema

        assert output_schema is not None
        assert output_schema["type"] == "object"
        assert "result" in output_schema["properties"]
        assert output_schema["properties"]["result"]["type"] == "string"

    def test_output_schema_array_wrapped_in_object(self):
        """Array output types get wrapped in an object with a 'result' property."""
        mcp_tool = self._make_tool_with_output(
            ValueSchema(val_type="array", inner_val_type="string")
        )
        output_schema = mcp_tool.outputSchema

        assert output_schema is not None
        assert output_schema["type"] == "object"
        assert output_schema["properties"]["result"]["type"] == "array"
        assert output_schema["properties"]["result"]["items"]["type"] == "string"


class TestConvertContentToStructuredContent:
    """Test convert_content_to_structured_content function."""

    def test_none_returns_none(self):
        assert convert_content_to_structured_content(None) is None

    def test_dict_returned_as_is(self):
        d = {"key": "value"}
        assert convert_content_to_structured_content(d) is d

    def test_list_wrapped_in_result(self):
        result = convert_content_to_structured_content([1, 2, 3])
        assert result == {"result": [1, 2, 3]}

    @pytest.mark.parametrize("value", ["hello", 42, 3.14, True])
    def test_primitives_wrapped_in_result(self, value):
        result = convert_content_to_structured_content(value)
        assert result == {"result": value}

    def test_arbitrary_object_str_wrapped(self):
        class Custom:
            def __str__(self):
                return "custom-str"

        result = convert_content_to_structured_content(Custom())
        assert result == {"result": "custom-str"}


class TestConvertToolExecution:
    """MCP conversion reads ``__tool_execution__`` off the tool function.

    The policy lives on the function (set by ``@tool(execution=...)``) -- it is
    NOT stored on ``ToolDefinition`` in arcade-core, which stays protocol-neutral.
    """

    def test_convert_no_execution_on_function(self):
        """Tool without __tool_execution__ -> no execution on MCPTool."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Toolkit.test",
            description="test",
            toolkit=ToolkitDefinition(name="Toolkit"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(available_modes=["value"]),
            requirements=ToolRequirements(),
        )

        @tool
        def f() -> str:
            return "result"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        assert mcp_tool.execution is None

    def test_convert_populates_execution_from_function_dunder(self):
        """Tool with execution policy on the function -> execution on MCPTool."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Toolkit.test",
            description="test",
            toolkit=ToolkitDefinition(name="Toolkit"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(available_modes=["value"]),
            requirements=ToolRequirements(),
        )

        @tool(execution=ToolExecution(taskSupport="optional"))
        def f() -> str:
            return "result"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        assert mcp_tool.execution is not None
        assert mcp_tool.execution.taskSupport == "optional"

    def test_convert_ignores_non_toolexecution_payload(self):
        """Non-ToolExecution ``__tool_execution__`` is ignored (guard against
        arbitrary dunder payloads reaching the MCP wire)."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Toolkit.test",
            description="test",
            toolkit=ToolkitDefinition(name="Toolkit"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(available_modes=["value"]),
            requirements=ToolRequirements(),
        )

        @tool(execution={"taskSupport": "optional"})  # dict, not ToolExecution
        def f() -> str:
            return "result"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        mcp_tool = create_mcp_tool(mat_tool)
        assert mcp_tool.execution is None


class TestOutputSchemaOptionalTypedDictFields:
    """Test that outputSchema correctly represents optional TypedDict fields.

    Reproduces: When a TypedDict uses total=False, extract_properties() treats
    every field identically — the outputSchema has no 'required' array, and field
    types never include 'null'. Combined with model_dump() emitting None for absent
    fields, the MCP client rejects the response because null doesn't match "string".
    """

    def _make_tool_and_mcp_tool(self, return_type, annotation_desc="result"):
        """Helper: register a tool returning `return_type` and get the MCP tool."""

        @tool
        def f() -> Annotated[return_type, annotation_desc]:
            """Test tool."""
            return {}

        tool_def = ToolCatalog().create_tool_definition(f, toolkit_name="test", toolkit_version="1.0")
        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit="test")
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        return create_mcp_tool(mat_tool)

    def test_total_false_typeddict_schema_allows_absent_fields(self):
        """The outputSchema for a total=False TypedDict must not require any field.

        JSON Schema: if "required" is absent, all properties are optional — that's fine.
        But the schema must also allow absent fields to validate. Currently the schema
        does not emit a "required" array, which accidentally makes all fields optional
        in JSON Schema terms. However, model_dump() reintroduces None values for the
        absent fields, and "null" is not valid for "type": "string". The schema must
        either: (a) include "null" in the type, or (b) the serializer must omit Nones.
        This test validates the schema side: if a field CAN be null in structuredContent,
        the schema must accept null.
        """
        from typing_extensions import TypedDict

        class AllOptional(TypedDict, total=False):
            name: str
            count: int

        mcp_tool = self._make_tool_and_mcp_tool(AllOptional)
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        # The schema must not list any field as required since all are total=False
        required = schema.get("required", [])
        assert "name" not in required
        assert "count" not in required

    def test_mixed_required_optional_schema_marks_required_fields(self):
        """A TypedDict with both required and optional fields must have a 'required' array.

        Required fields (from the base total=True class) must appear in the
        schema's 'required' array. Optional fields (from total=False) must not.
        """
        from typing_extensions import TypedDict

        class _Base(TypedDict):
            id: int

        class MixedDict(_Base, total=False):
            label: str

        mcp_tool = self._make_tool_and_mcp_tool(MixedDict)
        schema = mcp_tool.outputSchema

        assert schema is not None
        assert schema["type"] == "object"
        # "id" is required, "label" is optional
        required = schema.get("required", [])
        assert "id" in required, (
            "Required field 'id' must appear in outputSchema.required "
            f"but got required={required}"
        )
        assert "label" not in required

    def test_structuredcontent_validates_against_output_schema(self):
        """End-to-end: structuredContent for absent optional fields must match outputSchema.

        Simulates the full pipeline: Pydantic model_dump() round-trip then
        structuredContent conversion. When a tool omits an optional field,
        model_dump() reintroduces it as None. The outputSchema says "type": "string",
        so the MCP client rejects the null value.
        """
        from arcade_core.catalog import create_model_from_typeddict
        from typing_extensions import TypedDict

        class ResponseDict(TypedDict, total=False):
            name: str
            optional_detail: str

        # 1. Build outputSchema
        mcp_tool = self._make_tool_and_mcp_tool(ResponseDict)
        schema = mcp_tool.outputSchema

        # 2. Simulate the Pydantic round-trip that output.py performs:
        #    create_model_from_typeddict -> instantiate -> model_dump()
        pydantic_model = create_model_from_typeddict(ResponseDict, "ResponseDict")
        instance = pydantic_model(**{"name": "hello"})  # optional_detail absent
        dumped = instance.model_dump()

        # 3. Convert to structuredContent (what server.py does)
        structured = convert_content_to_structured_content(dumped)

        # The structured content must validate against the schema.
        # No field in structuredContent should have a value (like null)
        # that the schema's type declaration doesn't allow.
        assert structured is not None
        for field_name, field_schema in schema.get("properties", {}).items():
            if field_name in structured:
                value = structured[field_name]
                allowed_type = field_schema.get("type")
                if value is None:
                    # null must be allowed by the schema
                    if isinstance(allowed_type, list):
                        assert "null" in allowed_type, (
                            f"Field '{field_name}' is null in structuredContent but schema "
                            f"type {allowed_type} does not include 'null'"
                        )
                    else:
                        assert allowed_type == "null" or allowed_type is None, (
                            f"Field '{field_name}' is null in structuredContent but schema "
                            f"type is '{allowed_type}', not 'null'"
                        )

    def test_list_of_typeddict_items_have_required(self):
        """list[TypedDict] with total=True produces items.required in MCP outputSchema."""
        from typing_extensions import TypedDict

        class ItemDict(TypedDict):
            name: str
            value: int

        mcp_tool = self._make_tool_and_mcp_tool(list[ItemDict])
        schema = mcp_tool.outputSchema

        assert schema is not None
        # list output gets wrapped: {type: object, properties: {result: {type: array, ...}}}
        result_prop = schema["properties"]["result"]
        assert result_prop["type"] == "array"
        items_schema = result_prop["items"]
        assert items_schema["type"] == "object"
        assert sorted(items_schema["required"]) == ["name", "value"]

    def test_nullable_field_allows_null_in_schema(self):
        """str | None field produces 'type': ['string', 'null'] in outputSchema."""
        from typing_extensions import TypedDict

        class NullableDict(TypedDict):
            label: str
            note: str | None

        mcp_tool = self._make_tool_and_mcp_tool(NullableDict)
        schema = mcp_tool.outputSchema

        assert schema is not None
        props = schema["properties"]
        assert props["label"]["type"] == "string"
        assert props["note"]["type"] == ["string", "null"]

    def test_nullable_enum_field_allows_null(self):
        """Literal['a', 'b'] | None field produces type=['string', 'null'], enum=['a', 'b', None]."""
        from typing import Literal

        from typing_extensions import TypedDict

        class EnumNullableDict(TypedDict):
            status: Literal["a", "b"] | None

        mcp_tool = self._make_tool_and_mcp_tool(EnumNullableDict)
        schema = mcp_tool.outputSchema

        assert schema is not None
        status_schema = schema["properties"]["status"]
        assert status_schema["type"] == ["string", "null"]
        assert status_schema["enum"] == ["a", "b", None]

    def test_input_schema_typeddict_required_keys(self):
        """TypedDict used as input parameter gets required array in inputSchema."""
        from typing_extensions import TypedDict

        class ConfigDict(TypedDict):
            host: str
            port: int

        @tool
        def f(config: Annotated[ConfigDict, "The config"]) -> str:
            """Test tool."""
            return ""

        tool_def = ToolCatalog().create_tool_definition(
            f, toolkit_name="test", toolkit_version="1.0"
        )
        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit="test")
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        mcp_tool = create_mcp_tool(mat_tool)
        config_schema = mcp_tool.inputSchema["properties"]["config"]

        assert config_schema["type"] == "object"
        assert sorted(config_schema["required"]) == ["host", "port"]

    def test_input_schema_typeddict_nullable_field(self):
        """TypedDict input parameter with str | None field gets type=['string', 'null']."""
        from typing_extensions import TypedDict

        class InputDict(TypedDict):
            name: str
            tag: str | None

        @tool
        def f(data: Annotated[InputDict, "The data"]) -> str:
            """Test tool."""
            return ""

        tool_def = ToolCatalog().create_tool_definition(
            f, toolkit_name="test", toolkit_version="1.0"
        )
        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit="test")
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )
        mcp_tool = create_mcp_tool(mat_tool)
        data_schema = mcp_tool.inputSchema["properties"]["data"]

        assert data_schema["properties"]["name"]["type"] == "string"
        assert data_schema["properties"]["tag"]["type"] == ["string", "null"]
