import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_math.tools.miscellaneous import (
    abs_val,
    factorial,
    sqrt,
)


def test_abs_val():
    assert abs_val("2") == "2"
    assert abs_val("-1") == "1"
    assert abs_val("-1.12341234") == "1.12341234"


def test_factorial():
    assert factorial("1") == "1"
    assert factorial("0") == "1"
    assert factorial("-0") == "1"
    assert factorial("23") == "25852016738884976640000"
    assert factorial("24") == "620448401733239439360000"
    assert factorial("10") == "3628800"
    with pytest.raises(ToolExecutionError):
        factorial("-1")
    with pytest.raises(ToolExecutionError):
        factorial("-10")
    with pytest.raises(ToolExecutionError):
        factorial("0.0000")
    with pytest.raises(ToolExecutionError):
        factorial("-0.0")
    with pytest.raises(ToolExecutionError):
        factorial("1.0")
    with pytest.raises(ToolExecutionError):
        factorial("-1.0")
    with pytest.raises(ToolExecutionError):
        factorial("23.0")


def test_sqrt():
    assert sqrt("1") == "1"
    assert sqrt("0") == "0"
    assert sqrt("-0") == "-0"
    assert (
        sqrt("23") == "4.79583152331271954159743806416269391999670704190"
        "4129346485309114448257235907464082492191446436918861"
    )
    assert (
        sqrt("24") == "4.89897948556635619639456814941178278393189496131"
        "3340256865385134501920754914630053079718866209280470"
    )
    assert (
        sqrt("10") == "3.16227766016837933199889354443271853371955513932"
        "5216826857504852792594438639238221344248108379300295"
    )
    assert sqrt("0.0") == "0.0"
    assert sqrt("0.0000") == "0.00"
    assert sqrt("-0.0") == "-0.0"
    assert sqrt("1.0") == "1.0"
    assert (
        sqrt("3.14") == "1.772004514666935040199112509753631525073608516"
        "162942966817771970290992972348902551472561151153909188"
    )
    assert (
        sqrt("0.4") == "0.6324555320336758663997787088865437067439110278"
        "650433653715009705585188877278476442688496216758600590"
    )
    assert (
        sqrt("10.0") == "3.162277660168379331998893544432718533719555139"
        "325216826857504852792594438639238221344248108379300295"
    )
    with pytest.raises(ToolExecutionError):
        sqrt("-1")
    with pytest.raises(ToolExecutionError):
        sqrt("-10")
    with pytest.raises(ToolExecutionError):
        sqrt("-1.0")
    with pytest.raises(ToolExecutionError):
        sqrt("-1.3")
    with pytest.raises(ToolExecutionError):
        sqrt("-10.0")
