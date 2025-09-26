import ast
from pathlib import Path


def load_ast_tree(filepath: str | Path) -> ast.AST:
    """
    Load and parse the Abstract Syntax Tree (AST) from a Python file.

    """
    try:
        with open(filepath) as file:
            return ast.parse(file.read(), filename=filepath)
    except FileNotFoundError:
        raise FileNotFoundError(f"File {filepath} not found")


def get_function_name_if_decorated(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
    """
    Check if a function has a decorator.
    """
    decorator_ids = {"arc.tool", "tool"}
    for decorator in node.decorator_list:
        # if the function is decorated and the decorator is
        # either called, or placed on the function
        if (
            (isinstance(decorator, ast.Name) and decorator.id in decorator_ids)
            or (
                isinstance(decorator, ast.Attribute)
                and isinstance(decorator.value, ast.Name)
                and f"{decorator.value.id}.{decorator.attr}" in decorator_ids
            )
            or (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id in decorator_ids
            )
            # Support MCPApp tools. e.g., @app.tool or @app.tool(...)
            or (
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "tool"
                and isinstance(decorator.value, ast.Name)
            )
            or (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "tool"
                and isinstance(decorator.func.value, ast.Name)
            )
        ):
            return node.name
    return None


def get_tools_from_file(filepath: str | Path) -> list[str]:
    """
    Retrieve tools from a Python file.
    """
    tree = load_ast_tree(filepath)
    return get_tools_from_ast(tree)


def get_tools_from_ast(tree: ast.AST) -> list[str]:
    """
    Retrieve tools from Python source code.
    """
    tools = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tool_name = get_function_name_if_decorated(node)
            if tool_name:
                tools.append(tool_name)
    return tools
