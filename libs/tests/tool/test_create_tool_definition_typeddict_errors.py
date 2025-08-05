from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError
from arcade_tdk import tool
from typing_extensions import NotRequired, TypedDict


class ProductWithNotRequired(TypedDict):
    """Product with optional field using NotRequired."""

    name: str
    price: float
    description: NotRequired[str]  # NotRequired in TypedDict field is not supported


@tool
def func_takes_typeddict_with_notrequired(
    product: Annotated[ProductWithNotRequired, "Product information"],
) -> Annotated[str, "Product summary"]:
    """Process a product with NotRequired field."""
    return f"Product: {product['name']}"


class ProductWithUnionField(TypedDict):
    """Product with union type field."""

    name: str
    price: float | int  # Union type in TypedDict field is not supported
    stock: int


@tool
def func_takes_typeddict_with_union_field(
    product: Annotated[ProductWithUnionField, "Product with union price field"],
) -> Annotated[str, "Product info"]:
    """Process a product with union type field."""
    return f"Product: {product['name']}, Price: {product['price']}"


@tool
def func_takes_optional_typeddict_non_strict(
    config: ProductWithNotRequired | None = None,
) -> Annotated[str, "Configuration status"]:
    """Process optional TypedDict with non-strict syntax."""
    return "processed" if config else "no config"


@pytest.mark.parametrize(
    "func_under_test, exception_type",
    [
        pytest.param(
            func_takes_typeddict_with_notrequired,
            ToolDefinitionError,
            id="typeddict_with_notrequired",
        ),
        pytest.param(
            func_takes_typeddict_with_union_field,
            ToolDefinitionError,
            id="typeddict_with_union_field",
        ),
        pytest.param(
            func_takes_optional_typeddict_non_strict,
            ToolDefinitionError,
            id="optional_typeddict_non_strict",
        ),
    ],
)
def test_typeddict_errors_raise_tool_definition_error(func_under_test, exception_type):
    """Test that various TypedDict error scenarios raise ToolDefinitionError."""
    with pytest.raises(exception_type):
        ToolCatalog.create_tool_definition(func_under_test, "1.0")
