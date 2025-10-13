"""Unit tests for complex_tools toolkit."""

import json

import pytest
from arcade_core.errors import RetryableToolError

from complex_tools.tools.hello import (
    ToolMode,
    create_order,
    create_user,
    get_available_products,
    get_customer_info,
    get_discount_codes,
    get_shipping_rates,
)


class TestCreateUser:
    """Tests for create_user tool."""

    def test_get_request_schema_mode(self) -> None:
        """Test that GET_REQUEST_SCHEMA mode returns the schema."""
        result = create_user(mode=ToolMode.GET_REQUEST_SCHEMA)

        assert "request_body_schema" in result
        assert "instructions" in result
        schema = result["request_body_schema"]
        assert schema["type"] == "object"
        assert "user" in schema["required"]
        assert "metadata" in schema["required"]
        assert "properties" in schema

    def test_execute_without_request_body_raises_error(self) -> None:
        """Test that EXECUTE mode without request body raises RetryableToolError."""
        with pytest.raises(RetryableToolError) as exc_info:
            create_user(mode=ToolMode.EXECUTE, request_body=None)

        assert "Request body is required" in str(exc_info.value)
        assert exc_info.value.can_retry is True

    def test_execute_with_invalid_json_raises_error(self) -> None:
        """Test that EXECUTE mode with invalid JSON raises RetryableToolError."""
        with pytest.raises(RetryableToolError) as exc_info:
            create_user(mode=ToolMode.EXECUTE, request_body='{"invalid": json}')

        assert "Invalid JSON" in str(exc_info.value)

    def test_execute_with_missing_required_fields_raises_error(self) -> None:
        """Test that EXECUTE mode with missing required fields raises RetryableToolError."""
        invalid_request = {"user": {"email": "test@example.com"}}

        with pytest.raises(RetryableToolError) as exc_info:
            create_user(mode=ToolMode.EXECUTE, request_body=json.dumps(invalid_request))

        assert "validation failed" in str(exc_info.value).lower()

    def test_execute_with_valid_request_body_succeeds(self) -> None:
        """Test that EXECUTE mode with valid request body succeeds."""
        valid_request = {
            "user": {
                "email": "john@example.com",
                "username": "johndoe",
                "profile": {"firstName": "John", "lastName": "Doe"},
            },
            "metadata": {"source": "web"},
        }

        result = create_user(mode=ToolMode.EXECUTE, request_body=json.dumps(valid_request))

        assert result["success"] is True
        assert "userId" in result
        assert result["email"] == "john@example.com"


