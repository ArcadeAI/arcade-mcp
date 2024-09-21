import pytest

from arcade.core.catalog import ToolCatalog
from arcade.core.schema import FullyQualifiedName
from arcade.core.toolkit import Toolkit
from arcade.sdk import tool


@tool
def sample_tool() -> str:
    """
    A sample tool function
    """
    return "Hello, world!"


def test_add_tool_with_no_toolkit():
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool)
    assert catalog.get_tool(FullyQualifiedName("SampleTool", "Tools", None)).tool == sample_tool


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
