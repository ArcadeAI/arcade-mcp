import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_math.tools.rational import (
    gcd,
    lcm,
)


def test_gcd():
    assert gcd("-15", "-5") == "5"
    assert gcd("15", "0") == "15"
    assert gcd("15", "-2") == "1"
    assert gcd("15", "-0") == "15"
    assert gcd("15", "5") == "5"
    assert gcd("7", "13") == "1"
    assert gcd("-13", "13") == "13"
    with pytest.raises(ToolExecutionError):
        gcd("15.0", "5.0")


def test_lcm():
    assert lcm("-15", "-5") == "15"
    assert lcm("15", "0") == "0"
    assert lcm("15", "-2") == "30"
    assert lcm("15", "-0") == "0"
    assert lcm("15", "5") == "15"
    assert lcm("7", "13") == "91"
    assert lcm("-13", "13") == "13"
    with pytest.raises(ToolExecutionError):
        lcm("15.0", "5.0")
