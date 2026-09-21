from typing import Annotated, Union
from unittest.mock import MagicMock, patch

import pytest
from arcade_core.catalog import ToolCatalog, create_func_models, create_input_definition
from arcade_core.errors import (
    ToolDefinitionError,
    ToolInputSchemaError,
    ToolkitLoadError,
    ToolOutputSchemaError,
)
from arcade_core.schema import (
    FullyQualifiedName,
    InputParameter,
    ToolContext,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ValueSchema,
)
from arcade_core.toolkit import Toolkit
from arcade_mcp_server.context import Context
from arcade_tdk import tool
from arcade_tdk.auth import GitHub
from pydantic import BaseModel, Field


@tool
def sample_tool() -> str:
    """
    A sample tool function
    """
    return "Hello, world!"


@tool
def valid_tool(input_text: Annotated[str, "The text to process"]) -> str:
    """
    A test tool that processes input text.

    Args:
        input_text: The text to process

    Returns:
        The processed text
    """
    return f"Processed: {input_text}"


@tool
def tool_with_missing_input_parameter_annotation(input_text: str) -> str:
    """
    A test tool that processes input text.

    Args:
        input_text: The text to process

    Returns:
        The processed text
    """
    return f"Processed: {input_text}"


# Invalid tool examples for testing error cases


# ToolDefinitionError cases
def tool_missing_description(input_text: Annotated[str, "The text to process"]) -> str:
    return f"Processed: {input_text}"


@tool(requires_secrets=[123])  # type: ignore[misc]
def tool_with_invalid_secret_type(input_text: Annotated[str, "The text"]) -> str:
    """A tool with invalid secret type."""
    return f"Processed: {input_text}"


@tool(requires_secrets=[""])
def tool_with_empty_secret(input_text: Annotated[str, "The text"]) -> str:
    """A tool with empty secret."""
    return f"Processed: {input_text}"


@tool(requires_metadata=[123])  # type: ignore[misc]
def tool_with_invalid_metadata_type(input_text: Annotated[str, "The text"]) -> str:
    """A tool with invalid metadata type."""
    return f"Processed: {input_text}"


@tool(requires_metadata=["client_id"])  # Requires auth but no auth provided
def tool_with_metadata_requiring_auth_without_auth(input_text: Annotated[str, "The text"]) -> str:
    """A tool with metadata requiring auth but no auth provided."""
    return f"Processed: {input_text}"


@tool(requires_metadata=[""])
def tool_with_empty_metadata(input_text: Annotated[str, "The text"]) -> str:
    """A tool with empty metadata."""
    return f"Processed: {input_text}"


class MyFancyTestClass:
    pass


@tool
def tool_with_unsupported_param_type(
    param: Annotated[MyFancyTestClass, "A class that is a parameter"],
) -> str:
    """A tool with unsupported parameter type."""
    return "result"


# ToolInputSchemaError cases
@tool
def tool_with_no_type_annotation(param) -> str:  # type: ignore[no-untyped-def]
    """A tool with untyped parameter."""
    return f"Result: {param}"


@tool
def tool_with_invalid_param_name(param: Annotated[str, "123invalid", "Description"]) -> str:
    """A tool with invalid parameter name."""
    return f"Result: {param}"


@tool
def tool_with_too_many_annotations(param: Annotated[str, "name", "desc", "extra"]) -> str:
    """A tool with an input parameter that has too many annotations."""
    return f"Result: {param}"


@tool
def tool_with_required_union_param(param: Annotated[Union[str, int], "Union parameter"]) -> str:
    """A tool with an input parameter that is a non-optional union type."""
    return f"Result: {param}"


def non_callable_factory():
    raise RuntimeError("This should not be called")


@tool
def tool_with_non_callable_default_factory(
    param: Annotated[str, "Parameter"] = Field(default_factory="not_callable"),  # type: ignore[arg-type]
) -> str:
    """A tool with an input parameter that has a non-callable default factory."""
    return f"Result: {param}"


@tool
def tool_with_multiple_tool_contexts(ctx1: ToolContext, ctx2: ToolContext) -> str:
    """A tool with multiple input parameters that are ToolContext."""
    return "result"


