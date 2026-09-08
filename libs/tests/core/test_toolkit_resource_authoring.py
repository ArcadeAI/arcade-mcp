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
from arcade_core.resources import ResourceDeclaration, resource
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

from arcade_core.resources import resource


@resource(path="dashboard.html", mime_type="text/html;profile=example")
def dashboard() -> str:
    return (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
"""

# A decorator from somewhere else that happens to be called "resource". The AST
# scan matches on the attribute name, so this reaches registration.
# Module scope in the source, and never bound when the module is imported.
GUARDED_MODULE = """
from arcade_core.resources import resource

if __name__ == "__main__":

    @resource(path="unreachable.html", mime_type="text/html")
    def unreachable() -> str:
        return "<html></html>"
"""

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
from arcade_core.resources import resource


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
from arcade_core.resources import resource


async def _read() -> str:
    return "<html>"


@resource(path="sneaky.html", mime_type="text/html")
def sneaky() -> str:
    return _read()
"""

# A second module declaring the same path, so both qualify to one URI.
SECOND_UI_MODULE = """
from arcade_core.resources import resource


@resource(path="dashboard.html", mime_type="text/html;profile=example")
def other_dashboard() -> str:
    return "<!DOCTYPE html><p>second</p>"
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
    _forget("arcade_widgets")


@pytest.fixture
def two_word_package(tmp_path, monkeypatch):
    """A toolkit whose name normalises to something other than itself.

    `arcade_widgets` is one word, so it hides every difference between the raw
    package name and the name a tool is published under.
    """
    root = tmp_path / "docs"
    package = root / "arcade_google_docs"
    package.mkdir(parents=True)

    (root / "pyproject.toml").write_text(
        '[project]\nname = "arcade_google_docs"\nversion = "8.1.0"\n', encoding="utf-8"
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "tools.py").write_text(textwrap.dedent(TOOL_MODULE), encoding="utf-8")
    (package / "ui.py").write_text(textwrap.dedent(RESOURCE_MODULE), encoding="utf-8")
    (package / "dashboard.html").write_text("<!DOCTYPE html><p>hi</p>", encoding="utf-8")

    monkeypatch.syspath_prepend(str(root))
    _forget("arcade_google_docs")
    yield root
    _forget("arcade_google_docs")


def _forget(package_name):
    for name in [n for n in sys.modules if n == package_name or n.startswith(package_name + ".")]:
        del sys.modules[name]


def test_a_resource_uri_uses_the_same_toolkit_name_a_tool_does(two_word_package):
    """Registry lookup is exact, so one name spelled two ways is a 404."""
    catalog = ToolCatalog()
    catalog.add_toolkit(Toolkit.from_directory(two_word_package))

    tool = next(iter(catalog))
    expected = (
        f"ui://{tool.definition.toolkit.name}/{tool.definition.toolkit.version}/dashboard.html"
    )

    # Derived from the tool rather than written out, so the two cannot drift
    # apart without this failing.
    assert catalog.resources.get(expected).resource.uri == expected


def test_a_declaration_in_init_registers_without_importing_it_twice(tmp_path, monkeypatch):
    """Importing `pkg.__init__` runs the package body again as a second module object."""
    root = tmp_path / "initpkg"
    package = root / "arcade_initpkg"
    package.mkdir(parents=True)

    (root / "pyproject.toml").write_text(
        '[project]\nname = "arcade_initpkg"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (package / "__init__.py").write_text(
        textwrap.dedent("""
            from arcade_core.resources import resource

            RAN = []
            RAN.append(1)

            @resource(path="from-init.html", mime_type="text/html")
            def from_init() -> str:
                return "<html></html>"
        """),
        encoding="utf-8",
    )
    (package / "tools.py").write_text(textwrap.dedent(TOOL_MODULE), encoding="utf-8")
    monkeypatch.syspath_prepend(str(root))
    _forget("arcade_initpkg")

    toolkit = Toolkit.from_directory(root)
    assert "arcade_initpkg" in toolkit.resources
    assert "arcade_initpkg.__init__" not in toolkit.resources

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert "arcade_initpkg.__init__" not in sys.modules
    assert len(sys.modules["arcade_initpkg"].RAN) == 1, "the package body ran twice"
    assert len(catalog.resources) == 1
    _forget("arcade_initpkg")


def test_a_declaration_in_main_does_not_run_the_entrypoint(tmp_path, monkeypatch, caplog):
    """Importing `pkg.__main__` starts the toolkit's server while the catalog is loading."""
    root = tmp_path / "mainpkg"
    package = root / "arcade_mainpkg"
    package.mkdir(parents=True)

    (root / "pyproject.toml").write_text(
        '[project]\nname = "arcade_mainpkg"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(
        textwrap.dedent("""
            from arcade_core.resources import resource

            raise AssertionError("the entrypoint ran during catalog load")

            @resource(path="from-main.html", mime_type="text/html")
            def from_main() -> str:
                return "<html></html>"
        """),
        encoding="utf-8",
    )
    (package / "tools.py").write_text(textwrap.dedent(TOOL_MODULE), encoding="utf-8")
    monkeypatch.syspath_prepend(str(root))
    _forget("arcade_mainpkg")

    toolkit = Toolkit.from_directory(root)
    assert "arcade_mainpkg.__main__" not in toolkit.resources
    assert "arcade_mainpkg.__main__" in caplog.text

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert "arcade_mainpkg.__main__" not in sys.modules
    assert len(catalog) == 1, "the toolkit's tools still load"
    _forget("arcade_mainpkg")


def test_discovery_records_a_resource_module_that_declares_no_tools(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)

    assert toolkit.resources == {"arcade_widgets.ui": ["dashboard"]}
    assert toolkit.tools["arcade_widgets.ui"] == []


def test_a_declared_resource_is_registered_with_a_qualified_uri(widgets_package):
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    catalog.add_toolkit(toolkit)

    registered = catalog.resources.get("ui://Widgets/2.3.1/dashboard.html")
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

    assert "ui://Widgets/9.9.9/dashboard.html" in catalog.resources


def test_the_decorator_leaves_the_function_callable():
    """A toolkit's own tests should be able to call the function directly."""

    @resource(path="a.html", mime_type="text/plain")
    def body() -> str:
        return "hello"

    assert body() == "hello"
    assert isinstance(body, ResourceDeclaration)


def test_the_declaration_name_defaults_to_the_function_name():
    @resource(path="a.html")
    def draft_review() -> str:
        return "x"

    assert draft_review.name == "draft_review"


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
    """The scan knows this one is ours, so a replaced declaration is diagnosable."""
    (widgets_package / "arcade_widgets" / "wrapped.py").write_text(
        textwrap.dedent(WRAPPED_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    with pytest.raises(ToolkitLoadError) as exc_info:
        catalog.add_toolkit(toolkit)

    assert "declaration" in str(exc_info.value)
    assert "arcade_widgets.wrapped" in str(exc_info.value)


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
    """Every spelling that binds our decorator is the same declaration.

    A toolkit author writes the first one. The rest are here because discovery
    resolves the decorator against the module's imports, so each binding has to
    be recognised or the declaration goes missing with nothing raised.
    """
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    for source in (
        "from arcade_core.resources import resource\n\n@resource(path='a.html')\ndef a(): ...",
        "import arcade_mcp_server\n\n@arcade_mcp_server.resource(path='a.html')\ndef a(): ...",
        # arcade_tdk re-exports it, and a toolkit written before the move may
        # still reach for it directly.
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


def test_only_module_level_declarations_are_discovered():
    """Registration reaches a declaration with getattr on the module, and nothing else."""
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    header = "from arcade_core.resources import resource\n\n"
    for source in (
        # A method is an attribute of the class, not of the module.
        "class Widgets:\n    @resource(path='a.html')\n    def a(self): ...",
        # A nested function is a local of its enclosing one.
        "def outer():\n    @resource(path='a.html')\n    def a(): ...\n    return a",
        "async def outer():\n    @resource(path='a.html')\n    def a(): ...",
        # A class nested in a function is doubly out of reach.
        "def outer():\n    class Inner:\n        @resource(path='a.html')\n        def a(self): ...",
    ):
        assert get_resources_from_ast(_ast.parse(header + source)) == [], source


def test_a_declaration_guarded_by_a_module_level_block_is_discovered():
    """if, try and with keep module scope, so the name really can become an attribute."""
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    header = "from arcade_core.resources import resource\n\n"
    for source in (
        "if True:\n    @resource(path='a.html')\n    def a(): ...",
        "if False:\n    pass\nelse:\n    @resource(path='a.html')\n    def a(): ...",
        "try:\n    @resource(path='a.html')\n    def a(): ...\nexcept ImportError:\n    pass",
        "try:\n    pass\nexcept ImportError:\n    @resource(path='a.html')\n    def a(): ...",
        "try:\n    pass\nfinally:\n    @resource(path='a.html')\n    def a(): ...",
        "for _ in range(1):\n    @resource(path='a.html')\n    def a(): ...",
        "with open(__file__):\n    @resource(path='a.html')\n    def a(): ...",
        # A match case body hangs off `cases`, which is not a field any of the
        # others use. Walking every child rather than a list of field names is
        # what keeps a statement like this from going missing.
        "match 1:\n    case 1:\n        @resource(path='a.html')\n        def a(): ...",
    ):
        assert get_resources_from_ast(_ast.parse(header + source)) == ["a"], source


def test_a_name_written_in_two_branches_is_one_declaration():
    """Only one arm binds at import, so counting both would fail a toolkit with no duplicate."""
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    header = "from arcade_core.resources import resource\n\n"
    for source in (
        "if True:\n    @resource(path='a.html')\n    def a(): ...\n"
        "else:\n    @resource(path='a.html')\n    def a(): ...",
        "try:\n    @resource(path='a.html')\n    def a(): ...\n"
        "except ImportError:\n    @resource(path='a.html')\n    def a(): ...",
    ):
        assert get_resources_from_ast(_ast.parse(header + source)) == ["a"], source


def test_two_declarations_sharing_a_path_are_still_both_found():
    """Deduplication is by name, so it must not hide a real duplicate from the registry."""
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    source = (
        "from arcade_core.resources import resource\n\n"
        "@resource(path='a.html')\ndef a(): ...\n\n"
        "@resource(path='a.html')\ndef b(): ..."
    )

    assert get_resources_from_ast(_ast.parse(source)) == ["a", "b"]


def test_a_declaration_the_module_never_binds_is_skipped_not_fatal(widgets_package, caplog):
    """A __main__ guard is module scope in the source and absent after an import."""
    (widgets_package / "arcade_widgets" / "guarded.py").write_text(
        textwrap.dedent(GUARDED_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)
    assert "unreachable" in toolkit.resources["arcade_widgets.guarded"]

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    assert len(catalog) == 1, "the toolkit's tools must survive an unreachable declaration"
    assert len(catalog.resources) == 1, "and its reachable resource must still register"
    assert "arcade_widgets.guarded.unreachable" in caplog.text


def test_a_disabled_toolkit_registers_no_resources(widgets_package, monkeypatch):
    """Hiding a toolkit's tools must not leave its resources on the worker."""
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()
    monkeypatch.setattr(catalog, "_disabled_toolkits", {"widgets"})

    catalog.add_toolkit(toolkit)

    assert len(catalog.resources) == 0


def test_a_decorator_we_do_not_export_is_still_refused():
    """The import resolution buys precision, so it must not become a rubber stamp."""
    import ast as _ast

    from arcade_core.parse import get_resources_from_ast

    for source in (
        # Ours is never imported, so a same-named decorator is not ours.
        "from arcade_mcp_server import MCPApp\napp = MCPApp(name='x')\n\n@app.resource('ui://x')\ndef a(): ...",
        "@resource(path='a.html')\ndef a(): ...",
        # A star import from somewhere else binds nothing of ours.
        "from somewhere_else import *\n\n@resource(path='a.html')\ndef a(): ...",
    ):
        assert get_resources_from_ast(_ast.parse(source)) == [], source


def test_two_resources_sharing_a_path_fail_the_toolkit(widgets_package):
    """Qualification collapses them to one URI, and last-writer-wins loses the first."""
    (widgets_package / "arcade_widgets" / "ui_two.py").write_text(
        textwrap.dedent(SECOND_UI_MODULE), encoding="utf-8"
    )
    toolkit = Toolkit.from_directory(widgets_package)
    catalog = ToolCatalog()

    with pytest.raises(ToolkitLoadError) as exc_info:
        catalog.add_toolkit(toolkit)

    message = str(exc_info.value)
    assert "ui://Widgets/2.3.1/dashboard.html" in message
    assert "other_dashboard" in message
    assert "dashboard" in message

    # The guard runs before declare, which replaces on a repeated URI. Run after,
    # it would raise about a resource it had just overwritten, and any caller that
    # caught this would be left holding the second one.
    kept = catalog.resources.get("ui://Widgets/2.3.1/dashboard.html")
    assert kept.resource.name == "dashboard", "the first declaration must survive the conflict"
