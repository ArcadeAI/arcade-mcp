import pytest
from arcade_core.utils import pascal_to_snake_case, snake_to_pascal_case, space_to_snake_case


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


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("the simple server name", "the_simple_server_name"),
        (
            "the SIMPLE nAME and numbers 456",
            "the_SIMPLE_nAME_and_numbers_456",
        ),
    ],
)
def test_space_to_snake_case(input_str: str, expected: str):
    assert space_to_snake_case(input_str) == expected
