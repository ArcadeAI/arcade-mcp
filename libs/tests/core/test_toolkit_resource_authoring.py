"""A toolkit declares a resource, and installed-toolkit discovery finds it.

The channel has to survive the discovery pipeline a worker runs at startup.
Discovery is AST-based, and the import in add_toolkit sits inside the per-tool
loop, so a module contributing zero tools is never imported. That is why the app
object a toolkit builds in its entrypoint cannot carry declarations, and why
these tests pin the whole pipeline.
"""

import sys
import textwrap

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolkitLoadError
from arcade_core.resources import RESOURCE_ATTRIBUTE, ResourceDeclaration, resource
from arcade_core.toolkit import Toolkit

TOOL_MODULE = '''
from typing import Annotated

from arcade_tdk import tool


@tool
def add_numbers(
    a: Annotated[int, "The first number"],
    b: Annotated[int, "The second number"],
) -> Annotated[int, "The sum"]:
    """Add two numbers."""
    return a + b
'''

RESOURCE_MODULE = """
from pathlib import Path

from arcade_tdk import resource


@resource(path="dashboard.html", mime_type="text/html;profile=example")
def dashboard() -> str:
    return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
"""

# A decorator from somewhere else that happens to be called "resource". The AST
# scan matches on the attribute name, so this reaches registration.
LOOKALIKE_MODULE = """
class _App:
    def resource(self, uri, **kwargs):
        def decorator(func):
            return func

        return decorator


app = _App()


@app.resource("ui://not-ours.html", mime_type="text/html")
def not_ours() -> str:
    return "<html>"
"""

# @resource under a decorator that replaces the function without copying its
# attributes, so the declaration never reaches the module attribute.
WRAPPED_MODULE = """
from arcade_tdk import resource


def logged(fn):
    def inner(*args, **kwargs):
        return fn(*args, **kwargs)

    return inner


@logged
@resource(path="wrapped.html", mime_type="text/html")
def wrapped() -> str:
    return "<html>"
"""

# A synchronous function that hands back a coroutine. iscoroutinefunction says
# no, so only the returned value gives it away.
COROUTINE_MODULE = """
from arcade_tdk import resource


async def _read() -> str:
    return "<html>"


@resource(path="sneaky.html", mime_type="text/html")
def sneaky() -> str:
    return _read()
"""

PYPROJECT = """
[project]
name = "arcade_widgets"
version = "2.3.1"
description = "A fixture toolkit"
"""


@pytest.fixture
def widgets_package(tmp_path, monkeypatch):
    """A toolkit whose resource lives in a module containing no tools at all."""
    root = tmp_path / "widgets"
    package = root / "arcade_widgets"
    package.mkdir(parents=True)

    (root / "pyproject.toml").write_text(textwrap.dedent(PYPROJECT), encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "tools.py").write_text(textwrap.dedent(TOOL_MODULE), encoding="utf-8")
    (package / "ui.py").write_text(textwrap.dedent(RESOURCE_MODULE), encoding="utf-8")
    (package / "dashboard.html").write_text("<!DOCTYPE html><p>hi</p>", encoding="utf-8")

    monkeypatch.syspath_prepend(str(root))

    # Each test builds the package in a fresh tmp_path. Without dropping the
    # cached modules, a later test imports the earlier test's files.
    _forget_package()
    yield root
    _forget_package()


def _forget_package():
    for name in [
        n for n in sys.modules if n == "arcade_widgets" or n.startswith("arcade_widgets.")
    ]:
        del sys.modules[name]


def test_discovery_records_a_resource_module_that_declares_no_tools(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)

    assert toolkit.resources == {"arcade_widgets.ui": ["dashboard"]}
    assert toolkit.tools["arcade_widgets.ui"] == []


