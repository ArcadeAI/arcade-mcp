import ast
from collections.abc import Iterator
from pathlib import Path


def load_ast_tree(filepath: str | Path) -> ast.AST:
    """
    Load and parse the Abstract Syntax Tree (AST) from a Python file.

    """
    try:
        with open(filepath, encoding="utf-8") as file:
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


def _module_scope_functions(node: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """The functions a module can bind as its own attributes.

    Registration resolves a declaration with getattr on the imported module, so
    a method or a function nested inside another is not something it can reach.
    A def and a class open a new scope and stop the descent. Everything else is
    followed, an if, a try, a with, a loop and a match case alike, and naming
    none of them individually is the point: a def only appears in a statement
    list, so descending through expressions cannot turn up a false one, and a
    statement this misses is a declaration dropped with nothing raised.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield child
        elif not isinstance(child, ast.ClassDef):
            yield from _module_scope_functions(child)


def get_tools_from_ast(tree: ast.AST) -> list[str]:
    """
    Retrieve tools from Python source code.
    """
    # One name is one module attribute however many times it is written, so a
    # module defining the same tool in both arms of an if or a try/except
    # contributes it once.
    return list(
        dict.fromkeys(
            name
            for node in _module_scope_functions(tree)
            if (name := get_function_name_if_decorated(node))
        )
    )
