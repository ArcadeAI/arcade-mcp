from unittest.mock import MagicMock, patch

import pytest

from arcade.core.catalog import ToolCatalog
from arcade.core.errors import ToolDefinitionError
from arcade.core.schema import FullyQualifiedName
from arcade.core.toolkit import Toolkit
from arcade.sdk import tool


@tool
def sample_tool() -> str:
    """
    A sample tool function
    """
    return "Hello, world!"


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
        patch("arcade.core.catalog.import_module") as mock_import,
        patch("arcade.core.catalog.getattr") as mock_getattr,
    ):
        mock_import.return_value = MagicMock()
        mock_getattr.return_value = InvalidTool()

        # Assert that ToolDefinitionError is raised with the correct message
        with pytest.raises(ToolDefinitionError) as exc_info:
            catalog.add_toolkit(mock_toolkit)

        assert "Type error encountered while adding tool invalid_tool from mock_module" in str(
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
