"""Tests for MCP content conversion utilities."""

import base64
import json
from typing import Annotated

import pytest
from arcade_core.catalog import MaterializedTool, ToolMeta, create_func_models
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
from arcade_mcp_server.convert import convert_to_mcp_content, create_mcp_tool

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

    def test_missing_input_attribute_fallback(self):
        """Test tool with missing input attribute to trigger _build_input_schema_from_model fallback."""
        # Create a valid ToolDefinition first
        tool_def = ToolDefinition(
            name="test_fallback",
            fully_qualified_name="Test.test_fallback",
            description="Test fallback to input model",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        @tool
        def f(
            name: Annotated[str, "User name"], age: Annotated[int, "User age"] = 25
        ) -> Annotated[str, "greeting"]:
            return f"Hello {name}, you are {age} years old"

        input_model, output_model = create_func_models(f)
        meta = ToolMeta(module=f.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=f,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        # Remove the input attribute from the definition to simulate the missing attribute case
        delattr(mat_tool.definition, "input")

        mcp_tool = create_mcp_tool(mat_tool)
        schema = mcp_tool.inputSchema

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]

        # Ensure the schema was built from the model and not the definition
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

        if "required" in schema:
            assert "name" in schema["required"]
            assert "age" not in schema["required"]
