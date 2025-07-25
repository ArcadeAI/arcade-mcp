from arcade_math.tools.trigonometry import (
    deg_to_rad,
    rad_to_deg,
)


def test_deg_to_rad():
    assert deg_to_rad("1") == "0.017453292519943295"
    assert deg_to_rad("-1") == "-0.017453292519943295"
    assert deg_to_rad("0") == "0.0"
    assert deg_to_rad("-0") == "-0.0"
    assert deg_to_rad("23") == "0.4014257279586958"
    assert deg_to_rad("24") == "0.4188790204786391"
    assert deg_to_rad("-10") == "-0.17453292519943295"
    assert deg_to_rad("10") == "0.17453292519943295"
    assert deg_to_rad("180") == "3.141592653589793"
    assert deg_to_rad("0.0") == "0.0"
    assert deg_to_rad("0.0000") == "0.0"
    assert deg_to_rad("-0.0") == "-0.0"
    assert deg_to_rad("1.0") == "0.017453292519943295"
    assert deg_to_rad("-1.0") == "-0.017453292519943295"
    assert deg_to_rad("23.0") == "0.4014257279586958"
    assert deg_to_rad("0.4") == "0.006981317007977318"
    assert deg_to_rad("-10.0") == "-0.17453292519943295"
    assert deg_to_rad("10.0") == "0.17453292519943295"


def test_rad_to_deg():
    assert rad_to_deg("1") == "57.29577951308232"
    assert rad_to_deg("-1") == "-57.29577951308232"
    assert rad_to_deg("0") == "0.0"
    assert rad_to_deg("-0") == "-0.0"
    assert rad_to_deg("23") == "1317.8029288008934"
    assert rad_to_deg("24") == "1375.0987083139757"
    assert rad_to_deg("-10") == "-572.9577951308232"
    assert rad_to_deg("10") == "572.9577951308232"
    assert rad_to_deg("0.0") == "0.0"
    assert rad_to_deg("0.0000") == "0.0"
    assert rad_to_deg("-0.0") == "-0.0"
    assert rad_to_deg("1.0") == "57.29577951308232"
    assert rad_to_deg("-1.0") == "-57.29577951308232"
    assert rad_to_deg("3.14") == "179.9087476710785"
    assert rad_to_deg("0.4") == "22.918311805232932"
    assert rad_to_deg("-10.0") == "-572.9577951308232"
    assert rad_to_deg("10.0") == "572.9577951308232"
