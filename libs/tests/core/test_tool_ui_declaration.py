"""A tool names its user interface by path, and the catalog derives the URI.

The tool and the resource it names are qualified by one derivation, so the two
agree without the author ever writing a URI. A tool naming a path nothing in its
toolkit declares fails the load, as every other authoring mistake does.
"""

import sys
import textwrap

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError, ToolkitLoadError
from arcade_core.resources import ui_pointer, ui_resource_uri
from arcade_core.toolkit import Toolkit
from arcade_tdk import tool

TOOLS_MODULE = '''
from typing import Annotated

from arcade_tdk import tool


@tool(ui="dashboard.html")
def add_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The sum"]:
    """Add two numbers."""
    return a + b


@tool
def subtract_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The difference"]:
    """Subtract two numbers."""
    return a - b
'''

UI_MODULE = """
from arcade_core.resources import resource


@resource(path="dashboard.html", mime_type="text/html;profile=example")
def dashboard() -> str:
    return "<!DOCTYPE html><p>hi</p>"
"""

DANGLING_TOOLS_MODULE = '''
from typing import Annotated

from arcade_tdk import tool


@tool(ui="missing.html")
def add_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The sum"]:
    """Add two numbers."""
    return a + b
'''


def _forget(package_name):
    for name in [n for n in sys.modules if n == package_name or n.startswith(package_name + ".")]:
        del sys.modules[name]


@pytest.fixture
def build_toolkit(tmp_path, monkeypatch):
    """Write a toolkit to disk and load it the way installed-toolkit discovery does."""
    built = []

    def build(name, version, tools_source, ui_source=None):
        root = tmp_path / name
        package = root / name
        package.mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
        )
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "tools.py").write_text(textwrap.dedent(tools_source), encoding="utf-8")
        if ui_source is not None:
            (package / "ui.py").write_text(textwrap.dedent(ui_source), encoding="utf-8")
        monkeypatch.syspath_prepend(str(root))
        _forget(name)
        built.append(name)
        return Toolkit.from_directory(root)

    yield build
    for name in built:
        _forget(name)


def _by_name(catalog):
    return {materialized.definition.name: materialized.definition for materialized in catalog}


def test_the_tool_and_its_resource_derive_the_same_uri(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", "2.3.1", TOOLS_MODULE, UI_MODULE))

    add = _by_name(catalog)["AddNumbers"]
    # Built from the tool's own toolkit fields rather than written out, so the
    # two derivations cannot drift apart without this failing.
    expected = f"ui://{add.toolkit.name}/{add.toolkit.version}/dashboard.html"

    assert ui_resource_uri(add.meta) == expected
    assert catalog.resources.get(expected).resource.uri == expected


def test_a_tool_that_names_no_interface_carries_no_pointer(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", "2.3.1", TOOLS_MODULE, UI_MODULE))

    assert _by_name(catalog)["SubtractNumbers"].meta is None


def test_the_pointer_serializes_under_the_underscore_key(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", "2.3.1", TOOLS_MODULE, UI_MODULE))

    add = _by_name(catalog)["AddNumbers"]
    dumped = add.model_dump(by_alias=True, exclude_none=True)

    assert dumped["_meta"] == ui_pointer(ui_resource_uri(add.meta))
    assert "meta" not in dumped


def test_a_path_no_resource_declares_fails_the_toolkit(build_toolkit):
    toolkit = build_toolkit("arcade_widgets", "2.3.1", DANGLING_TOOLS_MODULE, UI_MODULE)

    with pytest.raises(ToolkitLoadError, match=r"AddNumbers.*missing\.html") as raised:
        ToolCatalog().add_toolkit(toolkit)

    assert "@resource" in str(raised.value)


def test_a_toolkit_with_no_resources_fails_the_same_way(build_toolkit):
    toolkit = build_toolkit("arcade_widgets", "2.3.1", DANGLING_TOOLS_MODULE)

    with pytest.raises(ToolkitLoadError, match=r"missing\.html"):
        ToolCatalog().add_toolkit(toolkit)


def test_the_uri_is_qualified_by_the_normalized_toolkit_name_and_version():
    @tool(ui="ui/dashboard.html")
    def show() -> str:
        """Show a dashboard."""
        return ""

    definition = ToolCatalog.create_tool_definition(show, "arcade_google_docs", "8.1.0")

    assert (
        ui_resource_uri(definition.meta)
        == f"ui://{definition.toolkit.name}/8.1.0/ui/dashboard.html"
    )


def test_a_toolkit_without_a_version_cannot_name_an_interface():
    @tool(ui="dashboard.html")
    def show() -> str:
        """Show a dashboard."""
        return ""

    with pytest.raises(ToolDefinitionError, match="version"):
        ToolCatalog.create_tool_definition(show, "widgets")


def test_a_traversing_path_is_refused_when_the_tool_is_defined():
    @tool(ui="../secret.html")
    def show() -> str:
        """Show a dashboard."""
        return ""

    with pytest.raises(ToolDefinitionError, match="traverse"):
        ToolCatalog.create_tool_definition(show, "widgets", "1.0.0")


def test_ui_resource_uri_reads_only_a_well_formed_pointer():
    assert ui_resource_uri(None) is None
    assert ui_resource_uri({}) is None
    assert ui_resource_uri({"ui": "not an object"}) is None
    assert ui_resource_uri({"ui": {"resourceUri": 7}}) is None
    assert ui_resource_uri(ui_pointer("ui://Kit/1.0.0/a.html")) == "ui://Kit/1.0.0/a.html"
