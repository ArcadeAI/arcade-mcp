import ast
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from typing import Optional, Union

from stdlib_list import stdlib_list


def load_ast_tree(filepath: str | Path) -> ast.AST:
    """
    Load and parse the Abstract Syntax Tree (AST) from a Python file.

    """
    try:
        with open(filepath) as file:
            return ast.parse(file.read(), filename=filepath)
    except FileNotFoundError:
        raise FileNotFoundError(f"File {filepath} not found")


def get_python_version() -> str:
    """
    Get the current Python version.
    """
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def retrieve_imported_libraries(tree: ast.AST) -> dict[str, Optional[str]]:
    """
    Retrieve non-standard libraries imported in the AST.
    """
    libraries = {}
    python_version = get_python_version()
    stdlib_modules = stdlib_list(python_version)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            package_name = node.module.split(".")[0] if node.module else None
            if package_name:
                if package_name in stdlib_modules:
                    continue
                else:
                    try:
                        package_version = importlib.metadata.version(package_name)
                    except importlib.metadata.PackageNotFoundError:
                        package_version = None
            else:
                continue
            libraries[package_name] = package_version
    return libraries


def get_function_name_if_decorated(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
) -> Optional[str]:
    """
    Check if a function has a decorator
    """
    decorator_ids = {"ar.tool", "tool"}
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id in decorator_ids:
            return node.name
    return None


def get_tools_from_file(filepath: str | Path) -> list[str]:
    """
    Retrieve tools from a Python file.
    """
    tree = load_ast_tree(filepath)
    tools = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tool_name = get_function_name_if_decorated(node)
            if tool_name:
                tools.append(tool_name)
    return tools
