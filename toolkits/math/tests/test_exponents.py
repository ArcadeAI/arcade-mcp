import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_math.tools.exponents import (
    log,
    power,
)


def test_log():
    assert log("8", "2") == "3.0"
    assert log("2", "3") == "0.6309297535714574"
    assert log("2", "0.5") == "-1.0"
    with pytest.raises(ToolExecutionError):
        log("-1", "0.5")
    with pytest.raises(ToolExecutionError):
        log("0", "10")


def test_power():
    assert power("-8", "2") == "64"
    assert power("0", "10") == "0"
    assert (
        power("2", "0.5") == "1.41421356237309504880168872420969807856"
        "9671875376948073176679737990732478462107038850387534327641573"
    )
    assert power("2", "3") == "8"
    assert (
        power("2.", "-0.5") == "0.707106781186547524400844362104849039"
        "2848359376884740365883398689953662392310535194251937671638207864"
    )
    assert (
        power("2.1234", "0.6") == "1.571155202490495156807227174573016145"
        "282682479346448636509576776014844055570115193494685328114403375"
    )
    assert power("2.1234", "1") == "2.1234"
    assert power("2.1234", "3") == "9.574044440904"
    assert power("8", "-2") == "0.015625"
    assert power("8", "2") == "64"
    with pytest.raises(ToolExecutionError):
        power("-1", "0.5")