@tool
def tool_missing_return_type_hint(input_text: Annotated[str, "The text to process"]):
    """A tool without return type hint."""
    return f"Processed: {input_text}"


@tool
def tool_with_unsupported_output_type(
    input_text: Annotated[str, "The text to process"],
) -> Annotated[MyFancyTestClass, "THe output type"]:
    """A tool with an output parameter type that is not supported."""
    return MyFancyTestClass()


def test_add_tool_with_empty_toolkit_name_raises():
    catalog = ToolCatalog()
    with pytest.raises(ValueError):
        catalog.add_tool(sample_tool, "")


def test_add_tool_with_toolkit_name():
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "sample_toolkit")
    assert (
        catalog.get_tool(FullyQualifiedName("SampleTool", "SampleToolkit", None)).tool
        == sample_tool
    )


def test_add_tool_with_toolkit():
    catalog = ToolCatalog()
    toolkit = Toolkit(
        name="sample_toolkit",
        description="A sample toolkit",
        version="1.0.0",
        package_name="sample_toolkit",
    )
    catalog.add_tool(sample_tool, toolkit)
    assert (
        catalog.get_tool(FullyQualifiedName("SampleTool", "SampleToolkit", None)).tool
        == sample_tool
    )


@pytest.mark.parametrize(
    "toolkit_version, expected_tool",
    [
        ("1.0.0", sample_tool),
        (None, sample_tool),
    ],
)
def test_get_tool(toolkit_version: str | None, expected_tool):
    catalog = ToolCatalog()
    fake_toolkit = Toolkit(
        name="sample_toolkit",
        description="A sample toolkit",
        version="1.0.0",
        package_name="sample_toolkit",
    )
    catalog.add_tool(sample_tool, fake_toolkit, module=None)

    fq_name = FullyQualifiedName(
        name="SampleTool", toolkit_name="SampleToolkit", toolkit_version=toolkit_version
    )
    tool = catalog.get_tool(fq_name)
    assert tool.tool == expected_tool


def test_add_toolkit_type_error():
    catalog = ToolCatalog()

    # Create a mock toolkit with an invalid tool
    class InvalidTool:
        pass

    mock_toolkit = Toolkit(
        name="mock_toolkit",
        description="A mock toolkit",
        version="0.0.1",
        package_name="mock_toolkit",
    )
    mock_toolkit.tools = {"mock_module": ["invalid_tool"]}

    # Mock the import_module and getattr functions
    with (
        patch("arcade_core.catalog.import_module") as mock_import,
        patch("arcade_core.catalog.getattr") as mock_getattr,
    ):
        mock_import.return_value = MagicMock()
        mock_getattr.return_value = InvalidTool()

        # Assert that ToolDefinitionError is raised
        with pytest.raises(ToolDefinitionError):
            catalog.add_toolkit(mock_toolkit)


def test_add_toolkit_import_module_error():
    catalog = ToolCatalog()

    # Create a mock toolkit with an invalid tool

    mock_toolkit = Toolkit(
        name="mock_toolkit",
        description="A mock toolkit",
        version="0.0.1",
        package_name="mock_toolkit",
    )
    mock_toolkit.tools = {"mock_module": ["sample_tool"]}

    # Mock the import_module and getattr functions
    with (
        patch("arcade_core.catalog.import_module") as mock_import,
    ):
        mock_import.side_effect = ImportError("Mock import error")

        # Assert that ToolkitLoadError is raised
        with pytest.raises(ToolkitLoadError) as exc_info:
            catalog.add_toolkit(mock_toolkit)

        # Check that the error message contains the expected substring
        assert "Could not import module mock_module. Reason: Mock import error" in str(
            exc_info.value
        )


def test_get_tool_by_name():
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "sample_toolkit")

    tool = catalog.get_tool_by_name("SampleToolkit.SampleTool")
    assert tool.tool == sample_tool
    assert tool.name == "SampleTool"
    assert tool.meta.toolkit == "sample_toolkit"
    assert tool.version is None

    with pytest.raises(ValueError):
        catalog.get_tool_by_name("nonexistent_toolkit.SampleTool")