def test_a_declared_resource_is_registered_with_a_qualified_uri(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    catalog.add_toolkit(toolkit)

    registered = catalog.resources.get("ui://widgets/2.3.1/dashboard.html")
    assert registered.resource.name == "dashboard"
    assert registered.resource.mimeType == "text/html;profile=example"
    assert registered.contents.text == "<!DOCTYPE html><p>hi</p>"


def test_registering_resources_does_not_disturb_the_tool_catalog(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    catalog.add_toolkit(toolkit)

    assert len(catalog) == 1
    assert len(catalog.resources) == 1


def test_a_toolkit_declaring_nothing_registers_no_resources(widgets_package):
    (widgets_package / "arcade_widgets" / "ui.py").unlink()
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    catalog.add_toolkit(toolkit)

    assert toolkit.resources == {}
    assert len(catalog.resources) == 0


def test_a_resource_that_cannot_load_fails_the_toolkit(widgets_package):
    """A resource is a toolkit primitive, so a broken one fails registration as a tool would."""
    (widgets_package / "arcade_widgets" / "dashboard.html").unlink()
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    with pytest.raises(ToolkitLoadError) as exc_info:
        catalog.add_toolkit(toolkit)

    assert "dashboard" in str(exc_info.value)
    assert "widgets" in str(exc_info.value)


def test_the_version_registered_is_the_toolkit_version(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    catalog.add_toolkit(toolkit, version="9.9.9")

    assert "ui://widgets/9.9.9/dashboard.html" in catalog.resources


def test_the_decorator_leaves_the_function_callable():
    """A toolkit's own tests should be able to call the function directly."""

    @resource(path="a.html", mime_type="text/plain")
    def body() -> str:
        return "hello"

    assert body() == "hello"
    assert isinstance(getattr(body, RESOURCE_ATTRIBUTE), ResourceDeclaration)


def test_the_declaration_name_defaults_to_the_function_name():
    @resource(path="a.html")
    def draft_review() -> str:
        return "x"

    assert getattr(draft_review, RESOURCE_ATTRIBUTE).name == "draft_review"



def test_the_decorator_refuses_an_async_function():
    """Registration calls the function synchronously, so an async one cannot work."""
    with pytest.raises(TypeError) as exc_info:
        @resource(path="a.html", mime_type="text/html")
        async def a() -> str:
            return "<html>"

    assert "async" in str(exc_info.value)


def test_a_lookalike_decorator_is_never_recorded_by_discovery(widgets_package):
    """@app.resource belongs to something else, so the scan resolves it away."""
    (widgets_package / "arcade_widgets" / "vendor.py").write_text(
        textwrap.dedent(LOOKALIKE_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)

    assert "arcade_widgets.vendor" not in toolkit.resources

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert len(catalog) == 1
    assert len(catalog.resources) == 1


def test_a_declaration_lost_to_a_wrapper_is_reported(widgets_package):
    """The scan knows this one is ours, so a missing marker is diagnosable."""
    (widgets_package / "arcade_widgets" / "wrapped.py").write_text(
        textwrap.dedent(WRAPPED_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    with pytest.raises(ToolkitLoadError) as exc_info:
        catalog.add_toolkit(toolkit)

    assert "functools.wraps" in str(exc_info.value)
    assert "wrapped" in str(exc_info.value)


def test_a_resource_returning_a_coroutine_is_reported(widgets_package):
    """A sync wrapper around an async read passes every check on the function."""
    (widgets_package / "arcade_widgets" / "sneaky.py").write_text(
        textwrap.dedent(COROUTINE_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    with pytest.raises(ToolkitLoadError) as exc_info:
        catalog.add_toolkit(toolkit)

    assert "coroutine" in str(exc_info.value)


def test_the_decorator_is_found_through_its_module(widgets_package):
    """@arcade_tdk.resource and an aliased import are the same declaration."""
    from arcade_core.parse import get_resources_from_ast
    import ast as _ast

    for source in (
        "import arcade_tdk\n\n@arcade_tdk.resource(path='a.html')\ndef a(): ...",
        "from arcade_tdk import resource as res\n\n@res(path='a.html')\ndef a(): ...",
        # The dotted binding `import arcade_core.resources` creates is a chain of
        # attributes, not a single-name receiver.
        "import arcade_core.resources\n\n@arcade_core.resources.resource(path='a.html')\ndef a(): ...",
        "import arcade_core.resources as r\n\n@r.resource(path='a.html')\ndef a(): ...",
        # A star import binds the name without naming it.
        "from arcade_tdk import *\n\n@resource(path='a.html')\ndef a(): ...",
        "from arcade_mcp_server import *\n\n@resource(path='a.html')\ndef a(): ...",
        # Importing the module out of its package, rather than the decorator.
        "from arcade_core import resources\n\n@resources.resource(path='a.html')\ndef a(): ...",
        "from arcade_core import resources as r\n\n@r.resource(path='a.html')\ndef a(): ...",
    ):
        assert get_resources_from_ast(_ast.parse(source)) == ["a"], source


def test_a_disabled_toolkit_registers_no_resources(widgets_package, monkeypatch):
    """Hiding a toolkit's tools must not leave its resources on the worker."""
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()
    monkeypatch.setattr(catalog, "_disabled_toolkits", {"widgets"})

    catalog.add_toolkit(toolkit)

    assert len(catalog.resources) == 0


def test_a_decorator_we_do_not_export_is_still_refused():
    """The import resolution buys precision, so it must not become a rubber stamp."""
    from arcade_core.parse import get_resources_from_ast
    import ast as _ast

    for source in (
        # Ours is never imported, so a same-named decorator is not ours.
        "from arcade_mcp_server import MCPApp\napp = MCPApp(name='x')\n\n@app.resource('ui://x')\ndef a(): ...",
        "@resource(path='a.html')\ndef a(): ...",
        # A star import from somewhere else binds nothing of ours.
        "from somewhere_else import *\n\n@resource(path='a.html')\ndef a(): ...",
    ):
        assert get_resources_from_ast(_ast.parse(source)) == [], source
