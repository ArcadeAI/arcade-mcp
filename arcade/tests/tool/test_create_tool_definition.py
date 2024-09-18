from enum import Enum
from typing import Annotated, Literal, Optional

import pytest

from arcade.core.catalog import ToolCatalog
from arcade.core.schema import (
    InputParameter,
    OAuth2Requirement,
    ToolAuthRequirement,
    ToolContext,
    ToolInputs,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)
from arcade.sdk import tool
from arcade.sdk.annotations import Inferrable
from arcade.sdk.auth import GitHubApp, Google, OAuth2, SlackUser


### Tests on @tool decorator
@tool(desc="A function with a description")
def func_with_description():
    pass


@tool
def func_with_docstring_description():
    """Docstring description"""
    pass


@tool
def func_with_multiline_docstring_description():
    """
    Docstring description
    on multiple lines
    """
    pass


@tool(name="MyCustomTool", desc="A function with a very cool description")
def func_with_name_and_description():
    pass


@tool(
    desc="A function that requires authentication",
    requires_auth=OAuth2(authority="https://example.com/oauth2/auth", scopes=["scope1", "scope2"]),
)
def func_with_auth_requirement():
    pass


@tool(
    desc="A function that requires Google authorization",
    requires_auth=Google(scopes=["https://www.googleapis.com/auth/gmail.readonly"]),
)
def func_with_google_auth_requirement():
    pass


@tool(
    desc="A function that requires GitHub authorization",
    requires_auth=GitHubApp(),
)
def func_with_github_auth_requirement():
    pass


@tool(
    desc="A function that requires Slack user authorization",
    requires_auth=SlackUser(scopes=["chat:write", "channels:history"]),
)
def func_with_slack_user_auth_requirement():
    pass


### Tests on input params
@tool(desc="A function with a non-inferrable input parameter")
def func_with_non_inferrable_param(param1: Annotated[str, "First param", Inferrable(False)]):
    pass


# Two string annotations on an input parameter is understood to be name, description
@tool(desc="A function with a renamed input parameter")
def func_with_renamed_param(param1: Annotated[str, "ParamOne", "First param"]):
    pass


class MyEnum(Enum):
    FOO_BAR = "foo bar"
    BAZ = "baz"


@tool(desc="A function that takes an enum")
def func_with_enum_param(param1: Annotated[MyEnum, "an enum"]):
    pass


@tool(desc="A function that takes a dictionary")
def func_with_dict_param(param1: Annotated[dict, "a cool dictionary"]):
    pass


@tool(desc="A function that takes a string literal")
def func_with_string_literal_param(param1: Annotated[Literal["value1", "value2"], "a few choices"]):
    pass


@tool(desc="A function with an input parameter with a default value (considered optional)")
def func_with_param_with_default(param1: Annotated[str, "First param"] = "default"):
    pass


@tool(desc="A function with an optional input parameter")
def func_with_optional_param(param1: Annotated[Optional[str], "First param"]):
    pass


@tool(desc="A function with an optional input parameter (default: None)")
def func_with_optional_param_with_default_None(
    param1: Annotated[Optional[str], "First param"] = None,
):
    pass


@tool(desc="A function with an optional input parameter with default value")
def func_with_optional_param_with_default_value(
    param1: Annotated[Optional[str], "First param"] = "default",
):
    pass


@tool(desc="A function with multiple parameters, some with default values")
def func_with_mixed_params(
    context: ToolContext,
    param1: Annotated[str, "First param"],
    param2: Annotated[int, "Second param"] = 42,
):
    pass


@tool(desc="A function with a list[str] parameter")
def func_with_list_param(param1: Annotated[list[str], "A list of strings"]):
    pass


@tool(desc="A function with a list[float] parameter")
def func_with_list_float_param(param1: Annotated[list[float], "A list of floats"]):
    pass


@tool(desc="A function with a list of enums parameter")
def func_with_list_of_enums_param(param1: Annotated[list[MyEnum], "A list of enums"]):
    pass


@tool(desc="A function with a complex parameter type")
def func_with_complex_param(
    param1: Annotated[dict[str, list[int]], "A dictionary with lists of integers"],
):
    pass


@tool(desc="A function that takes a context")
def func_with_context(my_context: ToolContext):
    pass


### Tests on output/return values
@tool(desc="A function that returns a list of strings")
def func_with_list_return() -> list[str]:
    return ["output1", "output2"]