def test_get_tool_by_name_with_version():
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "sample_toolkit")

    tool = catalog.get_tool_by_name("SampleToolkit.SampleTool")
    assert tool.tool == sample_tool
    assert tool.name == "SampleTool"
    assert tool.meta.toolkit == "sample_toolkit"

    with pytest.raises(ValueError):
        catalog.get_tool_by_name("SampleToolkit.SampleTool", version="2.0.0")


def test_get_tool_by_name_with_invalid_version():
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "SampleToolkit")

    with pytest.raises(ValueError):
        catalog.get_tool_by_name("SampleToolkit.SampleTool", version="2.0.0")


def test_load_disabled_tools(monkeypatch):
    disabled_tools = (
        "SampleToolkitOne.SampleToolOne,"  # valid
        + "SampleToolkitOne_SampleToolTwo,"  # invalid
        + "SampleToolkitTwo.SampleToolThree,"  # valid
        + "SampleToolkitTwo.SampleToolFour@0.0.1,"  # invalid
        + "SampleToolkitThree_SampleToolFive@0.0.1,"  # invalid
        + "SampleToolkitFour.sample_tool_six,"  # invalid
        + "sample_toolkit5.SampleTool7,"  # invalid
        + "sample_toolkit6.sample_tool_8"  # invalid
    )
    expected_disabled_tools = {
        "sampletoolkitone.sampletoolone",
        "sampletoolkittwo.sampletoolthree",
    }

    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", disabled_tools)
    catalog = ToolCatalog()

    assert catalog._disabled_tools == expected_disabled_tools


def test_add_tool_with_disabled_tool(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "SampleToolkitOne.SampleTool")
    catalog = ToolCatalog()

    catalog.add_tool(sample_tool, "SampleToolkitOne")
    assert len(catalog._tools) == 0


def test_add_tool_with_empty_string_disabled_tools(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "")
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "SampleToolkitOne")
    assert len(catalog._tools) == 1


def test_add_tool_with_whitespace_disabled_tools(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLS", "            ")
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "SampleToolkitOne")
    assert len(catalog._tools) == 1


def test_add_tool_with_disabled_toolkit(monkeypatch):
    monkeypatch.setenv("ARCADE_DISABLED_TOOLKITS", "SampleToolkitOne")
    catalog = ToolCatalog()

    catalog.add_toolkit(
        Toolkit(
            name="SampleToolkitOne",
            package_name="sample_toolkit_one",
            version="1.0.0",
            description="A sample toolkit",
        )
    )
    assert len(catalog._tools) == 0


