#!/usr/bin/env python3
"""Test script to validate your actual request data.

Usage:
    python test_with_your_data.py '{"data": {"title": "Your Title"}, "position": {"x": 0, "y": 0}}'
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


def analyze_string(s, max_display=100):
    """Analyze a string for control characters."""
    print(f"  Length: {len(s)}")
    print(f"  First {max_display} chars: {s[:max_display]}")
    print(f"  Repr: {repr(s[:max_display])}")

    # Find control characters
    control_chars = []
    for i, char in enumerate(s):
        if ord(char) < 32 and char not in "\n\r\t":
            control_chars.append((i, char, ord(char)))

    if control_chars:
        print(f"  ✗ Found {len(control_chars)} control character(s):")
        for pos, char, code in control_chars[:10]:  # Show first 10
            print(f"    Position {pos}: {repr(char)} (ord={code})")
    else:
        print("  ✓ No problematic control characters")


def test_request_data(request_body_str):
    """Test building parameters with provided request data."""
    print("=" * 80)
    print("TESTING YOUR REQUEST DATA")
    print("=" * 80)

    print("\n1. Input request_body:")
    analyze_string(request_body_str)

    # Parse JSON
    print("\n2. Parsing JSON...")
    try:
        request_data = json.loads(request_body_str)
        print("   ✓ JSON parsing successful")
        print(f"   Type: {type(request_data)}")
        if isinstance(request_data, dict):
            print(f"   Keys: {list(request_data.keys())}")
    except json.JSONDecodeError as e:
        print(f"   ✗ JSON parsing FAILED: {e}")
        print(f"   Error at position: {e.pos}")
        if e.pos < len(request_body_str):
            context_start = max(0, e.pos - 20)
            context_end = min(len(request_body_str), e.pos + 20)
            print(f"   Context: {repr(request_body_str[context_start:context_end])}")
        return False

    # Try to serialize back to JSON
    print("\n3. Re-serializing to JSON...")
    try:
        content = json.dumps(request_data)
        print("   ✓ JSON serialization successful")
        print(f"   Output length: {len(content)}")
        analyze_string(content, max_display=200)
    except (ValueError, TypeError) as e:
        print(f"   ✗ JSON serialization FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")

        # Analyze each field
        print("\n4. Analyzing each field...")
        if isinstance(request_data, dict):
            for key, value in request_data.items():
                print(f"\n   Field: '{key}'")
                print(f"   Type: {type(value)}")
                print(f"   Value: {repr(value)[:200]}")

                try:
                    json.dumps({key: value})
                    print(f"   ✓ Can serialize")
                except Exception as field_err:
                    print(f"   ✗ Cannot serialize: {field_err}")

                    # If it's a string, analyze it
                    if isinstance(value, str):
                        print("   String analysis:")
                        analyze_string(value)

                    # If it's a dict, check nested
                    elif isinstance(value, dict):
                        print("   Nested fields:")
                        for nested_key, nested_value in value.items():
                            print(
                                f"     '{nested_key}': {type(nested_value)} = {repr(nested_value)[:100]}"
                            )
                            try:
                                json.dumps({nested_key: nested_value})
                                print(f"       ✓ OK")
                            except Exception as nested_err:
                                print(f"       ✗ ERROR: {nested_err}")
                                if isinstance(nested_value, str):
                                    analyze_string(nested_value)
        return False

    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED - Your data is valid!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use provided data
        request_body = sys.argv[1]
    else:
        # Interactive mode
        print("Paste your request_body JSON (or press Ctrl+C to exit):")
        print('Example: {"data": {"title": "My Card"}, "position": {"x": 0, "y": 0}}')
        print()
        try:
            request_body = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not request_body:
        print("Error: No input provided")
        print("\nUsage:")
        print('  python test_with_your_data.py \'{"data": {"title": "Test"}}"')
        print("  or")
        print("  python test_with_your_data.py")
        print("  (then paste your JSON)")
        sys.exit(1)

    success = test_request_data(request_body)
    sys.exit(0 if success else 1)
