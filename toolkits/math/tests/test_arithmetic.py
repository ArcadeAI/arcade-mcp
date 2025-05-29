import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_math.tools.arithmetic import (
    add,
    divide,
    mod,
    multiply,
    subtract,
    sum_list,
    sum_range,
)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("1", "2", "3"),
        ("-1", "1", "0"),
        ("0.5", "10.9", "11.4"),
        # Big ints
        ("12345678901234567890", "9876543210987654321", "22222222112222222211"),
        # Big floats
        (
            "12345678901234567890.120",
            "9876543210987654321.987",
            "22222222112222222212.107",
        ),
    ],
)
def test_add(a, b, expected):
    assert add(a, b) == expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("1", "2", "-1"),
        ("-1", "1", "-2"),
        ("0.5", "10.9", "-10.4"),
        # Big ints
        ("12345678901234567890", "12323456679012345668", "22222222222222222"),
        # Big floats
        (
            "12345678901234567890.120",
            "12343557689113355768.9079",
            "2121212121212121.2121",
        ),
    ],
)
def test_subtract(a, b, expected):
    assert subtract(a, b) == expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("-1", "2", "-2"),
        ("-10", "0", "-0"),
        ("0.5", "10.9", "5.45"),
        # Big ints
        (
            "12345678901234567890",
            "18000000162000001474380013420000",
            "222222222222222222222222222261233060226101083800000",
        ),
        # Big floats
        (
            "12345678901234567890.120",
            "12345678901234567890.120",
            "152415787532388367504868162811315348393.614400",
        ),
    ],
)
def test_multiply(a, b, expected):
    assert multiply(a, b) == expected


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("-1", "2", "-0.5"),
        ("-10", "1", "-10"),
        (
            "0.5",
            "10.9",
            "0.0458715596330275229357798165137614678899082568807339"
            "4495412844036697247706422018348623853211009174312",
        ),
        # Big ints
        ("152407406035740740602050", "12345678901234567890", "12345"),
        # Big floats
        (
            "152407406035740740603531.400",
            "12345678901234567890.120",
            "12345",
        ),
    ],
)
def test_divide(a, b, expected):
    assert divide(a, b) == expected


def text_zero_division():
    with pytest.raises(ToolExecutionError):
        divide("1", "0")
    with pytest.raises(ToolExecutionError):
        divide("1", "0.0")
    with pytest.raises(ToolExecutionError):
        divide("1", "0.000000")


def test_sum_list():
    assert sum_list(["1", "2", "3", "4", "5", "6"]) == "21"
    assert sum_list([]) == "0"
    assert sum_list(["-1", "-2", "-3", "-4", "-5", "-6"]) == "-21"
    assert sum_list(["0.1", "0.2", "0.3", "0.3", "0.5", "0.7"]) == "2.1"


def test_sum_range():
    assert sum_range("8", "2") == "0"
    assert sum_range("-8", "2") == "-33"
    assert sum_range("8", "-2") == "0"
    assert sum_range("2", "3") == "5"
    assert sum_range("0", "10") == "55"
    with pytest.raises(ToolExecutionError):
        sum_range("2", "0.5")
    with pytest.raises(ToolExecutionError):
        sum_range("-1", "0.5")
    with pytest.raises(ToolExecutionError):
        sum_range("2.", "0.5")
    with pytest.raises(ToolExecutionError):
        sum_range("-1", "0.5")


def test_mod():
    assert mod("-1", "0.5") == "-0.0"
    assert mod("-8", "2") == "-0"
    assert mod("0", "10") == "0"
    assert mod("2", "0.5") == "0.0"
    assert mod("2", "3") == "2"
    assert mod("2.", "-0.5") == "0.0"
    assert mod("2.1234", "0.6") == "0.3234"
    assert mod("2.1234", "1") == "0.1234"
    assert mod("2.1234", "3") == "2.1234"
    assert mod("8", "-2") == "0"
    assert mod("8", "2") == "0"
