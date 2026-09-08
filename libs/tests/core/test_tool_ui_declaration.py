"""A tool passes the declaration of its user interface, and the catalog does the rest.

The tool and its interface are qualified by one derivation, so they agree without
the author ever writing a URI. Registering the tool registers the interface, so a
tool can only point at something the catalog serves.
"""

import sys
import textwrap

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolDefinitionError, ToolkitLoadError
from arcade_core.resources import UI_DOCUMENT_MIME_TYPE, resource, ui_pointer
from arcade_core.toolkit import Toolkit
from arcade_tdk import tool

UI_MODULE = '''
from arcade_core.resources import resource


@resource(file="dashboard.html")
def dashboard() -> None:
    """The numbers and their sum."""


@resource(path="report.html", mime_type="text/html")
def report() -> str:
    return "<!DOCTYPE html><p>report</p>"
'''

TOOLS_MODULE = '''
from typing import Annotated

from arcade_tdk import tool

from arcade_widgets.ui import dashboard


@tool(ui=dashboard)
def add_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The sum"]:
    """Add two numbers."""
    return a + b


@tool(ui=dashboard)
def multiply_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The product"]:
    """Multiply two numbers."""
    return a * b


@tool
def subtract_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The difference"]:
    """Subtract two numbers."""
    return a - b
'''

WRONG_TYPE_UI_MODULE = '''
from arcade_core.resources import resource


@resource(file="dashboard.html", mime_type="text/html")
def dashboard() -> None:
    """Declared as plain HTML, which a host will not render as an interface."""
'''

SECOND_UI_MODULE = """
from arcade_core.resources import resource


@resource(path="dashboard.html", mime_type="text/html")
def other_dashboard() -> str:
    return "<!DOCTYPE html><p>other</p>"
"""

TWIN_UI_MODULE = """
from arcade_core.resources import resource


@resource(path="dashboard.html", name="dashboard", mime_type="text/html")
def first() -> str:
    return "<!DOCTYPE html><p>first</p>"


@resource(path="dashboard.html", name="dashboard", mime_type="text/html")
def second() -> str:
    return "<!DOCTYPE html><p>second</p>"
"""

DASHBOARD_HTML = "<!DOCTYPE html><p>hi</p>"


def _forget(package_name):
    for name in [n for n in sys.modules if n == package_name or n.startswith(package_name + ".")]:
        del sys.modules[name]


@pytest.fixture
def build_toolkit(tmp_path, monkeypatch):
    """Write a toolkit to disk and load it the way installed-toolkit discovery does."""
    name = "arcade_widgets"

    def build(version="2.3.1", tools_source=TOOLS_MODULE, ui_source=UI_MODULE, extra=None):
        root = tmp_path / name
        package = root / name
        package.mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
        )
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "ui.py").write_text(textwrap.dedent(ui_source), encoding="utf-8")
        (package / "dashboard.html").write_text(DASHBOARD_HTML, encoding="utf-8")
        (package / "tools.py").write_text(textwrap.dedent(tools_source), encoding="utf-8")
        for filename, source in (extra or {}).items():
            (package / filename).write_text(textwrap.dedent(source), encoding="utf-8")
        monkeypatch.syspath_prepend(str(root))
        _forget(name)
        return Toolkit.from_directory(root)

    yield build
    _forget(name)


def _by_name(catalog):
    return {materialized.definition.name: materialized.definition for materialized in catalog}


def _uri(definition, path):
    # Built from the tool's own toolkit fields rather than written out, so the
    # two derivations cannot drift apart without this failing.
    return f"ui://{definition.toolkit.name}/{definition.toolkit.version}/{path}"


def test_the_tool_and_its_interface_share_one_uri(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit())

    add = _by_name(catalog)["AddNumbers"]
    uri = _uri(add, "dashboard.html")

    assert add.meta == ui_pointer(uri)
    assert catalog.resources.get(uri).contents.text == DASHBOARD_HTML


