import ast
import inspect
import re
from collections.abc import Iterable
from types import UnionType
from typing import Any, Callable, Literal, Optional, TypeVar, Union, get_args, get_origin

T = TypeVar("T")


def first_or_none(_type: type[T], iterable: Iterable[Any]) -> Optional[T]:
    """
    Returns the first item in the iterable that is an instance of the given type, or None if no such item is found.
    """
    for item in iterable:
        if isinstance(item, _type):
            return item
    return None


def pascal_to_snake_case(name: str) -> str:
    """
    Converts a PascalCase name to snake_case.
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def snake_to_pascal_case(name: str) -> str:
    """
    Converts a snake_case name to PascalCase.
    """
    if "_" in name:
        return "".join(x.capitalize() or "_" for x in name.split("_"))
    # check if first letter is uppercase
    if name[0].isupper():
        return name
    return name.capitalize()


def is_string_literal(_type: type) -> bool:
    """
    Returns True if the given type is a string literal, i.e. a Literal[str] or Literal[str, str, ...] etc.
    """
    return get_origin(_type) is Literal and all(isinstance(arg, str) for arg in get_args(_type))


def is_union(_type: type) -> bool:
    """
    Returns True if the given type is a union, i.e. a Union[T1, T2, ...] or T1 | T2 | ... etc.
    """
    return get_origin(_type) in {Union, UnionType}


def does_function_return_value(func: Callable) -> bool:
    """
    Returns True if the given function returns a value, i.e. if it has a return statement with a value.
    """
    try:
        source: Optional[str] = inspect.getsource(func)
    except OSError:
        # Workaround for parameterized unit tests that use a dynamically-generated function
        source = getattr(func, "__source__", None)

    if source is None:
        raise ValueError("Source code not found")

    tree = ast.parse(source)

    class ReturnVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.returns_value = False

        def visit_Return(self, node: ast.Return) -> None:
            if node.value is not None:
                self.returns_value = True

    visitor = ReturnVisitor()
    visitor.visit(tree)
    return visitor.returns_value
