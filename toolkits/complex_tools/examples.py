"""
Examples demonstrating the complex_tools toolkit usage.

This file shows how to use the dual-mode API wrapper tools.
"""

import json

from complex_tools.tools.hello import (
    ToolMode,
    create_order,
    create_user,
    get_available_products,
    get_customer_info,
    get_discount_codes,
    get_shipping_rates,
)


def example_user_creation() -> None:
    """Example: Creating a user with the dual-mode workflow."""
    print("=" * 80)
    print("EXAMPLE 1: Creating a User")
    print("=" * 80)

    # Step 1: Get the schema
    print("\n1. Getting request schema...")
    schema_response = create_user(mode=ToolMode.GET_REQUEST_SCHEMA)
    print(f"Instructions: {schema_response['instructions']}")
    print(
        f"Schema retrieved (showing required fields): {schema_response['request_body_schema']['required']}"
    )

    # Step 2: Build the request body
    print("\n2. Building request body...")
    user_request = {
        "user": {
            "email": "john.doe@example.com",
            "username": "johndoe123",
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "age": 30,
                "phoneNumber": "+14155551234",
            },
            "preferences": {
                "notifications": {
                    "type": "email",
                    "email": "john.doe@example.com",
                    "frequency": "weekly",
                },
                "theme": "dark",
                "language": "en",
            },
        },
        "metadata": {"source": "web", "tags": ["new-user", "premium"]},
    }

    request_body_json = json.dumps(user_request)
    print(f"Request body built: {request_body_json[:100]}...")

    # Step 3: Execute the creation
    print("\n3. Executing user creation...")
    result = create_user(mode=ToolMode.EXECUTE, request_body=request_body_json)
    print(f"Success! Result:\n{json.dumps(result, indent=2)}")


def example_order_creation() -> None:
    """Example: Creating an order with query parameters."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Creating an Order")
    print("=" * 80)

    # Step 1: Get helper data
    print("\n1. Getting available products...")
    products = get_available_products()
    products_data = json.loads(products)
    print(f"Found {products_data['totalCount']} products")

    print("\n2. Getting customer info...")
    customer = get_customer_info(customer_email="customer@example.com")
    customer_data = json.loads(customer)
    print(f"Customer ID: {customer_data['customerId']}")

    print("\n3. Getting discount codes...")
    discounts = get_discount_codes()
    discounts_data = json.loads(discounts)
    print(f"Available discount: {discounts_data['discountCodes'][0]['code']}")

    print("\n4. Getting shipping rates for US...")
    shipping = get_shipping_rates(country_code="US")
    shipping_data = json.loads(shipping)
    print(f"Cheapest shipping: {shipping_data['shippingMethods'][0]['method']}")

    # Step 2: Get the schema
    print("\n5. Getting order request schema...")
    schema_response = create_order(
        mode=ToolMode.GET_REQUEST_SCHEMA,
        priority="normal",  # Ignored in this mode
        notification_email="test@example.com",  # Ignored in this mode
    )
    print(f"Instructions: {schema_response['instructions'][:100]}...")
    print(
        f"Schema retrieved (showing required fields): {schema_response['request_body_schema']['required']}"
    )

    # Step 3: Build the order request
    print("\n6. Building order request...")
    order_request = {
        "order": {
            "customerId": customer_data["customerId"],
            "items": [
                {
                    "productId": products_data["products"][0]["productId"],
                    "quantity": 2,
                    "customization": {"type": "clothing", "color": "blue", "size": "L"},
                }
            ],
            "discountCode": discounts_data["discountCodes"][0]["code"],
        },
        "payment": {
            "method": "credit_card",
            "cardNumber": "4532123456789012",
            "cvv": "123",
            "expiryDate": "12/25",
        },
        "shipping": {
            "address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "country": "US",
                "postalCode": "94102",
            },
            "method": "express",
            "instructions": "Leave at front door",
        },
    }

    request_body_json = json.dumps(order_request)

    # Step 4: Execute the order creation
    print("\n7. Executing order creation...")
    result = create_order(
        mode=ToolMode.EXECUTE,
        priority="high",
        notification_email="customer@example.com",
        request_body=request_body_json,
        gift_message="Happy Birthday!",
    )
    print(f"Success! Result:\n{json.dumps(result, indent=2)}")


def example_error_handling() -> None:
    """Example: Demonstrating error handling with RetryableToolError."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Error Handling")
    print("=" * 80)

    print("\n1. Attempting to create user without request body...")
    try:
        result = create_user(mode=ToolMode.EXECUTE, request_body=None)
    except Exception as e:
        print(f"Error caught: {type(e).__name__}")
        print(f"Message: {e}")
        if hasattr(e, "additional_prompt_content"):
            print(f"\nAdditional prompt content (first 200 chars):")
            print(e.additional_prompt_content[:200] + "...")  # type: ignore[attr-defined]

    print("\n2. Attempting to create user with invalid JSON...")
    try:
        result = create_user(mode=ToolMode.EXECUTE, request_body='{"invalid": json}')
    except Exception as e:
        print(f"Error caught: {type(e).__name__}")
        print(f"Message: {e}")

    print("\n3. Attempting to create user with missing required fields...")
    invalid_request = {"user": {"email": "test@example.com"}}  # Missing profile
    try:
        result = create_user(mode=ToolMode.EXECUTE, request_body=json.dumps(invalid_request))
    except Exception as e:
        print(f"Error caught: {type(e).__name__}")
        print(f"Message: {e}")

    print("\n4. Attempting to create order with invalid priority...")
    try:
        result = create_order(
            mode=ToolMode.EXECUTE,
            priority="super-urgent",  # Invalid
            notification_email="test@example.com",
            request_body='{"test": "data"}',
        )
    except Exception as e:
        print(f"Error caught: {type(e).__name__}")
        print(f"Message: {e}")


if __name__ == "__main__":
    # Run examples
    example_user_creation()
    example_order_creation()
    example_error_handling()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)
