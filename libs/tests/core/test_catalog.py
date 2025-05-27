from unittest.mock import MagicMock, patch

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError
from arcade_core.schema import FullyQualifiedName
from arcade_core.toolkit import Toolkit
from arcade_tdk import tool


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
        patch("arcade_core.catalog.import_module") as mock_import,
        patch("arcade_core.catalog.getattr") as mock_getattr,
    ):
        mock_import.return_value = MagicMock()
        mock_getattr.return_value = InvalidTool()

        # Assert that ToolDefinitionError is raised
        with pytest.raises(ToolDefinitionError):
            catalog.add_toolkit(mock_toolkit)


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
