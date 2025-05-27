import ast

import pytest
from arcade_core.parse import get_tools_from_ast


@pytest.mark.parametrize(
    "source, expected_tools",
    [
        pytest.param(
            """
@tool
def my_function():
    pass
    """,
            ["my_function"],
            id="function with tool decorator",
        ),
        pytest.param(
            """
import arcade.sdk as arc
@arc.tool
def another_function():
    pass
    """,
            ["another_function"],
            id="function with arc.tool decorator",
        ),
        pytest.param(
            """
def no_decorator_function():
    pass
    """,
            [],
            id="function without decorator",
        ),
        pytest.param(
            """
@other_decorator
def different_function():
    pass
    """,
            [],
            id="function with other decorator",
        ),
    ],
)
def test_get_function_name_if_decorated(source, expected_tools):
    tree = ast.parse(source)
    tools = get_tools_from_ast(tree)
    assert tools == expected_tools