@pytest.mark.parametrize(
    "tool_name, expected_error_type, expected_error_substring",
    [
        # ToolDefinitionError cases
        (
            "tool_missing_description",
            ToolDefinitionError,
            "Tool 'tool_missing_description' is missing a description",
        ),
        (
            "tool_with_invalid_secret_type",
            ToolDefinitionError,
            "Secret keys must be strings (error in tool ToolWithInvalidSecretType)",
        ),
        (
            "tool_with_empty_secret",
            ToolDefinitionError,
            "Secrets must have a non-empty key (error in tool ToolWithEmptySecret)",
        ),
        (
            "tool_with_invalid_metadata_type",
            ToolDefinitionError,
            "Metadata must be strings (error in tool ToolWithInvalidMetadataType)",
        ),
        (
            "tool_with_metadata_requiring_auth_without_auth",
            ToolDefinitionError,
            "Tool ToolWithMetadataRequiringAuthWithoutAuth declares metadata key 'client_id'",
        ),
        (
            "tool_with_empty_metadata",
            ToolDefinitionError,
            "Metadata must have a non-empty key (error in tool ToolWithEmptyMetadata)",
        ),
        (
            "tool_with_unsupported_param_type",
            ToolDefinitionError,
            "Unsupported parameter type: <class 'test_catalog.MyFancyTestClass'>",
        ),
        # ToolInputSchemaError cases
        (
            "tool_with_missing_input_parameter_annotation",
            ToolInputSchemaError,
            "Parameter 'input_text' is missing a description",
        ),
        (
            "tool_with_no_type_annotation",
            ToolInputSchemaError,
            "Parameter param has no type annotation",
        ),
        (
            "tool_with_invalid_param_name",
            ToolInputSchemaError,
            "Invalid parameter name: '123invalid' is not a valid identifier",
        ),
        (
            "tool_with_too_many_annotations",
            ToolInputSchemaError,
            "Parameter param: Annotated[str, 'name', 'desc', 'extra'] has too many string annotations. Expected 0, 1, or 2, got 3",
        ),
        (
            "tool_with_required_union_param",
            ToolInputSchemaError,
            "Parameter param is a union type. Only optional types are supported",
        ),
        (
            "tool_with_non_callable_default_factory",
            ToolInputSchemaError,
            "Default factory for parameter param: Annotated[str, 'Parameter'] = FieldInfo(annotation=NoneType, required=False, default_factory=str) is not callable.",
        ),
        (
            "tool_with_multiple_tool_contexts",
            ToolInputSchemaError,
            "Only one ToolContext parameter is supported, but tool tool_with_multiple_tool_contexts has multiple",
        ),
        (
            "tool_missing_return_type_hint",
            ToolOutputSchemaError,
            "Tool 'ToolMissingReturnTypeHint' must have a return type",
        ),
        (
            "tool_with_unsupported_output_type",
            ToolOutputSchemaError,
            "Unsupported output type '<class 'test_catalog.MyFancyTestClass'>'",
        ),
    ],
)
def test_add_toolkit_with_invalid_tools(
    tool_name: str, expected_error_type: type, expected_error_substring: str
):
    """Test that add_toolkit raises the correct error for various invalid tool definitions."""
    catalog = ToolCatalog()

    # Create a toolkit that references our test tool
    test_toolkit = Toolkit(
        name="test_toolkit",
        description="A test toolkit",
        version="1.0.0",
        package_name="test_toolkit",
    )
    test_toolkit.tools = {"tests.core.test_catalog": [tool_name]}

    # Mock the import_module to return the current module
    import sys

    current_module = sys.modules[__name__]

    with patch("arcade_core.catalog.import_module") as mock_import:
        mock_import.return_value = current_module

        # Add the toolkit and expect the specified error
        with pytest.raises(expected_error_type) as exc_info:
            catalog.add_toolkit(test_toolkit)

        # Check that the error message contains the expected substring
        actual_error_message = str(exc_info.value)
        # Adjust for Python 3.11 and below where Annotated is returned as "typing.Annotated"
        if "typing.Annotated" in actual_error_message:
            expected_error_substring = expected_error_substring.replace(
                "Annotated", "typing.Annotated"
            )
        assert expected_error_substring in actual_error_message


def test_add_toolkit_with_duplicate_tool():
    """Test that add_toolkit raises ToolkitLoadError when a tool already exists in the catalog."""
    catalog = ToolCatalog()

    test_toolkit = Toolkit(
        name="test_toolkit",
        description="A test toolkit",
        version="1.0.0",
        package_name="test_toolkit",
    )
    test_toolkit.tools = {"tests.core.test_catalog": ["valid_tool", "valid_tool"]}

    # Mock the import_module to return the current module
    import sys

    current_module = sys.modules[__name__]

    with patch("arcade_core.catalog.import_module") as mock_import:
        mock_import.return_value = current_module

        # Adding the toolkit should raise ToolkitLoadError for duplicate tool
        with pytest.raises(ToolkitLoadError) as exc_info:
            catalog.add_toolkit(test_toolkit)

        # Check that the error message contains the expected substring
        assert "Tool 'ValidTool' in server 'test_toolkit' already exists in the catalog." in str(
            exc_info.value
        )


def _assert_reserved_argument_error(exc: BaseException) -> None:
    message = str(exc)
    assert "connected_account" in message
    assert "Arcade Engine" in message
    assert "Rename" in message


@tool
def tool_required_reserved_name(connected_account: Annotated[str, "The account to use"]) -> str:
    """A tool whose exposed input uses the reserved name."""
    return connected_account


@tool
def tool_optional_reserved_name(
    connected_account: Annotated[str | None, "The account to use"] = None,
) -> str:
    """A tool whose optional reserved input defaults to None."""
    return connected_account or ""


@tool
def tool_defaulted_reserved_name(
    connected_account: Annotated[str, "The account to use"] = "acct",
) -> str:
    """A tool whose reserved input has a non-None default."""
    return connected_account


