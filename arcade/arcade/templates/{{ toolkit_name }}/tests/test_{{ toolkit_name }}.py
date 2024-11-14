import pytest
from arcade.sdk.errors import ToolExecutionError
from {{ package_name }}.tools.hello import say_hello

def test_hello():
    assert say_hello("developer") == "Hello, developer!"

def test_hello_raises_error():
    with pytest.raises(ToolExecutionError):
        say_hello(1)