def test_an_interface_needs_no_media_type_from_its_author(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit())

    add = _by_name(catalog)["AddNumbers"]
    registered = catalog.resources.get(_uri(add, "dashboard.html")).resource

    assert registered.mimeType == UI_DOCUMENT_MIME_TYPE
    assert registered.description == "The numbers and their sum."


def test_two_tools_sharing_an_interface_register_it_once(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit())

    definitions = _by_name(catalog)

    assert definitions["AddNumbers"].meta == definitions["MultiplyNumbers"].meta
    assert [registered.resource.name for registered in catalog.resources] == ["dashboard", "report"]


def test_a_tool_that_names_no_interface_carries_no_pointer(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit())

    assert _by_name(catalog)["SubtractNumbers"].meta is None


def test_the_pointer_serializes_under_the_underscore_key(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit())

    add = _by_name(catalog)["AddNumbers"]
    dumped = add.model_dump(by_alias=True, exclude_none=True)

    assert dumped["_meta"] == {"ui": {"resourceUri": _uri(add, "dashboard.html")}}
    assert "meta" not in dumped


def test_an_interface_declared_with_another_media_type_fails_the_load(build_toolkit):
    toolkit = build_toolkit(ui_source=WRONG_TYPE_UI_MODULE)

    with pytest.raises(ToolDefinitionError, match="text/html;profile=mcp-app"):
        ToolCatalog().add_toolkit(toolkit)


def test_a_second_declaration_of_the_same_path_fails_the_load(build_toolkit):
    toolkit = build_toolkit(extra={"more_ui.py": SECOND_UI_MODULE})

    with pytest.raises(ToolkitLoadError, match="both declare"):
        ToolCatalog().add_toolkit(toolkit)


def test_two_declarations_that_read_alike_are_still_two(build_toolkit):
    """Only the declaration object itself counts as already registered, never a lookalike."""
    toolkit = build_toolkit(extra={"twins.py": TWIN_UI_MODULE})

    with pytest.raises(ToolkitLoadError, match="both declare"):
        ToolCatalog().add_toolkit(toolkit)


def test_registering_a_tool_alone_registers_its_interface():
    @resource(path="dashboard.html")
    def dashboard() -> str:
        return DASHBOARD_HTML

    @tool(ui=dashboard)
    def show() -> str:
        """Show a dashboard."""
        return ""

    catalog = ToolCatalog()
    catalog.add_tool(show, "widgets", toolkit_version="1.0.0")

    registered = catalog.resources.get("ui://Widgets/1.0.0/dashboard.html")

    assert registered.resource.mimeType == UI_DOCUMENT_MIME_TYPE
    assert registered.contents.text == DASHBOARD_HTML


def test_the_uri_is_qualified_by_the_normalized_toolkit_name_and_version():
    @resource(path="ui/dashboard.html")
    def dashboard() -> str:
        return DASHBOARD_HTML

    @tool(ui=dashboard)
    def show() -> str:
        """Show a dashboard."""
        return ""

    definition = ToolCatalog.create_tool_definition(show, "arcade_google_docs", "8.1.0")

    assert definition.meta == ui_pointer(f"ui://{definition.toolkit.name}/8.1.0/ui/dashboard.html")


def test_a_toolkit_without_a_version_cannot_name_an_interface():
    @resource(path="dashboard.html")
    def dashboard() -> str:
        return DASHBOARD_HTML

    @tool(ui=dashboard)
    def show() -> str:
        """Show a dashboard."""
        return ""

    with pytest.raises(ToolDefinitionError, match="version"):
        ToolCatalog.create_tool_definition(show, "widgets")


def test_a_traversing_path_is_refused_when_the_tool_is_defined():
    @resource(path="../secret.html")
    def secret() -> str:
        return ""

    @tool(ui=secret)
    def show() -> str:
        """Show a dashboard."""
        return ""

    with pytest.raises(ToolDefinitionError, match="traverse"):
        ToolCatalog.create_tool_definition(show, "widgets", "1.0.0")