class TestCreateOrder:
    """Tests for create_order tool."""

    def test_get_request_schema_mode(self) -> None:
        """Test that GET_REQUEST_SCHEMA mode returns the schema."""
        result = create_order(
            mode=ToolMode.GET_REQUEST_SCHEMA,
            priority="normal",  # Ignored
            notification_email="test@example.com",  # Ignored
        )

        assert "request_body_schema" in result
        assert "instructions" in result
        schema = result["request_body_schema"]
        assert schema["type"] == "object"
        assert "order" in schema["required"]
        assert "payment" in schema["required"]
        assert "shipping" in schema["required"]

    def test_execute_with_invalid_priority_raises_error(self) -> None:
        """Test that EXECUTE mode with invalid priority raises RetryableToolError."""
        with pytest.raises(RetryableToolError) as exc_info:
            create_order(
                mode=ToolMode.EXECUTE,
                priority="super-urgent",
                notification_email="test@example.com",
                request_body='{"test": "data"}',
            )

        assert "priority" in str(exc_info.value).lower()

    def test_execute_with_invalid_email_raises_error(self) -> None:
        """Test that EXECUTE mode with invalid email raises RetryableToolError."""
        with pytest.raises(RetryableToolError) as exc_info:
            create_order(
                mode=ToolMode.EXECUTE,
                priority="normal",
                notification_email="invalid-email",
                request_body='{"test": "data"}',
            )

        assert "email" in str(exc_info.value).lower()

    def test_execute_without_request_body_raises_error(self) -> None:
        """Test that EXECUTE mode without request body raises RetryableToolError."""
        with pytest.raises(RetryableToolError) as exc_info:
            create_order(
                mode=ToolMode.EXECUTE,
                priority="normal",
                notification_email="test@example.com",
                request_body=None,
            )

        assert "Request body is required" in str(exc_info.value)

    def test_execute_with_valid_request_succeeds(self) -> None:
        """Test that EXECUTE mode with valid request succeeds."""
        valid_request = {
            "order": {
                "customerId": "550e8400-e29b-41d4-a716-446655440000",
                "items": [{"productId": "550e8400-e29b-41d4-a716-446655440001", "quantity": 1}],
            },
            "payment": {"method": "paypal", "accountId": "user@example.com"},
            "shipping": {
                "address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "country": "US",
                    "postalCode": "94102",
                },
                "method": "standard",
            },
        }

        result = create_order(
            mode=ToolMode.EXECUTE,
            priority="normal",
            notification_email="test@example.com",
            request_body=json.dumps(valid_request),
        )

        assert result["success"] is True
        assert "orderId" in result
        assert result["priority"] == "normal"
        assert result["notificationEmail"] == "test@example.com"

    def test_execute_with_gift_message(self) -> None:
        """Test that gift message is included in the response."""
        valid_request = {
            "order": {
                "customerId": "550e8400-e29b-41d4-a716-446655440000",
                "items": [{"productId": "550e8400-e29b-41d4-a716-446655440001", "quantity": 1}],
            },
            "payment": {"method": "paypal", "accountId": "user@example.com"},
            "shipping": {
                "address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "country": "US",
                    "postalCode": "94102",
                },
                "method": "standard",
            },
        }

        result = create_order(
            mode=ToolMode.EXECUTE,
            priority="normal",
            notification_email="test@example.com",
            request_body=json.dumps(valid_request),
            gift_message="Happy Birthday!",
        )

        assert result["giftMessage"] == "Happy Birthday!"


class TestHelperTools:
    """Tests for helper tools."""

    def test_get_available_products(self) -> None:
        """Test that get_available_products returns product data."""
        result = get_available_products()
        data = json.loads(result)

        assert "products" in data
        assert "totalCount" in data
        assert data["totalCount"] > 0
        assert len(data["products"]) == data["totalCount"]

        # Check product structure
        product = data["products"][0]
        assert "productId" in product
        assert "name" in product
        assert "category" in product
        assert "price" in product

    def test_get_customer_info(self) -> None:
        """Test that get_customer_info returns customer data."""
        result = get_customer_info(customer_email="test@example.com")
        data = json.loads(result)

        assert "customerId" in data
        assert "email" in data
        assert data["email"] == "test@example.com"
        assert "profile" in data
        assert "accountStatus" in data

    def test_get_discount_codes(self) -> None:
        """Test that get_discount_codes returns discount data."""
        result = get_discount_codes()
        data = json.loads(result)

        assert "discountCodes" in data
        assert "totalCount" in data
        assert data["totalCount"] > 0

        # Check discount structure
        discount = data["discountCodes"][0]
        assert "code" in discount
        assert "description" in discount
        assert "discountPercentage" in discount
        assert "validUntil" in discount

    def test_get_shipping_rates_us(self) -> None:
        """Test that get_shipping_rates returns US shipping options."""
        result = get_shipping_rates(country_code="US")
        data = json.loads(result)

        assert data["countryCode"] == "US"
        assert "shippingMethods" in data
        assert len(data["shippingMethods"]) == 3  # No international for US

        # Check method names
        methods = [m["method"] for m in data["shippingMethods"]]
        assert "standard" in methods
        assert "express" in methods
        assert "overnight" in methods
        assert "international" not in methods

    def test_get_shipping_rates_international(self) -> None:
        """Test that get_shipping_rates includes international for non-US/CA."""
        result = get_shipping_rates(country_code="GB")
        data = json.loads(result)

        assert data["countryCode"] == "GB"
        assert len(data["shippingMethods"]) == 4  # Includes international

        methods = [m["method"] for m in data["shippingMethods"]]
        assert "international" in methods
