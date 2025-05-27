import pytest
from arcade_core.utils import pascal_to_snake_case, snake_to_pascal_case


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("SnakeCase", "snake_case"),
        ("VeryLongSnake456", "very_long_snake456"),
    ],
)
def test_pascal_to_snake_case(input_str: str, expected: str):
    assert pascal_to_snake_case(input_str) == expected


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("snake_case", "SnakeCase"),
        ("very_long_snake_456", "VeryLongSnake456"),
        ("camelCase", "Camelcase"),  # camelCase isn't explicitly supported
    ],
)
def test_snake_to_pascal_case(input_str: str, expected: str):
    assert snake_to_pascal_case(input_str) == expected
