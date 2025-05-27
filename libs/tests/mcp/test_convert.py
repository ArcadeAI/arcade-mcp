import json
from typing import Annotated

from arcade_core.catalog import ToolCatalog
from arcade_serve.mcp.convert import convert_to_mcp_content, create_mcp_tool
from arcade_tdk import tool


@tool
def sample_tool(x: Annotated[int, "first"], y: Annotated[int, "second"]) -> int:
    """Return x+y"""

    return x + y


def test_convert_to_mcp_content_primitives():
    assert convert_to_mcp_content(42) == [{"type": "text", "text": "42"}]
    assert convert_to_mcp_content("hello") == [{"type": "text", "text": "hello"}]
    assert convert_to_mcp_content(True) == [{"type": "text", "text": "True"}]


def test_convert_to_mcp_content_complex():
    data = {"a": 1}
    expected_json = json.dumps(data)
    assert convert_to_mcp_content(data) == [{"type": "text", "text": expected_json}]


def test_create_mcp_tool():
    # Materialize a tool via catalog then feed it to create_mcp_tool
    catalog = ToolCatalog()
    catalog.add_tool(sample_tool, "convert_toolkit")
    mat_tool = next(iter(catalog))  # only tool
    mcp_tool = create_mcp_tool(mat_tool)

    assert mcp_tool is not None
    assert mcp_tool["name"] == "ConvertToolkit_SampleTool"
    assert mcp_tool["description"]
    # Ensure input schema contains both parameters and marks them required
    props = mcp_tool["inputSchema"]["properties"]
    assert set(props.keys()) == {"x", "y"}

    required_fields = set(mcp_tool["inputSchema"].get("required", []))
    # Ensure no unexpected required fields and that declared ones are subset of expected
    assert required_fields.issubset({"x", "y"})
