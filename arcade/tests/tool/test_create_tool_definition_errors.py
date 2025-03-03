import pytest

from arcade.core.catalog import ToolCatalog
from arcade.core.errors import ToolDefinitionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool


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


@tool(desc="A function with a union parameter (illegal)")
def func_with_union_param(param1: str | int):
    pass


@tool(desc="A function with multiple context parameters (illegal)")
def func_with_multiple_context_params(context: ToolContext, context2: ToolContext):
    pass


@tool(
    desc="A function with a required secret with a missing key (illegal)",
    requires_secrets=[""],
)
def func_with_missing_secret_key(context: ToolContext):
    pass


@tool(
    desc="A function that requires a secret (invalid type)",
    requires_secrets=[True],
)
def func_with_secret_requirement_invalid_type():
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
        pytest.param(
            func_with_union_param,
            ToolDefinitionError,
            id=func_with_union_param.__name__,
        ),
        pytest.param(
            func_with_multiple_context_params,
            ToolDefinitionError,
            id=func_with_multiple_context_params.__name__,
        ),
        pytest.param(
            func_with_missing_secret_key,
            ToolDefinitionError,
            id=func_with_missing_secret_key.__name__,
        ),
        pytest.param(
            func_with_secret_requirement_invalid_type,
            ToolDefinitionError,
            id=func_with_secret_requirement_invalid_type.__name__,
        ),
    ],
)
def test_missing_info_raises_error(func_under_test, exception_type):
    with pytest.raises(exception_type):
        ToolCatalog.create_tool_definition(func_under_test, "1.0")
