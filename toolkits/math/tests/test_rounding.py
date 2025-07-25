from arcade_math.tools.rounding import (
    ceil,
    floor,
    round_num,
)


def test_ceil():
    assert ceil("1") == "1"
    assert ceil("-1") == "-1"
    assert ceil("0") == "0"
    assert ceil("-0") == "0"
    assert ceil("0.0") == "0"
    assert ceil("0.0000") == "0"
    assert ceil("-0.0") == "0"
    assert ceil("1.0") == "1"
    assert ceil("-1.0") == "-1"
    assert ceil("3.14") == "4"
    assert ceil("0.4") == "1"
    assert ceil("-1.3") == "-1"


def test_floor():
    assert floor("1") == "1"
    assert floor("-1") == "-1"
    assert floor("0") == "0"
    assert floor("-0") == "0"
    assert floor("10") == "10"
    assert floor("0.0") == "0"
    assert floor("0.0000") == "0"
    assert floor("-0.0") == "0"
    assert floor("1.0") == "1"
    assert floor("-1.0") == "-1"
    assert floor("3.14") == "3"
    assert floor("0.4") == "0"
    assert floor("-1.3") == "-2"


def test_round_num():
    # TODO(mateo): ok with scientific notatin? ok with negative round digits?
    assert round_num("1.2345", "-2") == "0"
    assert round_num("1.2345", "-1") == "0"
    assert round_num("1.2345", "0") == "1"
    assert round_num("1.2345", "1") == "1.2"
    assert round_num("1.2345", "2") == "1.23"
    assert round_num("1.2345", "3") == "1.234"
    assert round_num("1.2345", "8") == "1.23450000"
    assert round_num("1.654321", "-2") == "0"
    assert round_num("1.654321", "-1") == "0"
    assert round_num("1.654321", "0") == "2"
    assert round_num("1.654321", "1") == "1.7"
    assert round_num("1.654321", "2") == "1.65"
    assert round_num("1.654321", "3") == "1.654"
    assert round_num("1.654321", "8") == "1.65432100"
