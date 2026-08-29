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


#: Where Arcade's ``@resource`` decorator can be imported from.
_RESOURCE_DECORATOR_MODULES = frozenset({
    "arcade_tdk",
    "arcade_mcp_server",
    "arcade_core.resources",
})
_RESOURCE_DECORATOR = "resource"


def _resource_decorator_names(tree: ast.AST) -> set[str]:
    """The names this module binds Arcade's ``@resource`` decorator to.

    Resolving against the module's own imports is what separates a declaration
    from a same-named decorator belonging to something else, ``MCPApp.resource``
    among them. A module that never imports ours cannot be declaring one with it.

    Every spelling that can bind the decorator has to be covered here. Miss one
    and the declaration goes missing with nothing raised, because the decorator
    still runs at import time and the resource simply never gets registered.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound = alias.asname or alias.name
                if node.module in _RESOURCE_DECORATOR_MODULES:
                    if alias.name == _RESOURCE_DECORATOR:
                        # from arcade_tdk import resource
                        names.add(bound)
                    elif alias.name == "*":
                        # from arcade_tdk import *
                        names.add(_RESOURCE_DECORATOR)
                if f"{node.module}.{alias.name}" in _RESOURCE_DECORATOR_MODULES:
                    # from arcade_core import resources
                    names.add(f"{bound}.{_RESOURCE_DECORATOR}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _RESOURCE_DECORATOR_MODULES:
                    # import arcade_tdk / import arcade_core.resources
                    names.add(f"{alias.asname or alias.name}.{_RESOURCE_DECORATOR}")
    return names


def _dotted_name(node: ast.expr) -> str | None:
    """The dotted path a decorator expression names, or None if it names none.

    Walks the whole attribute chain, so ``@arcade_core.resources.resource`` is
    matched against the same binding ``import arcade_core.resources`` produces.
    """
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _is_resource_declaration(
    node: ast.FunctionDef | ast.AsyncFunctionDef, bindings: set[str]
) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if _dotted_name(target) in bindings:
            return True
    return False


def get_resources_from_file(filepath: str | Path) -> list[str]:
    """
    Retrieve resource declarations from a Python file.
    """
    return get_resources_from_ast(load_ast_tree(filepath))


def _module_scope_functions(node: ast.AST) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """The functions a module can bind as its own attributes.

    Registration resolves a declaration with getattr on the imported module, so
    a method or a function nested inside another is not something it can reach.
    An if, try, with or loop body stays in module scope and is followed into; a
    def or a class opens a new one and is not.
    """
    for field in ("body", "orelse", "finalbody"):
        for stmt in getattr(node, field, []):
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield stmt
            elif not isinstance(stmt, ast.ClassDef):
                yield from _module_scope_functions(stmt)
    for handler in getattr(node, "handlers", []):
        yield from _module_scope_functions(handler)


def get_resources_from_ast(tree: ast.AST) -> list[str]:
    """
    Retrieve resource declarations from Python source code.
    """
    bindings = _resource_decorator_names(tree)
    if not bindings:
        return []

    return [
        node.name
        for node in _module_scope_functions(tree)
        if _is_resource_declaration(node, bindings)
    ]