@tool
def tool_alias_reserved_name(
    value: Annotated[str, "connected_account", "Tool-owned value"],
) -> str:
    """A tool whose Annotated alias exposes the reserved name."""
    return value


@tool
def tool_reserved_name_after_valid(
    input_text: Annotated[str, "The text to process"],
    connected_account: Annotated[str, "The account to use"],
) -> str:
    """A tool that places the reserved name after a valid input."""
    return f"{input_text}:{connected_account}"


@tool(requires_auth=GitHub())
def tool_auth_reserved_name(connected_account: Annotated[str, "The account to use"]) -> str:
    """An authorized tool whose exposed input uses the reserved name."""
    return connected_account


@tool
def tool_permitted_alias(
    connected_account: Annotated[str, "account_reference", "Tool-owned value"],
) -> str:
    """A tool that renames the reserved Python identifier to a permitted exposed name."""
    return connected_account


@tool
def tool_near_match_connected_account_title(
    Connected_account: Annotated[str, "Near-match title-case name"],
) -> str:
    """A tool whose exposed name differs only by case."""
    return Connected_account


@tool
def tool_near_match_connected_accounts(
    connected_accounts: Annotated[str, "Near-match plural name"],
) -> str:
    """A tool whose exposed name is a near match, not the reserved name."""
    return connected_accounts


@tool
def tool_near_match_connected_account_id(
    connected_account_id: Annotated[str, "Near-match suffixed name"],
) -> str:
    """A tool whose exposed name is a related but unreserved identifier."""
    return connected_account_id


@tool
def tool_context_named_reserved(
    connected_account: ToolContext,
    input_text: Annotated[str, "The text to process"],
) -> str:
    """A tool whose injected ToolContext parameter uses the reserved Python name."""
    return input_text


@tool
def tool_mcp_context_named_reserved(
    connected_account: Context,
    input_text: Annotated[str, "The text to process"],
) -> str:
    """A tool whose injected Context parameter uses the reserved Python name."""
    return input_text


class AccountPayload(BaseModel):
    connected_account: str
    note: str = "ok"


@tool
def tool_nested_reserved_field(payload: Annotated[AccountPayload, "Account payload"]) -> str:
    """A tool with a nested model field named connected_account."""
    return payload.connected_account


class AccountResult(BaseModel):
    connected_account: str


@tool
def tool_output_reserved_field() -> AccountResult:
    """A tool whose output model includes connected_account."""
    return AccountResult(connected_account="acct")


@pytest.mark.parametrize(
    "func",
    [
        tool_required_reserved_name,
        tool_optional_reserved_name,
        tool_defaulted_reserved_name,
        tool_alias_reserved_name,
        tool_reserved_name_after_valid,
    ],
)
def test_create_input_definition_rejects_reserved_exposed_name(func):
    with pytest.raises(ToolInputSchemaError) as exc_info:
        create_input_definition(func)

    _assert_reserved_argument_error(exc_info.value)


@pytest.mark.parametrize(
    "func",
    [
        tool_required_reserved_name,
        tool_auth_reserved_name,
    ],
)
def test_create_tool_definition_rejects_reserved_exposed_name(func):
    with pytest.raises(ToolInputSchemaError) as exc_info:
        ToolCatalog.create_tool_definition(func, "test_toolkit", "1.0.0")

    _assert_reserved_argument_error(exc_info.value)
    assert "in definition of tool" not in str(exc_info.value)


def test_create_tool_definition_reserved_error_is_unwrapped():
    with pytest.raises(ToolInputSchemaError) as exc_info:
        ToolCatalog.create_tool_definition(tool_required_reserved_name, "test_toolkit")

    _assert_reserved_argument_error(exc_info.value)
    assert "in definition of tool" not in str(exc_info.value)


def test_add_tool_rejects_reserved_name_and_does_not_insert():
    catalog = ToolCatalog()

    with pytest.raises(ToolInputSchemaError) as exc_info:
        catalog.add_tool(tool_required_reserved_name, "test_toolkit")

    _assert_reserved_argument_error(exc_info.value)
    assert catalog.get_tool_count() == 0


