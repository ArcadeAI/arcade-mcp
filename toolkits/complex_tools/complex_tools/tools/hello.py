import json
from enum import Enum
from typing import Annotated, Any

import jsonschema
from arcade_core.errors import RetryableToolError
from arcade_tdk import tool


class ToolMode(str, Enum):
    """Mode of operation for API wrapper tools."""

    GET_REQUEST_SCHEMA = "get_request_schema"
    EXECUTE = "execute"


# OpenAPI schema for a complex user creation request
USER_CREATE_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["user", "metadata"],
    "properties": {
        "user": {
            "type": "object",
            "required": ["email", "profile"],
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "User's email address",
                },
                "username": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]{3,20}$",
                    "description": "Username (3-20 alphanumeric characters, underscores, or hyphens)",
                },
                "profile": {
                    "type": "object",
                    "required": ["firstName", "lastName"],
                    "properties": {
                        "firstName": {"type": "string", "minLength": 1, "maxLength": 50},
                        "lastName": {"type": "string", "minLength": 1, "maxLength": 50},
                        "age": {"type": "integer", "minimum": 18, "maximum": 120},
                        "phoneNumber": {
                            "type": "string",
                            "pattern": "^\\+?[1-9]\\d{1,14}$",
                            "description": "Phone number in E.164 format",
                        },
                    },
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "notifications": {
                            "oneOf": [
                                {
                                    "type": "object",
                                    "required": ["type", "email"],
                                    "properties": {
                                        "type": {"type": "string", "enum": ["email"]},
                                        "email": {"type": "string", "format": "email"},
                                        "frequency": {
                                            "type": "string",
                                            "enum": ["daily", "weekly", "monthly"],
                                            "default": "weekly",
                                        },
                                    },
                                },
                                {
                                    "type": "object",
                                    "required": ["type", "phoneNumber"],
                                    "properties": {
                                        "type": {"type": "string", "enum": ["sms"]},
                                        "phoneNumber": {"type": "string"},
                                    },
                                },
                            ]
                        },
                        "theme": {
                            "type": "string",
                            "enum": ["light", "dark", "auto"],
                            "default": "auto",
                        },
                        "language": {
                            "type": "string",
                            "enum": ["en", "es", "fr", "de", "pt", "zh"],
                            "default": "en",
                        },
                    },
                },
            },
        },
        "metadata": {
            "type": "object",
            "required": ["source"],
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["web", "mobile", "api", "admin"],
                    "description": "Source of the user creation",
                },
                "referralCode": {"type": "string", "pattern": "^[A-Z0-9]{6,10}$"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 0,
                    "maxItems": 10,
                },
            },
        },
    },
}


