from arcade.core.toolkit import Toolkit
from arcade.sdk import tool
import pytest
from arcade.core.catalog import ToolCatalog
from arcade.core.schema import FullyQualifiedToolName


@tool
def sample_tool() -> str:
    """
    A sample tool function
    """
    return "Hello, world!"


@pytest.fixture
def catalog() -> ToolCatalog:
    catalog = ToolCatalog()
    fake_toolkit = Toolkit(
        name="sample_toolkit",
        description="A sample toolkit",
        version="1.0.0",
        package_name="sample_toolkit",
    )
    catalog.add_tool(sample_tool, fake_toolkit, module=None)
    return catalog


@pytest.mark.parametrize(
    "toolkit_version, expected_tool",
    [
        ("1.0.0", sample_tool),
        (None, sample_tool),
    ],
)
def test_get_tool(catalog: ToolCatalog, toolkit_version: str | None, expected_tool):
    fq_name = FullyQualifiedToolName(
        name="SampleTool", toolkit_name="SampleToolkit", toolkit_version=toolkit_version
    )
    tool = catalog.get_tool(fq_name)

    assert tool.tool == expected_tool
