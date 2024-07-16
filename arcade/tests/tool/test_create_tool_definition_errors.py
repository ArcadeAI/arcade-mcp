import pytest

from arcade.sdk.tool import tool
from arcade.tool.catalog import ToolCatalog
from arcade.tool.errors import ToolDefinitionError


@tool
def func_with_missing_description():
    pass


@tool(desc="Returning function with declared no return type (illegal)")
def func_with_missing_return_type():
    return "hello world"


@tool(desc="A function with a parameter type (illegal)")
def func_with_missing_param_type(param1):
    pass


@tool(desc="A function with a parameter missing a description (illegal)")
def func_with_missing_param_description(param1: str):
    pass


@tool(desc="A function with an unsupported parameter type (illegal)")
def func_with_unsupported_param(param1: complex):
    pass


@pytest.mark.parametrize(
    "func_under_test, exception_type",
    [
        pytest.param(
            func_with_missing_description,
            ToolDefinitionError,
            id=func_with_missing_description.__name__,
        ),
        pytest.param(
            func_with_missing_return_type,
            ToolDefinitionError,
            id=func_with_missing_return_type.__name__,
        ),
        pytest.param(
            func_with_missing_param_type,
            ToolDefinitionError,
            id=func_with_missing_param_type.__name__,
        ),
        pytest.param(
            func_with_missing_param_description,
            ToolDefinitionError,
            id=func_with_missing_param_description.__name__,
        ),
        pytest.param(
            func_with_unsupported_param,
            ToolDefinitionError,
            id=func_with_unsupported_param.__name__,
        ),
    ],
)
def test_missing_info_raises_error(func_under_test, exception_type):
    with pytest.raises(exception_type):
        ToolCatalog.create_tool_definition(func_under_test, "1.0")