# OpenAPI schema for a complex order creation request
ORDER_CREATE_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["order", "payment", "shipping"],
    "properties": {
        "order": {
            "type": "object",
            "required": ["items", "customerId"],
            "properties": {
                "customerId": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of the customer placing the order",
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "required": ["productId", "quantity"],
                        "properties": {
                            "productId": {"type": "string", "format": "uuid"},
                            "quantity": {"type": "integer", "minimum": 1, "maximum": 100},
                            "customization": {
                                "anyOf": [
                                    {
                                        "type": "object",
                                        "required": ["type", "color", "size"],
                                        "properties": {
                                            "type": {"type": "string", "enum": ["clothing"]},
                                            "color": {
                                                "type": "string",
                                                "enum": [
                                                    "red",
                                                    "blue",
                                                    "green",
                                                    "black",
                                                    "white",
                                                ],
                                            },
                                            "size": {
                                                "type": "string",
                                                "enum": ["XS", "S", "M", "L", "XL", "XXL"],
                                            },
                                        },
                                    },
                                    {
                                        "type": "object",
                                        "required": ["type", "engraving"],
                                        "properties": {
                                            "type": {"type": "string", "enum": ["jewelry"]},
                                            "engraving": {
                                                "type": "string",
                                                "maxLength": 50,
                                            },
                                        },
                                    },
                                    {
                                        "type": "object",
                                        "required": ["type"],
                                        "properties": {
                                            "type": {"type": "string", "enum": ["electronics"]},
                                            "warranty": {
                                                "type": "string",
                                                "enum": ["1year", "2year", "3year"],
                                            },
                                        },
                                    },
                                ]
                            },
                        },
                    },
                },
                "discountCode": {
                    "type": "string",
                    "pattern": "^[A-Z0-9]{4,12}$",
                },
            },
        },
        "payment": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["method", "cardNumber"],
                    "properties": {
                        "method": {"type": "string", "enum": ["credit_card"]},
                        "cardNumber": {
                            "type": "string",
                            "pattern": "^[0-9]{16}$",
                        },
                        "cvv": {"type": "string", "pattern": "^[0-9]{3,4}$"},
                        "expiryDate": {
                            "type": "string",
                            "pattern": "^(0[1-9]|1[0-2])/[0-9]{2}$",
                        },
                    },
                },
                {
                    "type": "object",
                    "required": ["method", "accountId"],
                    "properties": {
                        "method": {"type": "string", "enum": ["paypal"]},
                        "accountId": {"type": "string", "format": "email"},
                    },
                },
                {
                    "type": "object",
                    "required": ["method", "walletId"],
                    "properties": {
                        "method": {"type": "string", "enum": ["crypto"]},
                        "walletId": {"type": "string", "pattern": "^0x[a-fA-F0-9]{40}$"},
                        "currency": {
                            "type": "string",
                            "enum": ["BTC", "ETH", "USDT"],
                            "default": "ETH",
                        },
                    },
                },
            ]
        },
        "shipping": {
            "type": "object",
            "required": ["address", "method"],
            "properties": {
                "address": {
                    "type": "object",
                    "required": ["street", "city", "country", "postalCode"],
                    "properties": {
                        "street": {"type": "string", "minLength": 1, "maxLength": 100},
                        "street2": {"type": "string", "maxLength": 100},
                        "city": {"type": "string", "minLength": 1, "maxLength": 50},
                        "state": {"type": "string", "maxLength": 50},
                        "country": {
                            "type": "string",
                            "pattern": "^[A-Z]{2}$",
                            "description": "ISO 3166-1 alpha-2 country code",
                        },
                        "postalCode": {"type": "string", "maxLength": 20},
                    },
                },
                "method": {
                    "type": "string",
                    "enum": ["standard", "express", "overnight", "international"],
                },
                "instructions": {"type": "string", "maxLength": 500},
            },
        },
    },
}