@tool(desc="A function that returns a known list of string literals")
def func_with_known_list_return() -> Literal["value1", "value2"]:
    return "value1"


@tool(desc="A function that returns an enum")
def func_with_enum_return() -> MyEnum:
    return MyEnum.FOO_BAR


@tool(desc="A function with an annotated return type")
def func_with_annotated_return() -> Annotated[str, "Annotated return description"]:
    return "output"


@tool(desc="A function with an optional return type")
def func_with_optional_return() -> Optional[str]:
    return "maybe output"


@tool(desc="A function with a complex return type")
def func_with_complex_return() -> dict[str, str]:
    return [{"key": "value"}]


@pytest.mark.parametrize(
    "func_under_test, expected_tool_def_fields",
    [
        # Tests on @tool decorator
        pytest.param(
            func_with_description,
            {
                "name": "FuncWithDescription",  # Defaults to the camelCased function name
            },
            id="func_with_default_name",
        ),
        pytest.param(
            func_with_description,
            {"description": "A function with a description"},
            id="func_with_description",
        ),
        pytest.param(
            func_with_docstring_description,
            {"description": "Docstring description"},
            id="func_with_docstring_description",
        ),
        pytest.param(
            func_with_multiline_docstring_description,
            {"description": "Docstring description\non multiple lines"},
            id="func_with_multiline_docstring_description",
        ),
        pytest.param(
            func_with_name_and_description,
            {"name": "MyCustomTool", "description": "A function with a very cool description"},
            id="func_with_description_and_name",
        ),
        pytest.param(
            func_with_name_and_description,
            {"name": "MyCustomTool", "requirements": ToolRequirements(auth=None)},
            id="func_with_no_auth_requirement",
        ),
        pytest.param(
            func_with_auth_requirement,
            {
                "requirements": ToolRequirements(
                    authorization=ToolAuthRequirement(
                        provider="oauth2",
                        oauth2=OAuth2Requirement(
                            authority="https://example.com/oauth2/auth",
                            scopes=["scope1", "scope2"],
                        ),
                    )
                )
            },
            id="func_with_auth_requirement",
        ),
        pytest.param(
            func_with_google_auth_requirement,
            {
                "requirements": ToolRequirements(
                    authorization=ToolAuthRequirement(
                        provider="google",
                        oauth2=OAuth2Requirement(
                            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                        ),
                    )
                )
            },
            id="func_with_google_auth_requirement",
        ),
        pytest.param(
            func_with_github_auth_requirement,
            {
                "requirements": ToolRequirements(
                    authorization=ToolAuthRequirement(
                        provider="github_app",
                    )
                )
            },
            id="func_with_github_auth_requirement",
        ),
        pytest.param(
            func_with_slack_user_auth_requirement,
            {
                "requirements": ToolRequirements(
                    authorization=ToolAuthRequirement(
                        provider="slack_user",
                        oauth2=OAuth2Requirement(
                            scopes=["chat:write", "channels:history"],
                        ),
                    )
                )
            },
            id="func_with_slack_user_auth_requirement",
        ),
        # Tests on input params
        pytest.param(
            func_with_non_inferrable_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=False,  # Set using Inferrable(False)
                            required=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
            },
            id="func_with_non_inferrable_param",
        ),
        pytest.param(
            func_with_renamed_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="ParamOne",
                            description="First param",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
            },
            id="func_with_renamed_param",
        ),
        pytest.param(
            func_with_enum_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="an enum",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="string", enum=["foo bar", "baz"]),
                        )
                    ]
                ),
            },
            id="func_with_enum_param",
        ),
        pytest.param(
            func_with_dict_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="a cool dictionary",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="json", enum=None),
                        )
                    ]
                ),
            },
            id="func_with_dict_param",
        ),
        pytest.param(
            func_with_string_literal_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="a few choices",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="string", enum=["value1", "value2"]),
                        )
                    ]
                ),
            },
            id="func_with_string_enum_param",
        ),
        pytest.param(
            func_with_param_with_default,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=True,
                            required=False,  # Because a default value is provided
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
                "output": ToolOutput(
                    available_modes=["null"], description="No description provided."
                ),
            },
            id="func_with_param_with_default",
        ),
        pytest.param(
            func_with_optional_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=True,
                            required=False,  # Because of Optional[str]
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
                "output": ToolOutput(
                    available_modes=["null"], description="No description provided."
                ),
            },
            id="func_with_optional_param",
        ),
        pytest.param(
            func_with_optional_param_with_default_None,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=True,
                            required=False,  # Because of Optional[str]
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
                "output": ToolOutput(
                    available_modes=["null"], description="No description provided."
                ),
            },
            id="func_with_optional_param_with_default_None",
        ),
        pytest.param(
            func_with_optional_param_with_default_value,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=True,
                            required=False,  # Because of Optional[str] and default value
                            value_schema=ValueSchema(val_type="string", enum=None),
                        )
                    ]
                ),
                "output": ToolOutput(
                    available_modes=["null"], description="No description provided."
                ),
            },
            id="func_with_optional_param_with_default_value",
        ),
        pytest.param(
            func_with_mixed_params,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="First param",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="string", enum=None),
                        ),
                        InputParameter(
                            name="param2",
                            description="Second param",
                            inferrable=True,
                            required=False,  # Because a default value is provided
                            value_schema=ValueSchema(val_type="integer", enum=None),
                        ),
                    ],
                    tool_context_parameter_name="context",
                ),
            },
            id="func_with_mixed_params",
        ),
        pytest.param(
            func_with_list_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="A list of strings",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(
                                val_type="array", inner_val_type="string", enum=None
                            ),
                        )
                    ]
                ),
            },
            id="func_with_list_param",
        ),
        pytest.param(
            func_with_list_float_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="A list of floats",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(
                                val_type="array", inner_val_type="number", enum=None
                            ),
                        )
                    ]
                ),
            },
            id="func_with_list_float_param",
        ),
        pytest.param(
            func_with_list_of_enums_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="A list of enums",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(
                                val_type="array", inner_val_type="string", enum=["foo bar", "baz"]
                            ),
                        )
                    ]
                ),
            },
            id="func_with_list_of_enums_param",
        ),
        pytest.param(
            func_with_complex_param,
            {
                "inputs": ToolInputs(
                    parameters=[
                        InputParameter(
                            name="param1",
                            description="A dictionary with lists of integers",
                            inferrable=True,
                            required=True,
                            value_schema=ValueSchema(val_type="json", enum=None),
                        )
                    ]
                ),
            },
            id="func_with_complex_param",
        ),
        pytest.param(
            func_with_context,
            {
                "inputs": ToolInputs(
                    parameters=[], tool_context_parameter_name="my_context"
                ),  # ToolContext type is not an input param, but it's stored in the inputs field
            },
            id="func_with_context",
        ),
        # Tests on output values
        pytest.param(
            func_with_list_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="array", inner_val_type="string", enum=None),
                    available_modes=["value", "error"],
                    description="No description provided.",
                ),
            },
            id="func_with_list_return",
        ),
        pytest.param(
            func_with_known_list_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="string", enum=["value1", "value2"]),
                    available_modes=["value", "error"],
                    description="No description provided.",
                ),
            },
            id="func_with_known_list_return",
        ),
        pytest.param(
            func_with_enum_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="string", enum=["foo bar", "baz"]),
                    available_modes=["value", "error"],
                    description="No description provided.",
                ),
            },
            id="func_with_enum_return",
        ),
        pytest.param(
            func_with_annotated_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="string", enum=None),
                    available_modes=["value", "error"],
                    description="Annotated return description",
                ),
            },
            id="func_with_annotated_return",
        ),
        pytest.param(
            func_with_optional_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="string", enum=None),
                    available_modes=["value", "error", "null"],
                    description="No description provided.",
                ),
            },
            id="func_with_optional_return",
        ),
        pytest.param(
            func_with_complex_return,
            {
                "inputs": ToolInputs(parameters=[]),
                "output": ToolOutput(
                    value_schema=ValueSchema(val_type="json", enum=None),
                    available_modes=["value", "error"],
                    description="No description provided.",
                ),
            },
            id="func_with_complex_return",
        ),
    ],
)
def test_create_tool_def(func_under_test, expected_tool_def_fields):
    tool_def = ToolCatalog.create_tool_definition(func_under_test, "1.0")

    assert tool_def.version == "1.0"

    for field, expected_value in expected_tool_def_fields.items():
        assert getattr(tool_def, field) == expected_value


def tool_version_is_set_correctly():
    tool_def = ToolCatalog.create_tool_definition(func_with_description, "abcd1236")
    assert tool_def.version == "abcd1236"
