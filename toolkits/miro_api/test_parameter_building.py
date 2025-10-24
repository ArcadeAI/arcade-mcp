#!/usr/bin/env python3
"""Test script to build parameters for add_card_to_miro_board without calling the API.

This script reproduces the exact parameter building logic to identify
where control characters might be introduced.
"""

import json
import sys


def remove_none_values(data):
    """Recursively remove None values from dictionaries."""
    if isinstance(data, dict):
        return {k: remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    return data


def test_parameter_building():
    """Test building parameters exactly as add_card_to_miro_board does."""
    print("=" * 80)
    print("TESTING PARAMETER BUILDING FOR add_card_to_miro_board")
    print("=" * 80)

    # Simulate typical inputs (modify these to match your actual use case)
    board_identifier = "test_board_123"
    request_body = json.dumps({
        "data": {"title": "Test Card", "description": "This is a test description"},
        "position": {"x": 0, "y": 0},
    })

    print("\n1. Input request_body (as string):")
    print(f"   Type: {type(request_body)}")
    print(f"   Length: {len(request_body)}")
    print(f"   Content: {request_body}")
    print(f"   Repr: {repr(request_body)}")

    # Parse JSON (as the function does)
    print("\n2. Parsing JSON...")
    try:
        request_data = json.loads(request_body)
        print("   ✓ JSON parsing successful")
        print(f"   Type: {type(request_data)}")
        print(f"   Keys: {request_data.keys()}")
    except json.JSONDecodeError as e:
        print(f"   ✗ JSON parsing FAILED: {e}")
        return

    # Build URL
    print("\n3. Building URL...")
    url = "https://api.miro.com/v2/boards/{board_id}/cards".format(board_id=board_identifier)
    print(f"   URL: {url}")

    # Build headers
    print("\n4. Building headers...")
    headers = remove_none_values({
        "Content-Type": "application/json",
        "Authorization": "Bearer test_token_123",
    })
    print(f"   Headers: {headers}")

    # Build params
    print("\n5. Building params...")
    params = remove_none_values({})
    print(f"   Params: {params}")

    # Try to serialize request_data to JSON (this is where the error might occur)
    print("\n6. Serializing request_data to JSON...")
    try:
        content = json.dumps(request_data)
        print("   ✓ JSON serialization successful")
        print(f"   Length: {len(content)}")
        print(f"   Content: {content}")
        print(f"   Repr: {repr(content)}")

        # Check for control characters
        print("\n7. Checking for control characters...")
        has_control_chars = False
        for i, char in enumerate(content):
            if ord(char) < 32 and char not in "\n\r\t":
                print(
                    f"   ✗ Control character found at position {i}: {repr(char)} (ord={ord(char)})"
                )
                has_control_chars = True

        if not has_control_chars:
            print("   ✓ No control characters found")

    except (ValueError, TypeError) as e:
        print(f"   ✗ JSON serialization FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")

        # Analyze each field
        print("\n8. Analyzing each field in request_data...")
        for key, value in request_data.items():
            try:
                json.dumps({key: value})
                print(f"   ✓ Field '{key}': OK")
            except Exception as field_err:
                print(f"   ✗ Field '{key}': ERROR - {field_err}")
                print(f"      Type: {type(value)}")
                print(f"      Repr: {repr(value)}")
                print(f"      Str: {str(value)}")

                # If it's a dict or list, check nested values
                if isinstance(value, dict):
                    print(f"      Nested keys: {value.keys()}")
                    for nested_key, nested_value in value.items():
                        try:
                            json.dumps({nested_key: nested_value})
                            print(f"        ✓ Nested '{nested_key}': OK")
                        except Exception as nested_err:
                            print(f"        ✗ Nested '{nested_key}': ERROR - {nested_err}")
                            print(f"           Repr: {repr(nested_value)}")
        return

    print("\n" + "=" * 80)
    print("✓ ALL PARAMETER BUILDING SUCCESSFUL - No issues found")
    print("=" * 80)


if __name__ == "__main__":
    test_parameter_building()

    # Test with potentially problematic data
    print("\n\n")
    print("=" * 80)
    print("TESTING WITH POTENTIALLY PROBLEMATIC DATA")
    print("=" * 80)

    problematic_inputs = [
        {"name": "String with newline", "data": {"title": "Line 1\nLine 2"}},
        {"name": "String with tab", "data": {"title": "Col1\tCol2"}},
        {"name": "String with null byte", "data": {"title": "Test\x00String"}},
        {"name": "String with control character", "data": {"title": "Test\x01String"}},
    ]

    for test_case in problematic_inputs:
        print(f"\nTesting: {test_case['name']}")
        print(f"  Data: {repr(test_case['data'])}")
        try:
            serialized = json.dumps(test_case["data"])
            print(f"  ✓ Serialization successful: {repr(serialized)}")
        except (ValueError, TypeError) as e:
            print(f"  ✗ Serialization FAILED: {e}")