def validate_json_against_schema(
    json_data: dict[str, Any], schema: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate JSON data against an OpenAPI/JSON Schema using the jsonschema library.
    This provides full JSON Schema Draft 7 validation including:
    - Required fields, types, enums
    - Pattern validation (regex)
    - Format validation (email, uuid, date-time, etc.)
    - Min/max length and values
    - oneOf, anyOf, allOf
    - And all other JSON Schema features

    Returns (is_valid, error_message).
    """
    try:
        # Use Draft7Validator with format checking enabled
        validator = jsonschema.Draft7Validator(
            schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER
        )
        # Validate and get the first error if any
        errors = list(validator.iter_errors(json_data))
        if errors:
            error = errors[0]
            error_path = ".".join(str(p) for p in error.path) if error.path else "root"
            return False, f"{error.message} at {error_path}"
        return True, None
    except jsonschema.SchemaError as e:
        # Schema itself is invalid
        return False, f"Invalid schema: {e.message}"
    except Exception as e:
        return False, f"Validation error: {e!s}"


@tool
def create_user(
    mode: Annotated[
        ToolMode,
        "Operation mode: 'get_request_schema' returns the OpenAPI spec for the request body, 'execute' performs the actual user creation",
    ],
    request_body: Annotated[
        str | None,
        "Stringified JSON representing the user creation request body. Required when mode is 'execute', ignored when mode is 'get_request_schema'",
    ] = None,
) -> dict[str, Any]:
    """
    Create a new user in the system.

    Note: Understanding the request schema is necessary to properly create the stringified
    JSON input object for execution.

    Modes:
    - GET_REQUEST_SCHEMA: Returns the schema. Only call if you don't already have it.
      Do NOT call repeatedly if you already received the schema.
    - EXECUTE: Creates the user with the provided request body JSON.

    If you need the schema, call with mode='get_request_schema' ONCE, then execute.
    """
    if mode == ToolMode.GET_REQUEST_SCHEMA:
        return {
            "request_body_schema": USER_CREATE_REQUEST_SCHEMA,
            "instructions": (
                "Use the request_body_schema to construct a valid JSON object. "
                "Once you have populated the object following the schema structure and requirements, "
                "call this tool again with mode='execute' and the stringified JSON as the request_body parameter. "
                "Do NOT call the schema mode again - you already have the schema now."
            ),
        }

    # Mode is EXECUTE - validate request body
    if not request_body:
        raise RetryableToolError(
            message="Request body is required when mode is 'execute'",
            developer_message="The request_body parameter was null or empty",
            additional_prompt_content=(
                "The request body is required to create a user. "
                "If you need to see the required structure, you can call this tool with "
                "mode='get_request_schema' first. Here's the schema:\n\n"
                f"{json.dumps(USER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        )

    # Parse JSON
    try:
        request_data = json.loads(request_body)
    except json.JSONDecodeError as e:
        raise RetryableToolError(
            message=f"Invalid JSON in request body: {e!s}",
            developer_message=f"JSON parsing failed: {e!s}",
            additional_prompt_content=(
                f"The request body contains invalid JSON. Error: {e!s}\n\n"
                "Please provide a valid JSON string. If you need the schema specification, "
                "you can call this tool with mode='get_request_schema'. "
                f"Schema:\n\n{json.dumps(USER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        ) from e

    # Validate against schema
    is_valid, validation_error = validate_json_against_schema(
        request_data, USER_CREATE_REQUEST_SCHEMA
    )
    if not is_valid:
        raise RetryableToolError(
            message=f"Request body validation failed: {validation_error}",
            developer_message=f"Schema validation error: {validation_error}",
            additional_prompt_content=(
                f"The request body does not match the required schema. Error: {validation_error}\n\n"
                "If you need the complete specification, you can call this tool with "
                "mode='get_request_schema'. Schema:\n\n"
                f"{json.dumps(USER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        )

    # Simulate successful user creation
    user_id = "usr_" + request_data["user"]["email"].split("@")[0]
    return {
        "success": True,
        "userId": user_id,
        "message": f"User '{request_data['user'].get('username', 'N/A')}' created successfully",
        "email": request_data["user"]["email"],
        "profile": request_data["user"]["profile"],
        "createdAt": "2025-10-13T10:30:00Z",
    }


@tool
def create_order(
    mode: Annotated[
        ToolMode,
        "Operation mode: 'get_request_schema' returns the OpenAPI spec for the request body, 'execute' performs the actual order creation",
    ],
    priority: Annotated[
        str,
        "Order priority level. Required when mode is 'execute', ignored when mode is 'get_request_schema'. Valid values: 'low', 'normal', 'high', 'urgent'",
    ],
    notification_email: Annotated[
        str,
        "Email address for order notifications. Required when mode is 'execute', ignored when mode is 'get_request_schema'",
    ],
    request_body: Annotated[
        str | None,
        "Stringified JSON representing the order creation request body. Required when mode is 'execute', ignored when mode is 'get_request_schema'",
    ] = None,
    gift_message: Annotated[
        str | None,
        "Optional gift message to include with the order. Only used when mode is 'execute'",
    ] = None,
) -> dict[str, Any]:
    """
    Create a new order in the e-commerce system.

    Note: Understanding the request schema is necessary to properly create the stringified
    JSON input object for execution.

    Modes:
    - GET_REQUEST_SCHEMA: Returns the schema. Only call if you don't already have it.
      Do NOT call repeatedly if you already received the schema.
    - EXECUTE: Creates the order with request body JSON, priority, and notification_email.
      Priority must be: 'low', 'normal', 'high', or 'urgent'.

    If you need the schema, call with mode='get_request_schema' ONCE, then execute.
    """
    if mode == ToolMode.GET_REQUEST_SCHEMA:
        return {
            "request_body_schema": ORDER_CREATE_REQUEST_SCHEMA,
            "instructions": (
                "Use the request_body_schema to construct a valid JSON object. "
                "Once you have populated the object following the schema structure and requirements, "
                "call this tool again with mode='execute', provide valid values for 'priority' and "
                "'notification_email' parameters, and the stringified JSON as the request_body parameter. "
                "Do NOT call the schema mode again - you already have the schema now."
            ),
        }

    # Mode is EXECUTE - validate query parameters
    valid_priorities = ["low", "normal", "high", "urgent"]
    if not priority or priority not in valid_priorities:
        raise RetryableToolError(
            message=f"Invalid or missing priority parameter. Must be one of: {', '.join(valid_priorities)}",
            developer_message=f"Priority parameter validation failed. Received: {priority}",
            additional_prompt_content=(
                f"The 'priority' parameter is required when executing order creation. "
                f"Valid values are: {', '.join(valid_priorities)}. "
                "Please call this tool again with a valid priority value."
            ),
        )

    if not notification_email or "@" not in notification_email:
        raise RetryableToolError(
            message="Invalid or missing notification_email parameter. Must be a valid email address",
            developer_message=f"Notification email validation failed. Received: {notification_email}",
            additional_prompt_content=(
                "The 'notification_email' parameter is required when executing order creation "
                "and must be a valid email address. Please provide a valid email address."
            ),
        )

    # Validate request body
    if not request_body:
        raise RetryableToolError(
            message="Request body is required when mode is 'execute'",
            developer_message="The request_body parameter was null or empty",
            additional_prompt_content=(
                "The request body is required to create an order. "
                "If you need to see the required structure, you can call this tool with "
                "mode='get_request_schema' first. Here's the schema:\n\n"
                f"{json.dumps(ORDER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        )

    # Parse JSON
    try:
        request_data = json.loads(request_body)
    except json.JSONDecodeError as e:
        raise RetryableToolError(
            message=f"Invalid JSON in request body: {e!s}",
            developer_message=f"JSON parsing failed: {e!s}",
            additional_prompt_content=(
                f"The request body contains invalid JSON. Error: {e!s}\n\n"
                "Please provide a valid JSON string. If you need the schema specification, "
                "you can call this tool with mode='get_request_schema'. "
                f"Schema:\n\n{json.dumps(ORDER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        ) from e

    # Validate against schema
    is_valid, validation_error = validate_json_against_schema(
        request_data, ORDER_CREATE_REQUEST_SCHEMA
    )
    if not is_valid:
        raise RetryableToolError(
            message=f"Request body validation failed: {validation_error}",
            developer_message=f"Schema validation error: {validation_error}",
            additional_prompt_content=(
                f"The request body does not match the required schema. Error: {validation_error}\n\n"
                "If you need the complete specification, you can call this tool with "
                "mode='get_request_schema'. Schema:\n\n"
                f"{json.dumps(ORDER_CREATE_REQUEST_SCHEMA, indent=2)}"
            ),
        )

    # Simulate successful order creation
    order_id = "ord_" + request_data["order"]["customerId"][:8]
    total_items = sum(item["quantity"] for item in request_data["order"]["items"])

    result: dict[str, Any] = {
        "success": True,
        "orderId": order_id,
        "customerId": request_data["order"]["customerId"],
        "totalItems": total_items,
        "priority": priority,
        "notificationEmail": notification_email,
        "paymentMethod": request_data["payment"]["method"],
        "shippingMethod": request_data["shipping"]["method"],
        "shippingAddress": request_data["shipping"]["address"],
        "estimatedDelivery": "2025-10-20T10:00:00Z",
        "createdAt": "2025-10-13T10:30:00Z",
    }

    if gift_message:
        result["giftMessage"] = gift_message

    return result


@tool
def get_available_products() -> str:
    """
    Retrieve a list of available products with their IDs and details.

    This tool returns static product data that can be used when creating orders.
    Each product includes its UUID, name, category, and available customizations.
    Use the product IDs from this response when building order request bodies.
    """
    products = [
        {
            "productId": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Classic Cotton T-Shirt",
            "category": "clothing",
            "price": 29.99,
            "availableCustomizations": {
                "colors": ["red", "blue", "green", "black", "white"],
                "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
            },
        },
        {
            "productId": "550e8400-e29b-41d4-a716-446655440002",
            "name": "Sterling Silver Bracelet",
            "category": "jewelry",
            "price": 149.99,
            "availableCustomizations": {"engraving": "Up to 50 characters"},
        },
        {
            "productId": "550e8400-e29b-41d4-a716-446655440003",
            "name": "Wireless Headphones",
            "category": "electronics",
            "price": 199.99,
            "availableCustomizations": {"warranty": ["1year", "2year", "3year"]},
        },
        {
            "productId": "550e8400-e29b-41d4-a716-446655440004",
            "name": "Denim Jacket",
            "category": "clothing",
            "price": 89.99,
            "availableCustomizations": {
                "colors": ["blue", "black"],
                "sizes": ["S", "M", "L", "XL"],
            },
        },
        {
            "productId": "550e8400-e29b-41d4-a716-446655440005",
            "name": "Gold Necklace",
            "category": "jewelry",
            "price": 299.99,
            "availableCustomizations": {"engraving": "Up to 50 characters"},
        },
    ]

    return json.dumps({"products": products, "totalCount": len(products)}, indent=2)


@tool
def get_customer_info(
    customer_email: Annotated[str, "Email address of the customer to look up"],
) -> str:
    """
    Retrieve customer information by email address.

    This tool returns customer details including their UUID, profile information,
    and preferences. The customer ID can be used when creating orders or users.
    This is a simplified tool that returns static data for demonstration purposes.
    """
    # Simulate customer lookup with static data
    customer_data = {
        "customerId": "550e8400-e29b-41d4-a716-446655440100",
        "email": customer_email,
        "profile": {
            "firstName": "John",
            "lastName": "Doe",
            "phoneNumber": "+14155551234",
        },
        "preferences": {"notifications": {"type": "email", "frequency": "weekly"}},
        "accountStatus": "active",
        "memberSince": "2024-01-15T08:00:00Z",
    }

    return json.dumps(customer_data, indent=2)


@tool
def get_discount_codes() -> str:
    """
    Retrieve a list of currently active discount codes.

    This tool returns available discount codes that can be applied to orders,
    including their codes, descriptions, and discount percentages.
    Use these codes in the order creation request body.
    """
    discount_codes = [
        {
            "code": "SUMMER2025",
            "description": "Summer sale - 20% off all items",
            "discountPercentage": 20,
            "validUntil": "2025-08-31T23:59:59Z",
        },
        {
            "code": "WELCOME10",
            "description": "New customer welcome discount",
            "discountPercentage": 10,
            "validUntil": "2025-12-31T23:59:59Z",
        },
        {
            "code": "FLASHSALE",
            "description": "Flash sale - 30% off",
            "discountPercentage": 30,
            "validUntil": "2025-10-20T23:59:59Z",
        },
    ]

    return json.dumps(
        {"discountCodes": discount_codes, "totalCount": len(discount_codes)}, indent=2
    )


@tool
def get_shipping_rates(
    country_code: Annotated[str, "ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'CA')"],
) -> str:
    """
    Get available shipping rates and estimated delivery times for a specific country.

    This tool returns shipping options (standard, express, overnight, international)
    with their costs and estimated delivery times based on the destination country.
    Use this information to choose an appropriate shipping method when creating orders.
    """
    # Simulate shipping rates based on country
    shipping_methods: list[dict[str, Any]] = [
        {
            "method": "standard",
            "cost": 5.99,
            "estimatedDays": "5-7",
            "description": "Standard ground shipping",
        },
        {
            "method": "express",
            "cost": 15.99,
            "estimatedDays": "2-3",
            "description": "Express shipping",
        },
        {
            "method": "overnight",
            "cost": 29.99,
            "estimatedDays": "1",
            "description": "Next-day delivery",
        },
    ]

    if country_code.upper() not in ["US", "CA"]:
        international_method = {
            "method": "international",
            "cost": 39.99,
            "estimatedDays": "10-14",
            "description": "International shipping with customs handling",
        }
        shipping_methods.append(international_method)

    shipping_options = {
        "countryCode": country_code.upper(),
        "shippingMethods": shipping_methods,
    }

    return json.dumps(shipping_options, indent=2)
