from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog, get_wire_type
from arcade_tdk import tool


class Case:
    def __init__(self, input_type: type, output_type: type | None):
        self.input_type = input_type
        self.output_type = output_type

    def __str__(self):
        return f"Case(input_type={self.input_type}, output_type={self.output_type})"


primitives = [bool, float, int, str]

test_cases = [
    Case(input_type=input_type, output_type=output_type)
    for input_type in [*primitives, []]
    for output_type in [*primitives, None]
] + [
    Case(input_type=[primitives[i] for i in range(n)], output_type=output_type)
    for n in range(2, len(primitives) + 1)
    for output_type in [*primitives, None]
]


# Generate tool functions dynamically
def generate_tool_function(input_types: list[type], output_type: type | None):
    input_annotation = ", ".join([
        f"param{i}: Annotated[{input_type.__name__}, 'Param {i + 1}']"
        for i, input_type in enumerate(input_types)
    ])
    output_annotation = f" -> {output_type.__name__}" if output_type else ""

    func_code = f"""
@tool(desc="Generated function with input and output types")
def generated_func({input_annotation}){output_annotation}:
    pass
"""
    local_vars = {}
    exec(func_code, {"tool": tool, "Annotated": Annotated}, local_vars)  # noqa: S102
    generated_func = local_vars.get("generated_func")
    generated_func.__source__ = func_code  # Attach the source code to the function
    return generated_func


@pytest.mark.parametrize("test_case", test_cases, ids=[str(tc) for tc in test_cases])
def test_create_tool_def2(test_case):
    input_types = (
        test_case.input_type if isinstance(test_case.input_type, list) else [test_case.input_type]
    )
    output_type = test_case.output_type

    # Generate the function dynamically
    generated_func = generate_tool_function(input_types, output_type)

    assert generated_func is not None, "generated_func was not created"

    # Create tool definition using the generated function
    tool_def = ToolCatalog.create_tool_definition(generated_func, "1.0")

    for i, input_type in enumerate(input_types):
        param = tool_def.input.parameters[i]
        assert (
            param.value_schema.val_type == get_wire_type(input_type)
        ), f"Parameter {param.name} has value type {param.value_schema.val_type} but {input_type} was expected at index {i}"

    if output_type:
        assert tool_def.output.value_schema.val_type == get_wire_type(
            output_type
        ), f"Output has value type {tool_def.output.val_type} but {output_type} was expected"
    else:
        assert tool_def.output.value_schema is None, "Output is not None"
