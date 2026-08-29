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


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "class Helpers:\n    @tool\n    def a(self): ...",
            id="a method is an attribute of the class",
        ),
        pytest.param(
            "def outer():\n    @tool\n    def a(): ...\n    return a",
            id="a nested function is a local of its enclosing one",
        ),
        pytest.param(
            "async def outer():\n    @tool\n    def a(): ...",
            id="the same inside an async def",
        ),
        pytest.param(
            "def outer():\n    class Inner:\n        @tool\n        def a(self): ...",
            id="a class inside a function is doubly out of reach",
        ),
    ],
)
def test_a_tool_the_module_cannot_bind_is_not_discovered(source):
    """Registration reaches a tool with getattr on the module, and nothing else."""
    assert get_tools_from_ast(ast.parse(source)) == []


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("if True:\n    @tool\n    def a(): ...", id="if"),
        pytest.param("if False:\n    pass\nelse:\n    @tool\n    def a(): ...", id="else"),
        pytest.param("try:\n    @tool\n    def a(): ...\nexcept ImportError:\n    pass", id="try"),
        pytest.param(
            "try:\n    pass\nexcept ImportError:\n    @tool\n    def a(): ...",
            id="except",
        ),
        pytest.param("try:\n    pass\nfinally:\n    @tool\n    def a(): ...", id="finally"),
        pytest.param("for _ in range(1):\n    @tool\n    def a(): ...", id="for"),
        pytest.param("with open(__file__):\n    @tool\n    def a(): ...", id="with"),
        pytest.param("match 1:\n    case 1:\n        @tool\n        def a(): ...", id="match case"),
    ],
)
def test_a_tool_guarded_by_a_module_level_block_is_discovered(source):
    """These keep module scope, so the name really can become an attribute."""
    assert get_tools_from_ast(ast.parse(source)) == ["a"]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            "if True:\n    @tool\n    def a(): ...\nelse:\n    @tool\n    def a(): ...",
            id="both arms of an if",
        ),
        pytest.param(
            "try:\n    @tool\n    def a(): ...\nexcept ImportError:\n    @tool\n    def a(): ...",
            id="both arms of a try",
        ),
    ],
)
def test_a_name_written_in_two_branches_is_one_tool(source):
    """Only one arm binds at import, so counting both would register the same function twice."""
    assert get_tools_from_ast(ast.parse(source)) == ["a"]


def test_discovery_keeps_source_order():
    """The catalog is built by walking this list, so the order it reports is the order it sees."""
    source = "@tool\ndef z(): ...\n\n@tool\ndef a(): ...\n\n@tool\ndef m(): ..."

    assert get_tools_from_ast(ast.parse(source)) == ["z", "a", "m"]
