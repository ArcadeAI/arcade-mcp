from typing import Annotated

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.schema import (
    InputParameter,
    ToolInput,
    ToolOutput,
    ValueSchema,
)
from arcade_tdk import tool
from pydantic import BaseModel, Field


class ProductOutputModel(BaseModel):
    product_name: str
    """The name of the product"""
    price: int
    """The price of the product"""
    stock_quantity: int
    """The stock quantity of the product"""

    class Config:
        extra = "forbid"


@tool(desc="A function that returns a Pydantic model")
def func_returns_pydantic_model() -> Annotated[
    ProductOutputModel, "The product, price, and quantity"
]:
    """
    Returns a ProductOutput Pydantic model with sample data.

    Returns:
        ProductOutput: The product, price, and quantity.

    Example:
        >>> func_returns_pydantic_model()
        ProductOutput(product_name='Product 1', price=100, stock_quantity=1000)
    """
    return ProductOutputModel(
        product_name="Product 1",
        price=100,
        stock_quantity=1000,
    )


@tool(desc="A function that accepts a required Pydantic Field with a description")
def func_takes_pydantic_field_with_description(
    product_name: str = Field(..., description="The name of the product"),
) -> str:
    return product_name


@tool(desc="A function that accepts an optional Pydantic Field")
def func_takes_pydantic_field_optional(
    product_name: str | None = Field(None, description="The name of the product"),
) -> str:
    return product_name if product_name is not None else "Product 1"


@tool(desc="A function that accepts an optional Pydantic Field with bar syntax")
def func_takes_pydantic_field_optional_bar_syntax(
    product_name: str | None = Field(None, description="The name of the product"),
) -> str | None:
    return product_name if product_name is not None else None


@tool(desc="A function that accepts an optional Pydantic Field with union syntax")
def func_takes_pydantic_field_optional_union_syntax(
    product_name: str | None = Field(None, description="The name of the product"),
) -> str:
    return product_name if product_name is not None else "Product 1"


# Annotated[] takes precedence over Field() properties
@tool(desc="A function that accepts an annotated Pydantic Field")
def func_takes_pydantic_field_annotated_description(
    product_name: Annotated[str, "The name of the product"] = Field(
        ..., description="The name of the product???"
    ),
) -> str:
    return product_name


# Annotated[] takes precedence over Field() properties
@tool(desc="A function that accepts an annotated Pydantic Field")
def func_takes_pydantic_field_annotated_name_and_description(
    product_name: Annotated[str, "ProductName", "The name of the product"] = Field(
        ..., title="The name of the product???"
    ),
) -> str:
    return product_name


@tool(desc="A function that accepts a Pydantic Field with a default value")
def func_takes_pydantic_field_default(
    product_name: str = Field(description="The name of the product", default="Product 1"),
) -> str:
    return product_name


@tool(desc="A function that accepts a Pydantic Field with a default value factory")
def func_takes_pydantic_field_default_factory(
    product_name: str = Field(
        default_factory=lambda: "Product 1", description="The name of the product"
    ),
) -> str:
    """
    Accepts a product name with a default value provided by a factory.

    Parameters:
        product_name: The name of the product. Defaults to "Product 1" if not provided.

    Returns:
        str: The product name.

    Example:
        >>> func_takes_pydantic_field_default_factory()
        'Product 1'
    """
    return product_name


# TODO: Function that takes a Pydantic model as an argument: break it down into components? Look at OpenAPI, do they represent nested arguments?
# TODO: Should title and default_value be added to JSON schema?
# TODO: Pydantic Field() properties stretch goal: gt, ge, lt, le, multiple_of, range, regex, max_length, min_length, max_items, min_items, unique_items, exclusive_maximum, exclusive_minimum, title?


### A complex, real-world example
class ProductFilter(BaseModel):
    column: str = Field(..., description="The column to filter on")


class FilterRating(ProductFilter):
    greater_than: int = Field(..., description="The rating to filter greater than", gt=0, lt=5)


class FilterPriceGreaterThan(ProductFilter):
    price: int = Field(..., description="The price to filter greater than", gt=0)


class FilterPriceLessThan(ProductFilter):
    price: int = Field(..., description="The price to filter less than", gt=0)


class ProductSearch(BaseModel):
    column: str = Field(..., description="The column to search in")
    query: str = Field(..., description="The query to search for")
    filter_operation: FilterRating | None = Field(
        default=None,
        description="The filter operation to apply (rating or price filter).",
    )
    highest_price: FilterPriceGreaterThan | None = Field(
        default=None, description="The highest price to filter by"
    )
    lowest_price: FilterPriceLessThan | None = Field(
        default=None, description="The lowest price to filter by"
    )


class ProductOutput(BaseModel):
    product_name: str = Field(..., description="The name of the product")
    price: int = Field(..., description="The price of the product")
    stock_quantity: int = Field(..., description="The stock quantity of the product")


