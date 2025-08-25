from arcade_math.tools.statistics import (
    avg,
    median,
)


def test_avg():
    assert avg(["1", "2", "3", "4", "5", "6"]) == "3.5"
    assert avg([]) == "0.0"
    assert avg(["-1", "-2", "-3", "-4", "-5", "-6"]) == "-3.5"
    assert avg(["0.1", "0.2", "0.3", "0.3", "0.5", "0.7"]) == "0.35"


def test_median():
    assert median(["1", "2", "3", "4", "5", "6"]) == "3.5"
    assert median([]) == "0.0"
    assert median(["-1", "-2", "-3", "-4", "-5", "-6"]) == "-3.5"
    assert median(["0.1", "0.2", "0.3", "0.3", "0.5", "0.7"]) == "0.3"
