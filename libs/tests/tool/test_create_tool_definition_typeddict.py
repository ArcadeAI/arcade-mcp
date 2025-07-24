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
from typing_extensions import TypedDict


class ProductOutputDict(TypedDict):
    """A product with its details."""

    product_name: str
    price: int
    stock_quantity: int


@tool(desc="A function that returns a TypedDict")
def func_returns_typeddict() -> Annotated[ProductOutputDict, "The product, price, and quantity"]:
    """Returns a ProductOutput TypedDict with sample data."""
    return ProductOutputDict(
        product_name="Product 1",
        price=100,
        stock_quantity=1000,
    )


@tool(desc="A function that returns a list of TypedDict")
def func_returns_list_of_typeddict() -> Annotated[
    list[ProductOutputDict], "The product, price, and quantity"
]:
    """Returns a list of ProductOutput TypedDict with sample data."""
    return [
        ProductOutputDict(
            product_name="Product 1",
            price=100,
            stock_quantity=1000,
        ),
        ProductOutputDict(
            product_name="Product 2",
            price=200,
            stock_quantity=2000,
        ),
    ]


@tool(desc="A function that accepts an optional TypedDict parameter")
def func_takes_optional_typeddict_param(
    product: Annotated[ProductOutputDict | None, "The product information"] = None,
) -> str:
    if product is None:
        return "No product provided"
    return f"{product['product_name']} for price {product['price']}"


class ProductOutputDictWithOptional(TypedDict):
    """A product with its details."""

    product_name: str
    price: int
    stock_quantity: int
    description: str | None


@tool(desc="A function that returns a TypedDict with an optional field")
def func_returns_typeddict_with_optional_field() -> Annotated[
    ProductOutputDictWithOptional, "The product, price, and quantity"
]:
    """
    Returns a ProductOutput TypedDict with sample data.
    """
    return ProductOutputDictWithOptional(
        product_name="Product 1",
        price=100,
        stock_quantity=1000,
    )


class ProductListDict(TypedDict):
    """A collection of products."""

    category: str
    products: list[str]


@tool(desc="A function that accepts a TypedDict with list fields")
def func_takes_typeddict_with_list_field(
    product_list: Annotated[ProductListDict | None, "The product collection"] = None,
) -> Annotated[list[str], "The product names."]:
    """Accepts a product list with category information."""
    if product_list is None:
        return ["Laptop", "Phone"]
    return product_list["products"]


### TypedDict with total=False for optional fields
class OptionalFieldsDict(TypedDict, total=False):
    """A TypedDict with all optional fields."""

    name: str
    description: str
    price: int


@tool(desc="A function that returns a TypedDict with optional fields")
def func_returns_typeddict_optional_fields() -> Annotated[
    OptionalFieldsDict, "Product info with optional fields"
]:
    """Returns a TypedDict where some fields may be missing."""
    return OptionalFieldsDict(name="Product 1")


### Nested TypedDict example
class AddressDict(TypedDict):
    """Address information."""

    street: str
    city: str
    zip_code: str


class CustomerDict(TypedDict):
    """Customer information with nested address."""

    name: str
    email: str
    address: AddressDict


@tool(desc="A function that returns nested Typedicts")
def func_returns_nested_typedicts() -> Annotated[CustomerDict, "Customer information with address"]:
    """Returns a nested TypedDict structure."""
    return CustomerDict(
        name="John Doe",
        email="john@example.com",
        address=AddressDict(
            street="123 Main St",
            city="Anytown",
            zip_code="12345",
        ),
    )


@pytest.mark.parametrize(
    "func_under_test, expected_tool_def_fields",
    [
        pytest.param(
            func_returns_typeddict,
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
            id="func_returns_typeddict",
        ),
        pytest.param(
            func_returns_list_of_typeddict,
            {
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
                    description="The product, price, and quantity",
                )
            },
            id="func_returns_list_of_typeddict",
        ),
        pytest.param(
            func_takes_optional_typeddict_param,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product",
                            description="The product information",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(
                                val_type="json",
                                enum=None,
                                properties={
                                    "product_name": ValueSchema(val_type="string", enum=None),
                                    "price": ValueSchema(val_type="integer", enum=None),
                                    "stock_quantity": ValueSchema(val_type="integer", enum=None),
                                },
                            ),
                        )
                    ]
                )
            },
            id="func_takes_optional_typeddict_param",
        ),
        pytest.param(
            func_returns_typeddict_with_optional_field,
            {
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="json",
                        enum=None,
                        properties={
                            "product_name": ValueSchema(val_type="string", enum=None),
                            "price": ValueSchema(val_type="integer", enum=None),
                            "stock_quantity": ValueSchema(val_type="integer", enum=None),
                            "description": ValueSchema(val_type="string", enum=None, nullable=True),
                        },
                    ),
                    available_modes=["value", "error"],
                    description="The product, price, and quantity",
                )
            },
            id="func_returns_typeddict_with_optional_field",
        ),
        pytest.param(
            func_takes_typeddict_with_list_field,
            {
                "input": ToolInput(
                    parameters=[
                        InputParameter(
                            name="product_list",
                            description="The product collection",
                            required=False,
                            inferrable=True,
                            value_schema=ValueSchema(
                                val_type="json",
                                enum=None,
                                properties={
                                    "category": ValueSchema(val_type="string", enum=None),
                                    "products": ValueSchema(
                                        val_type="array", inner_val_type="string", enum=None
                                    ),
                                },
                            ),
                        )
                    ]
                ),
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="array",
                        inner_val_type="string",
                        enum=None,
                    ),
                    available_modes=["value", "error"],
                    description="The product names.",
                ),
            },
            id="func_takes_typeddict_with_list_field",
        ),
        pytest.param(
            func_returns_typeddict_optional_fields,
            {
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="json",
                        enum=None,
                        properties={
                            "name": ValueSchema(val_type="string", enum=None),
                            "description": ValueSchema(val_type="string", enum=None),
                            "price": ValueSchema(val_type="integer", enum=None),
                        },
                    ),
                    available_modes=["value", "error"],
                    description="Product info with optional fields",
                )
            },
            id="func_returns_typeddict_optional_fields",
        ),
        pytest.param(
            func_returns_nested_typedicts,
            {
                "output": ToolOutput(
                    value_schema=ValueSchema(
                        val_type="json",
                        enum=None,
                        properties={
                            "name": ValueSchema(val_type="string", enum=None),
                            "email": ValueSchema(val_type="string", enum=None),
                            "address": ValueSchema(
                                val_type="json",
                                enum=None,
                                properties={
                                    "street": ValueSchema(val_type="string", enum=None),
                                    "city": ValueSchema(val_type="string", enum=None),
                                    "zip_code": ValueSchema(val_type="string", enum=None),
                                },
                            ),
                        },
                    ),
                    available_modes=["value", "error"],
                    description="Customer information with address",
                )
            },
            id="func_returns_nested_typedicts",
        ),
    ],
)
def test_create_tool_def_from_typeddict(func_under_test, expected_tool_def_fields):
    tool_def = ToolCatalog.create_tool_definition(func_under_test, "1.0")

    for field, expected_value in expected_tool_def_fields.items():
        assert getattr(tool_def, field) == expected_value
