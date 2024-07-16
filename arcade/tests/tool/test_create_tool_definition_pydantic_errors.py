from typing import Annotated

import pytest
from pydantic import Field

from arcade.sdk.tool import tool
from arcade.tool.catalog import ToolCatalog
from arcade.tool.errors import ToolDefinitionError


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


@pytest.mark.parametrize(
    "func_under_test, exception_type",
    [
        pytest.param(
            field_with_literal_default_factory,
            ToolDefinitionError,
            id=field_with_literal_default_factory.__name__,
        ),
    ],
)
def test_missing_info_raises_error(func_under_test, exception_type):
    with pytest.raises(exception_type):
        ToolCatalog.create_tool_definition(func_under_test, "1.0")