def test_add_toolkit_rejects_reserved_name_and_does_not_insert():
    catalog = ToolCatalog()
    test_toolkit = Toolkit(
        name="test_toolkit",
        description="A test toolkit",
        version="1.0.0",
        package_name="test_toolkit",
    )
    test_toolkit.tools = {"tests.core.test_catalog": ["tool_required_reserved_name"]}

    import sys

    with patch("arcade_core.catalog.import_module", return_value=sys.modules[__name__]):
        with pytest.raises(ToolInputSchemaError) as exc_info:
            catalog.add_toolkit(test_toolkit)

    _assert_reserved_argument_error(exc_info.value)
    assert "tool_required_reserved_name" in str(exc_info.value)
    assert catalog.get_tool_count() == 0


def test_permitted_alias_emits_account_reference():
    definition = ToolCatalog.create_tool_definition(tool_permitted_alias, "test_toolkit", "1.0.0")

    assert [parameter.name for parameter in definition.input.parameters] == ["account_reference"]
    assert definition.input.parameters[0].required is True


@pytest.mark.parametrize(
    "func, expected_name",
    [
        (tool_near_match_connected_account_title, "Connected_account"),
        (tool_near_match_connected_accounts, "connected_accounts"),
        (tool_near_match_connected_account_id, "connected_account_id"),
    ],
)
def test_near_match_exposed_names_are_accepted(func, expected_name: str):
    definition = ToolCatalog.create_tool_definition(func, "test_toolkit", "1.0.0")
    assert [parameter.name for parameter in definition.input.parameters] == [expected_name]


def test_nested_connected_account_field_is_preserved():
    definition = ToolCatalog.create_tool_definition(
        tool_nested_reserved_field, "test_toolkit", "1.0.0"
    )

    payload_schema = definition.input.parameters[0].value_schema
    assert payload_schema.properties is not None
    assert "connected_account" in payload_schema.properties


def test_output_connected_account_field_is_preserved():
    definition = ToolCatalog.create_tool_definition(
        tool_output_reserved_field, "test_toolkit", "1.0.0"
    )

    assert definition.output.value_schema is not None
    assert definition.output.value_schema.properties is not None
    assert "connected_account" in definition.output.value_schema.properties


@pytest.mark.parametrize(
    "func, context_name",
    [
        (tool_context_named_reserved, "connected_account"),
        (tool_mcp_context_named_reserved, "connected_account"),
    ],
)
def test_injected_context_named_connected_account_is_not_an_exposed_input(func, context_name):
    definition = ToolCatalog.create_tool_definition(func, "test_toolkit", "1.0.0")

    assert definition.input.tool_context_parameter_name == context_name
    assert [parameter.name for parameter in definition.input.parameters] == ["input_text"]


def test_valid_tool_still_registers_with_original_input_metadata():
    catalog = ToolCatalog()
    catalog.add_tool(valid_tool, "sample_toolkit")

    materialized = catalog.get_tool(FullyQualifiedName("ValidTool", "SampleToolkit", None))
    parameters = materialized.definition.input.parameters
    assert [parameter.name for parameter in parameters] == ["input_text"]
    assert parameters[0].description == "The text to process"
    assert parameters[0].required is True
    assert catalog.get_tool_count() == 1


def test_create_func_models_does_not_apply_reserved_name_guard():
    input_model, _output_model = create_func_models(tool_required_reserved_name)

    assert "connected_account" in input_model.model_fields


def test_raw_tool_definition_deserializes_connected_account_input():
    payload = {
        "name": "Sample",
        "fully_qualified_name": "Test.Sample",
        "description": "A sample",
        "toolkit": {"name": "Test", "version": "1.0.0"},
        "input": {
            "parameters": [
                {
                    "name": "connected_account",
                    "required": True,
                    "description": "An account id",
                    "value_schema": {"val_type": "string"},
                }
            ]
        },
        "output": {},
        "requirements": {},
    }

    definition = ToolDefinition.model_validate(payload)

    assert definition.input.parameters[0].name == "connected_account"
    assert isinstance(definition.toolkit, ToolkitDefinition)
    assert isinstance(definition.input, ToolInput)
    assert isinstance(definition.output, ToolOutput)
    assert isinstance(definition.requirements, ToolRequirements)
    assert isinstance(definition.input.parameters[0], InputParameter)
    assert definition.input.parameters[0].value_schema == ValueSchema(val_type="string")
