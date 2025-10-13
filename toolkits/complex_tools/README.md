# Complex Tools - API Wrapper Testing Toolkit

This toolkit provides a set of tools designed to test complex API wrappers with intricate request bodies. It demonstrates how to handle APIs that require complex nested JSON structures by using stringified JSON inputs combined with dual-mode operation.

## Overview

The toolkit includes tools that simulate real-world API endpoints with complex request bodies that can't be easily represented with simple primitive types. Each main tool operates in two modes to help LLMs understand and build the required request structures.

## Tools

### Main API Wrapper Tools

#### 1. `create_user`
Creates a new user in the system with complex nested preferences and metadata.

**Modes:**
- `GET_REQUEST_SCHEMA`: Returns the complete OpenAPI specification for the request body
- `EXECUTE`: Creates the user using the provided request body JSON

**Parameters:**
- `mode` (ToolMode, required): Operation mode
- `request_body` (str | None): Stringified JSON representing the user creation request

**Request Body Schema Includes:**
- User details (email, username)
- Profile information (firstName, lastName, age, phoneNumber)
- Preferences with `oneOf`:
  - Email notifications (with frequency)
  - SMS notifications
- Theme and language preferences
- Metadata with source, referral code, and tags

**Example Workflow:**
1. Call with `mode='get_request_schema'` to see the required structure
2. Build the JSON object based on the schema
3. Call with `mode='execute'` and the stringified JSON

#### 2. `create_order`
Creates a new order in an e-commerce system with complex payment and shipping options.

**Modes:**
- `GET_REQUEST_SCHEMA`: Returns the complete OpenAPI specification for the request body
- `EXECUTE`: Creates the order using the provided request body and query parameters

**Parameters:**
- `mode` (ToolMode, required): Operation mode
- `priority` (str, required in execute mode): Order priority ('low', 'normal', 'high', 'urgent')
- `notification_email` (str, required in execute mode): Email for order notifications
- `request_body` (str | None): Stringified JSON representing the order request
- `gift_message` (str | None, optional): Optional gift message

**Request Body Schema Includes:**
- Order details with items array
- Product customizations using `anyOf`:
  - Clothing (color, size)
  - Jewelry (engraving)
  - Electronics (warranty)
- Payment methods using `oneOf`:
  - Credit card
  - PayPal
  - Crypto wallet
- Shipping address and method
- Discount codes

**Special Features:**
- Simple query parameters (`priority`, `notification_email`) are validated only in execute mode
- Demonstrates mixing simple parameters with complex request bodies

### Helper Tools

#### 3. `get_available_products`
Returns a list of available products with their IDs, categories, and customization options.

**Returns:** Static JSON with product catalog including:
- Product UUIDs
- Names and categories
- Prices
- Available customizations per product type

#### 4. `get_customer_info`
Retrieves customer information by email address.

**Parameters:**
- `customer_email` (str, required): Email address to look up

**Returns:** Customer data including UUID, profile, preferences, and account status

#### 5. `get_discount_codes`
Returns currently active discount codes.

**Returns:** List of discount codes with:
- Code strings
- Descriptions
- Discount percentages
- Validity dates

#### 6. `get_shipping_rates`
Gets shipping rates for a specific country.

**Parameters:**
- `country_code` (str, required): ISO 3166-1 alpha-2 country code

**Returns:** Available shipping methods with costs and delivery times

## Error Handling

The main tools use `RetryableToolError` with comprehensive error messages:

1. **Missing Request Body**: Returns the schema with instructions
2. **Invalid JSON**: Shows the parsing error and provides the schema
3. **Schema Validation Failure**: Points to the specific validation error with the full schema
4. **Invalid Query Parameters**: Explains the valid values and requirements

Each error includes:
- `message`: User-friendly error description
- `developer_message`: Technical details
- `additional_prompt_content`: Instructions for the LLM with the full schema

## Schema Validation

The toolkit includes a custom JSON schema validator that checks:
- Required fields
- Type validation (object, array, string, integer, number)
- Enum constraints
- Nested properties
- Array items
- Pattern validation (partially implemented)

## Design Patterns

### 1. Dual-Mode Operation
Tools operate in two modes to help LLMs:
- First call retrieves the schema
- Second call executes with the built JSON

### 2. Stringified JSON Input
Complex nested structures are passed as stringified JSON to avoid:
- Parameter explosion
- Complex type definitions
- Nested object limitations

### 3. Conditional Parameter Validation
Parameters can be required in execute mode but optional in schema mode:
```python
if mode == ToolMode.GET_REQUEST_SCHEMA:
    return schema
# Validate parameters only in execute mode
if not priority or priority not in valid_priorities:
    raise RetryableToolError(...)
```

### 4. Rich Error Messages
Errors include the full schema to guide the LLM in constructing valid requests

## Testing

To test the tools:

```bash
# Test import
uv run python -c "from complex_tools.tools.hello import create_user; print('OK')"

# Test schema retrieval
uv run python -c "
from complex_tools.tools.hello import create_user, ToolMode
schema = create_user(mode=ToolMode.GET_REQUEST_SCHEMA)
print(schema)
"

# Test execution (will fail without valid request body)
uv run python -c "
from complex_tools.tools.hello import create_user, ToolMode
try:
    result = create_user(mode=ToolMode.EXECUTE, request_body=None)
except Exception as e:
    print(f'Expected error: {e}')
"
```

## Use Cases

This toolkit is ideal for testing:
- LLM ability to handle complex API specifications
- Schema-driven API interaction
- Error recovery and retry logic
- Multi-step tool calling workflows
- JSON construction from specifications
- Complex nested data structures with oneOf/anyOf

## OpenAPI Features Demonstrated

- **oneOf**: Payment methods, notification types
- **anyOf**: Product customizations
- **enum**: Themes, languages, shipping methods, priorities
- **required fields**: At multiple nesting levels
- **pattern validation**: Email, UUID, phone numbers, postal codes
- **array constraints**: minItems, maxItems
- **string constraints**: minLength, maxLength
- **numeric constraints**: minimum, maximum
- **nested objects**: Multiple levels deep
- **format validation**: email, uuid, date-time

## Future Enhancements

Potential additions:
- Full JSON Schema Draft 7 validation
- Pattern matching validation
- Format validation (email, uuid, etc.)
- Conditional schemas (if/then/else)
- Additional complex schemas (allOf, not)
- Real API integration examples
- Performance benchmarks for LLM schema understanding
