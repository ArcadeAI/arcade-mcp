import pytest
from arcade.sdk.errors import ToolExecutionError

from arcade_math.tools.arithmetic import (
    add,
    divide,
    multiply,
    sqrt,
    subtract,
    sum_list,
    sum_range,
)


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0.5, 10.9) == 11.4


def test_subtract():
    assert subtract(2, 1) == 1
    assert subtract(2, 3.5) == -1.5


def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(-1, 1.5) == -1.5


def test_divide():
    assert divide(6, 3) == 2.0
    assert divide(5, 2) == 2.5
    with pytest.raises(ToolExecutionError):
        divide(1, 0)


def test_sqrt():
    assert sqrt(4) == 2.0
    assert sqrt(9) == 3.0


def test_sum_list():
    assert sum_list([1, 2, 3]) == 6
    assert sum_list([0, -1.5, 1]) == -0.5


def test_sum_range():
    assert sum_range(1, 3) == 6
    assert sum_range(0, 10) == 55
