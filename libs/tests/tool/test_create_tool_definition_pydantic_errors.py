from typing import Annotated, Union

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError
from arcade_tdk import tool
from pydantic import Field


@tool
def field_with_literal_default_factory(
    cols: list[str] = Field(
        ...,
        description="The columns to return",
        default_factory=["Product Name", "Price", "Stock Quantity"],
    ),
) -> Annotated[str, "Data with the selected columns"]:
    """Used to search through products by name and filter by rating or price."""

    pass


@tool(desc="A function that accepts an optional Pydantic Field with non-strict optional syntax")
def func_takes_pydantic_field_non_strict_optional_bar_syntax(
    product_name: str | int | None = Field(None, description="The name of the product"),
) -> str:
    return product_name


@tool(desc="A function that accepts an optional Pydantic Field with non-strict optional syntax")
def func_takes_pydantic_field_non_strict_optional_union_syntax(
    product_name: Union[str, int, None] = Field(None, description="The name of the product"),
) -> str:
    return product_name


@pytest.mark.parametrize(
    "func_under_test, exception_type",
    [
        pytest.param(
            field_with_literal_default_factory,
            ToolDefinitionError,
            id=field_with_literal_default_factory.__name__,
        ),
        pytest.param(
            func_takes_pydantic_field_non_strict_optional_bar_syntax,
            ToolDefinitionError,
            id=func_takes_pydantic_field_non_strict_optional_bar_syntax.__name__,
        ),
        pytest.param(
            func_takes_pydantic_field_non_strict_optional_union_syntax,
            ToolDefinitionError,
            id=func_takes_pydantic_field_non_strict_optional_union_syntax.__name__,
        ),
    ],
)
def test_missing_info_raises_error(func_under_test, exception_type):
    with pytest.raises(exception_type):
        ToolCatalog.create_tool_definition(func_under_test, "1.0")
