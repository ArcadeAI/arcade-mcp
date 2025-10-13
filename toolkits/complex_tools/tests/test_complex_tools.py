import pytest
from arcade_tdk.errors import ToolExecutionError

from complex_tools.tools.hello import say_hello


def test_hello() -> None:
    assert say_hello("developer") == "Hello, developer!"


def test_hello_raises_error() -> None:
    with pytest.raises(ToolExecutionError):
        say_hello(1)
