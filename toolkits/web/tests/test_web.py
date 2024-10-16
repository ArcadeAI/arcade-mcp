import pytest
from arcade_web.tools.hello import hello

from arcade.sdk.error import ToolExecutionError


def test_hello():
    assert hello("developer") == "Hello, developer!"


def test_hello_raises_error():
    with pytest.raises(ToolExecutionError):
        hello(1)