@tool
def read_products(
    action: Annotated[ProductSearch, "The search query to perform"],
    cols: list[str] = Field(
        default_factory=lambda: ["Product Name", "Price", "Stock Quantity"],
        description="The columns to return",
    ),
) -> Annotated[list[ProductOutput], "Data with the selected columns"]:
    """
    Used to search through products by name and filter by rating or price.

    Parameters:
        action: The search query to perform, as a ProductSearch model.
        cols: The columns to return. Defaults to ["Product Name", "Price", "Stock Quantity"].

    Returns:
        list[ProductOutput]: Data with the selected columns.

    Raises:
        None

    Example:
        >>> await read_products(ProductSearch(query="Widget"), ["Product Name", "Price"])
    """
    # This is a stub implementation for testing; in real code, this would query a database or service.
    return [
        ProductOutput(product_name="Widget", price=100, stock_quantity=50),
        ProductOutput(product_name="Gadget", price=150, stock_quantity=20),
    ]


@pytest.mark.parametrize(
    "func_under_test, expected_tool_def_fields",
    [
        pytest.param(
            func_returns_pydantic_model,
            {
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="json",
                        enum=None,
                        properties={
                            "product_name": ValueSchema(val_type="string", enum=None),
                            "price": ValueSchema(val_type="integer", enum=None),
                            "stock_quantity": ValueSchema(val_type="integer", enum=None),
                        },
                    ),
                    available_modes=["value", "error"],
                    description="The product, price, and quantity",
                )
            },
            id="func_returns_pydantic_model",
        ),
        pytest.param(
            func_takes_pydantic_field_with_description,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=True,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_with_description",
        ),
        pytest.param(
            func_takes_pydantic_field_optional,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_optional",
        ),
        pytest.param(
            func_takes_pydantic_field_optional_bar_syntax,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_optional_bar_syntax",
        ),
        pytest.param(
            func_takes_pydantic_field_optional_union_syntax,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_optional_union_syntax",
        ),
        pytest.param(
            func_takes_pydantic_field_annotated_description,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",  # Annotated[] takes precedence over Field() properties
                            required=True,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_annotated_description",
        ),
        pytest.param(
            func_takes_pydantic_field_annotated_name_and_description,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="ProductName",
                            description="The name of the product",  # Annotated[] takes precedence over Field() properties
                            required=True,
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                )
            },
            id="func_takes_pydantic_field_annotated_name_and_description",
        ),
        pytest.param(
            func_takes_pydantic_field_default,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=False,  # Because it has a default value
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
            },
            id="func_takes_pydantic_field_default",
        ),
        pytest.param(
            func_takes_pydantic_field_default_factory,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_name",
                            description="The name of the product",
                            required=False,  # Because it has a default value factory
                            inferrable=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
            },
            id="func_takes_pydantic_field_default_factory",
        ),
        pytest.param(
            read_products,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="action",
                            description="The search query to perform",
                            required=True,
                            inferrable=True,
                            value_schema=ValueSchema(
                                val_type="json",
                                enum=None,
                                properties={
                                    "column": ValueSchema(val_type="string", enum=None),
                                    "query": ValueSchema(val_type="string", enum=None),
                                    "filter_operation": ValueSchema(
                                        val_type="json",
                                        enum=None,
                                        properties={
                                            "column": ValueSchema(val_type="string", enum=None),
                                            "greater_than": ValueSchema(
                                                val_type="integer", enum=None
                                            ),
                                        },
                                    ),
                                    "highest_price": ValueSchema(
                                        val_type="json",
                                        enum=None,
                                        properties={
                                            "column": ValueSchema(val_type="string", enum=None),
                                            "price": ValueSchema(val_type="integer", enum=None),
                                        },
                                    ),
                                    "lowest_price": ValueSchema(
                                        val_type="json",
                                        enum=None,
                                        properties={
                                            "column": ValueSchema(val_type="string", enum=None),
                                            "price": ValueSchema(val_type="integer", enum=None),
                                        },
                                    ),
                                },
                            ),
                        ),
                        InputParameter(
                            name="cols",
                            description="The columns to return",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(
                                val_type="array", inner_val_type="string", enum=None
                            ),
                        ),
                    ]
                ),
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="array",
                        inner_val_type="json",
                        enum=None,
                        inner_properties={
                            "product_name": ValueSchema(val_type="string", enum=None),
                            "price": ValueSchema(val_type="integer", enum=None),
                            "stock_quantity": ValueSchema(val_type="integer", enum=None),
                        },
                    ),
                    available_modes=["value", "error"],
                    description="Data with the selected columns",
                ),
            },
            id="read_products",
        ),
    ],
)
def test_create_tool_def_from_pydantic(func_under_test, expected_tool_def_fields):
    tool_def = ToolCatalog.create_tool_definition(func_under_test, "1.0")

    for field, expected_value in expected_tool_def_fields.items():
        assert getattr(tool_def, field) == expected_value
