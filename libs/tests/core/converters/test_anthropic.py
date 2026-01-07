"""Tests for Anthropic converter utilities."""

from typing import Annotated

import pytest
from arcade_core.catalog import MaterializedTool, ToolMeta, create_func_models
from arcade_core.converters.anthropic import (
    AnthropicInputSchema,
    _convert_input_parameters_to_json_schema,
    _convert_value_schema_to_json_schema,
    _create_tool_schema,
    to_anthropic,
)
from arcade_core.schema import (
    InputParameter,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)


class TestAnthropicConverter:
    """Test Anthropic converter functions."""

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

    def test_to_anthropic_basic(self, materialized_tool):
        """Test basic Anthropic tool conversion."""
        result = to_anthropic(materialized_tool)

        assert isinstance(result, dict)
        # Anthropic has flat structure - no "type: function" wrapper
        assert "type" not in result
        assert "function" not in result

        # Check top-level fields
        assert result["name"] == "MathToolkit_calculate"
        assert result["description"] == "Perform a calculation"
        assert "input_schema" in result

    def test_function_name_conversion(self, materialized_tool):
        """Test that dots in fully_qualified_name are converted to underscores."""
        result = to_anthropic(materialized_tool)
        assert result["name"] == "MathToolkit_calculate"

    def test_input_schema_structure(self, materialized_tool):
        """Test the structure of input_schema."""
        result = to_anthropic(materialized_tool)
        input_schema = result["input_schema"]

        assert input_schema["type"] == "object"
        assert "properties" in input_schema
        # Only required parameters should be in required list
        assert input_schema["required"] == ["expression"]

    def test_no_strict_mode_constraints(self, materialized_tool):
        """Test that Anthropic format doesn't have strict mode constraints."""
        result = to_anthropic(materialized_tool)
        input_schema = result["input_schema"]

        # No additionalProperties constraint (unlike OpenAI strict mode)
        assert "additionalProperties" not in input_schema

        # No "strict" flag
        assert "strict" not in result

    def test_required_parameter_schema(self, materialized_tool):
        """Test required parameter schema generation."""
        result = to_anthropic(materialized_tool)
        props = result["input_schema"]["properties"]

        expression_prop = props["expression"]
        assert expression_prop["type"] == "string"
        assert expression_prop["description"] == "Math expression to evaluate"

    def test_optional_parameter_schema(self, materialized_tool):
        """Test optional parameter schema - no null union type like OpenAI."""
        result = to_anthropic(materialized_tool)
        props = result["input_schema"]["properties"]

        precision_prop = props["precision"]
        # Unlike OpenAI, optional parameters should NOT have union type with null
        assert precision_prop["type"] == "integer"
        assert precision_prop["description"] == "Decimal precision"

    def test_optional_params_not_in_required(self, materialized_tool):
        """Test that only required params are in the required array."""
        result = to_anthropic(materialized_tool)
        required = result["input_schema"]["required"]

        assert "expression" in required
        assert "precision" not in required

    def test_no_parameters_tool(self):
        """Test tool with no parameters."""
        tool_def = ToolDefinition(
            name="get_time",
            fully_qualified_name="TimeToolkit.get_time",
            description="Get current time",
            toolkit=ToolkitDefinition(name="TimeToolkit"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def get_time() -> Annotated[str, "current time"]:
            return "2023-01-01T00:00:00Z"

        input_model, output_model = create_func_models(get_time)
        meta = ToolMeta(module=get_time.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=get_time,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        input_schema = result["input_schema"]

        assert input_schema["type"] == "object"
        assert input_schema["properties"] == {}
        # No required field when there are no parameters
        assert "required" not in input_schema

    @pytest.mark.parametrize(
        "arcade_type,expected_json_type",
        [
            ("string", "string"),
            ("integer", "integer"),
            ("number", "number"),
            ("boolean", "boolean"),
            ("array", "array"),
            ("json", "object"),
        ],
    )
    def test_parameter_type_conversion(self, arcade_type, expected_json_type):
        """Test different parameter type conversions."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test tool",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="param",
                        required=True,
                        description="Test parameter",
                        value_schema=ValueSchema(val_type=arcade_type),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def test_func(param: Annotated[str, "Test parameter"]):
            return param

        input_model, output_model = create_func_models(test_func)
        meta = ToolMeta(module=test_func.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=test_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_schema = result["input_schema"]["properties"]["param"]
        assert param_schema["type"] == expected_json_type

    def test_array_parameter_with_inner_type(self):
        """Test array parameter with inner type specification."""
        tool_def = ToolDefinition(
            name="process_items",
            fully_qualified_name="ArrayToolkit.process_items",
            description="Process a list of items",
            toolkit=ToolkitDefinition(name="ArrayToolkit"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="items",
                        required=True,
                        description="List of string items",
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

        def process_items(items: Annotated[list[str], "List of string items"]):
            return items

        input_model, output_model = create_func_models(process_items)
        meta = ToolMeta(module=process_items.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=process_items,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_schema = result["input_schema"]["properties"]["items"]

        assert param_schema["type"] == "array"
        assert param_schema["items"]["type"] == "string"

    def test_enum_parameter(self):
        """Test parameter with enum values."""
        tool_def = ToolDefinition(
            name="set_color",
            fully_qualified_name="ColorToolkit.set_color",
            description="Set a color",
            toolkit=ToolkitDefinition(name="ColorToolkit"),
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

        def set_color(color: Annotated[str, "Color choice"]):
            return color

        input_model, output_model = create_func_models(set_color)
        meta = ToolMeta(module=set_color.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=set_color,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_schema = result["input_schema"]["properties"]["color"]

        assert param_schema["type"] == "string"
        assert param_schema["enum"] == ["red", "green", "blue"]

    def test_array_with_enum_items(self):
        """Test array parameter where items have enum values."""
        tool_def = ToolDefinition(
            name="set_colors",
            fully_qualified_name="ColorToolkit.set_colors",
            description="Set multiple colors",
            toolkit=ToolkitDefinition(name="ColorToolkit"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="colors",
                        required=True,
                        description="List of colors",
                        value_schema=ValueSchema(
                            val_type="array",
                            inner_val_type="string",
                            enum=["red", "green", "blue"],
                        ),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def set_colors(colors: Annotated[list[str], "List of colors"]):
            return colors

        input_model, output_model = create_func_models(set_colors)
        meta = ToolMeta(module=set_colors.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=set_colors,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_schema = result["input_schema"]["properties"]["colors"]

        assert param_schema["type"] == "array"
        assert param_schema["items"]["type"] == "string"
        assert param_schema["items"]["enum"] == ["red", "green", "blue"]

    def test_json_parameter_with_properties(self):
        """Test JSON parameter with nested properties."""
        tool_def = ToolDefinition(
            name="create_user",
            fully_qualified_name="UserToolkit.create_user",
            description="Create a user",
            toolkit=ToolkitDefinition(name="UserToolkit"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="user_data",
                        required=True,
                        description="User information",
                        value_schema=ValueSchema(
                            val_type="json",
                            properties={
                                "name": ValueSchema(val_type="string"),
                                "age": ValueSchema(val_type="integer"),
                                "active": ValueSchema(val_type="boolean"),
                            },
                        ),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def create_user(user_data: Annotated[dict, "User information"]):
            return user_data

        input_model, output_model = create_func_models(create_user)
        meta = ToolMeta(module=create_user.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=create_user,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_schema = result["input_schema"]["properties"]["user_data"]

        assert param_schema["type"] == "object"
        assert "properties" in param_schema
        assert param_schema["properties"]["name"]["type"] == "string"
        assert param_schema["properties"]["age"]["type"] == "integer"
        assert param_schema["properties"]["active"]["type"] == "boolean"

    def test_multiple_optional_parameters(self):
        """Test tool with multiple optional parameters."""
        tool_def = ToolDefinition(
            name="search",
            fully_qualified_name="SearchToolkit.search",
            description="Search with filters",
            toolkit=ToolkitDefinition(name="SearchToolkit"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="query",
                        required=True,
                        description="Search query",
                        value_schema=ValueSchema(val_type="string"),
                    ),
                    InputParameter(
                        name="limit",
                        required=False,
                        description="Result limit",
                        value_schema=ValueSchema(val_type="integer"),
                    ),
                    InputParameter(
                        name="include_metadata",
                        required=False,
                        description="Include metadata in results",
                        value_schema=ValueSchema(val_type="boolean"),
                    ),
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def search(
            query: Annotated[str, "Search query"],
            limit: Annotated[int, "Result limit"] = 10,
            include_metadata: Annotated[bool, "Include metadata"] = False,
        ):
            return f"Search results for {query}"

        input_model, output_model = create_func_models(search)
        meta = ToolMeta(module=search.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=search,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        props = result["input_schema"]["properties"]

        # All parameters should have their simple type (no null union)
        assert props["query"]["type"] == "string"
        assert props["limit"]["type"] == "integer"
        assert props["include_metadata"]["type"] == "boolean"

        # Only required parameter should be in required list
        assert result["input_schema"]["required"] == ["query"]


class TestHelperFunctions:
    """Test helper functions used by the converter."""

    def test_create_tool_schema(self):
        """Test _create_tool_schema helper function."""
        input_schema: AnthropicInputSchema = {
            "type": "object",
            "properties": {"test": {"type": "string"}},
            "required": ["test"],
        }

        result = _create_tool_schema("test_func", "Test function", input_schema)

        # Verify flat structure (no "type: function" wrapper)
        assert "type" not in result
        assert "function" not in result

        assert result["name"] == "test_func"
        assert result["description"] == "Test function"
        assert result["input_schema"] == input_schema

    def test_convert_value_schema_to_json_schema_basic_types(self):
        """Test _convert_value_schema_to_json_schema for basic types."""
        test_cases = [
            ("string", "string"),
            ("integer", "integer"),
            ("number", "number"),
            ("boolean", "boolean"),
            ("json", "object"),
            ("array", "array"),
        ]

        for arcade_type, expected_json_type in test_cases:
            schema = ValueSchema(val_type=arcade_type)
            result = _convert_value_schema_to_json_schema(schema)
            assert result["type"] == expected_json_type

    def test_convert_value_schema_with_enum(self):
        """Test _convert_value_schema_to_json_schema with enum values."""
        schema = ValueSchema(val_type="string", enum=["a", "b", "c"])
        result = _convert_value_schema_to_json_schema(schema)

        assert result["type"] == "string"
        assert result["enum"] == ["a", "b", "c"]

    def test_convert_input_parameters_empty_list(self):
        """Test _convert_input_parameters_to_json_schema with empty parameters."""
        result = _convert_input_parameters_to_json_schema([])

        assert result["type"] == "object"
        assert result["properties"] == {}
        # No additionalProperties constraint for Anthropic
        assert "additionalProperties" not in result
        assert "required" not in result

    def test_convert_input_parameters_with_required_and_optional(self):
        """Test _convert_input_parameters_to_json_schema with mixed parameters."""
        params = [
            InputParameter(
                name="required_param",
                required=True,
                description="Required parameter",
                value_schema=ValueSchema(val_type="string"),
            ),
            InputParameter(
                name="optional_param",
                required=False,
                description="Optional parameter",
                value_schema=ValueSchema(val_type="integer"),
            ),
        ]

        result = _convert_input_parameters_to_json_schema(params)

        assert result["type"] == "object"
        # No additionalProperties for Anthropic
        assert "additionalProperties" not in result

        # Only required parameter should be in required list
        assert result["required"] == ["required_param"]

        # Required parameter should have single type
        assert result["properties"]["required_param"]["type"] == "string"

        # Optional parameter should also have single type (no null union like OpenAI)
        assert result["properties"]["optional_param"]["type"] == "integer"

    def test_convert_input_parameters_all_optional(self):
        """Test that required array is omitted when all parameters are optional."""
        params = [
            InputParameter(
                name="optional_a",
                required=False,
                description="Optional A",
                value_schema=ValueSchema(val_type="string"),
            ),
            InputParameter(
                name="optional_b",
                required=False,
                description="Optional B",
                value_schema=ValueSchema(val_type="integer"),
            ),
        ]

        result = _convert_input_parameters_to_json_schema(params)

        assert result["type"] == "object"
        assert "required" not in result  # No required field when all optional


class TestAnthropicVsOpenAIDifferences:
    """Tests that explicitly verify differences between Anthropic and OpenAI formats."""

    def test_no_type_function_wrapper(self):
        """Verify Anthropic format doesn't have OpenAI's 'type: function' wrapper."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def test_func() -> str:
            """Test func."""
            return "test"

        input_model, output_model = create_func_models(test_func)
        meta = ToolMeta(module=test_func.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=test_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)

        # OpenAI has: {"type": "function", "function": {...}}
        # Anthropic should NOT have this wrapper
        assert "type" not in result
        assert "function" not in result

    def test_input_schema_key_not_parameters(self):
        """Verify Anthropic uses 'input_schema' not 'parameters'."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="param",
                        required=True,
                        description="A param",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def test_func(param: Annotated[str, "A param"]) -> str:
            """Test func."""
            return param

        input_model, output_model = create_func_models(test_func)
        meta = ToolMeta(module=test_func.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=test_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)

        # Anthropic uses input_schema, not parameters
        assert "input_schema" in result
        assert "parameters" not in result

    def test_no_strict_flag(self):
        """Verify Anthropic format doesn't have OpenAI's 'strict' flag."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(parameters=[]),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def test_func() -> str:
            """Test func."""
            return "test"

        input_model, output_model = create_func_models(test_func)
        meta = ToolMeta(module=test_func.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=test_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)

        # Anthropic should NOT have strict flag
        assert "strict" not in result

    def test_optional_params_no_null_union(self):
        """Verify optional params don't get null union type (OpenAI strict mode behavior)."""
        tool_def = ToolDefinition(
            name="test",
            fully_qualified_name="Test.test",
            description="Test",
            toolkit=ToolkitDefinition(name="Test"),
            input=ToolInput(
                parameters=[
                    InputParameter(
                        name="optional_param",
                        required=False,
                        description="Optional",
                        value_schema=ValueSchema(val_type="string"),
                    )
                ]
            ),
            output=ToolOutput(),
            requirements=ToolRequirements(),
        )

        def test_func(optional_param: Annotated[str, "Optional"] = "default") -> str:
            """Test func."""
            return optional_param

        input_model, output_model = create_func_models(test_func)
        meta = ToolMeta(module=test_func.__module__, toolkit=tool_def.toolkit.name)
        mat_tool = MaterializedTool(
            tool=test_func,
            definition=tool_def,
            meta=meta,
            input_model=input_model,
            output_model=output_model,
        )

        result = to_anthropic(mat_tool)
        param_type = result["input_schema"]["properties"]["optional_param"]["type"]

        # OpenAI strict mode would have: ["string", "null"]
        # Anthropic should just have: "string"
        assert param_type == "string"
        assert not isinstance(param_type, list)

    def test_no_additional_properties_constraint(self):
        """Verify Anthropic format doesn't require additionalProperties: false."""
        params = [
            InputParameter(
                name="param",
                required=True,
                description="Param",
                value_schema=ValueSchema(val_type="string"),
            )
        ]

        result = _convert_input_parameters_to_json_schema(params)

        # OpenAI strict mode requires: "additionalProperties": false
        # Anthropic should NOT have this constraint
        assert "additionalProperties" not in result
