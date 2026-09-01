import textwrap

from arcade_core.discovery import analyze_files_for_tools
from loguru import logger


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
