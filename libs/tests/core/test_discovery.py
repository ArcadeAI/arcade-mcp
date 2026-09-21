import textwrap

import pytest
from arcade_core.discovery import (
    analyze_files_for_tools,
    collect_tools_from_modules,
    discover_tools,
    load_module_from_path,
)
from arcade_core.errors import ToolDefinitionError, ToolInputSchemaError
from loguru import logger

BROKEN_APP_TOOL = textwrap.dedent(
    """
    from arcade_mcp_server import MCPApp

    app = MCPApp(name="Test")

    @app.tool
    def broken() -> str:
        return "example"
    """
)

RESERVED_APP_TOOL = textwrap.dedent(
    """
    from typing import Annotated
    from arcade_mcp_server import MCPApp

    app = MCPApp(name="Reserved")

    @app.tool
    def reserved(connected_account: Annotated[str, "The account to use"]) -> str:
        \"\"\"A tool that collides with the reserved name.\"\"\"
        return connected_account
    """
)


VALID_APP_TOOL = textwrap.dedent(
    """
    from arcade_mcp_server import MCPApp

    app = MCPApp(name="Valid")

    @app.tool
    def ok() -> str:
        \"\"\"A valid tool.\"\"\"
        return "ok"
    """
)


def test_a_local_scan_warns_about_a_resource_it_cannot_register(tmp_path):
    """The decorator imports and runs here, and registers nothing.

    A loose-file scan loads one file at a time and never builds a Toolkit, so
    the registry it would go into does not exist. Saying so is the difference
    between a decorator that is unsupported on this path and one that looks
    supported and quietly does nothing.
    """
    both = tmp_path / "server.py"
    both.write_text(
        textwrap.dedent("""
            from typing import Annotated
            from arcade_core.resources import resource
            from arcade_tdk import tool

            @tool
            def add(a: Annotated[int, "a"]) -> Annotated[int, "b"]:
                \"\"\"Add.\"\"\"
                return a

            @resource(path="ui.html")
            def ui() -> str:
                return "<html></html>"
        """),
        encoding="utf-8",
    )
    only = tmp_path / "just_ui.py"
    only.write_text(
        'from arcade_tdk import resource\n\n@resource(path="x.html")\ndef x() -> str:\n    return "y"\n',
        encoding="utf-8",
    )

    # discovery.py logs through loguru, which does not reach caplog.
    captured: list[str] = []
    sink = logger.add(captured.append, level="WARNING", format="{message}")
    try:
        found = analyze_files_for_tools([both, only])
    finally:
        logger.remove(sink)
    warnings = "".join(captured)

    assert found == [(both, ["add"])], "the tool still loads"
    assert "server.py declares 1 resource(s) (ui)" in warnings
    # The resource-only file contributes no tools, so without the warning it
    # leaves the scan with nothing said about it at all.
    assert "just_ui.py declares 1 resource(s) (x)" in warnings


def test_load_module_from_path_preserves_tool_definition_error(tmp_path):
    tool_file = tmp_path / "broken.py"
    tool_file.write_text(BROKEN_APP_TOOL, encoding="utf-8")

    captured: list[str] = []
    sink = logger.add(captured.append, level="ERROR", format="{message}")
    try:
        with pytest.raises(ToolDefinitionError, match="broken") as exc_info:
            load_module_from_path(tool_file)
    finally:
        logger.remove(sink)

    assert "missing a description" in str(exc_info.value)
    assert any(str(tool_file) in message for message in captured)


def test_collection_and_discover_tools_propagate_definition_error(tmp_path, monkeypatch):
    valid_file = tmp_path / "valid.py"
    valid_file.write_text(VALID_APP_TOOL, encoding="utf-8")
    broken_file = tmp_path / "broken.py"
    broken_file.write_text(BROKEN_APP_TOOL, encoding="utf-8")

    files_with_tools = analyze_files_for_tools([valid_file, broken_file])
    with pytest.raises(ToolDefinitionError, match="broken"):
        collect_tools_from_modules(files_with_tools)

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ToolDefinitionError, match="broken"):
        discover_tools()


def test_load_module_from_path_preserves_reserved_argument_error(tmp_path):
    tool_file = tmp_path / "reserved.py"
    tool_file.write_text(RESERVED_APP_TOOL, encoding="utf-8")

    captured: list[str] = []
    sink = logger.add(captured.append, level="ERROR", format="{message}")
    try:
        with pytest.raises(ToolInputSchemaError, match="connected_account") as exc_info:
            load_module_from_path(tool_file)
    finally:
        logger.remove(sink)

    message = str(exc_info.value)
    assert "Arcade Engine" in message
    assert "Rename" in message
    assert "reserved" in message
    assert any(str(tool_file) in log_message for log_message in captured)


def test_collection_and_discover_tools_propagate_reserved_argument_error(tmp_path, monkeypatch):
    valid_file = tmp_path / "valid.py"
    valid_file.write_text(VALID_APP_TOOL, encoding="utf-8")
    reserved_file = tmp_path / "reserved.py"
    reserved_file.write_text(RESERVED_APP_TOOL, encoding="utf-8")

    files_with_tools = analyze_files_for_tools([valid_file, reserved_file])
    with pytest.raises(ToolInputSchemaError, match="connected_account") as exc_info:
        collect_tools_from_modules(files_with_tools)

    assert "Arcade Engine" in str(exc_info.value)

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ToolInputSchemaError, match="connected_account"):
        discover_tools()
