"""A document is addressed by the package that ships it, not by the server serving it.

One server can compose tools from several installed toolkits, and each toolkit
names its own documents without seeing the others. Qualifying by the composing
server puts authors who cannot see each other in one collision domain, so two
toolkits that both ship ``panel.html`` take the whole server down.
"""

import importlib
import sys
import textwrap

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolkitLoadError
from arcade_core.resources import _distribution_identity
from arcade_core.toolkit import Toolkit

UI_MODULE = '''
from arcade_core.resources import resource


@resource(file="panel.html")
def show_panel_ui() -> None:
    """The panel."""
'''

TOOLS_MODULE = '''
from typing import Annotated

from arcade_tdk import tool

from {package}.ui import show_panel_ui


@tool(ui=show_panel_ui, name="{tool_name}")
def show_panel() -> Annotated[str, "a note"]:
    """Show the panel."""
    return "shown"
'''

TWO_AT_ONE_PATH = """
from arcade_core.resources import resource


@resource(path="panel.html", name="first")
def first() -> str:
    return "<!DOCTYPE html><p>first</p>"


@resource(path="panel.html", name="second")
def second() -> str:
    return "<!DOCTYPE html><p>second</p>"
"""


@pytest.fixture
def build_package(tmp_path, monkeypatch):
    """Write an importable package, optionally as an installed distribution.

    ``importlib.metadata`` reads ``*.dist-info/METADATA`` off ``sys.path``, so
    writing one is what makes a package look installed to origin resolution.
    """
    built: list[str] = []

    def build(package, version=None, tool_name="ShowPanel", ui_source=UI_MODULE):
        root = tmp_path / package
        pkg = root / package
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "panel.html").write_text(f"<!DOCTYPE html><p>{package}</p>", encoding="utf-8")
        (pkg / "ui.py").write_text(textwrap.dedent(ui_source), encoding="utf-8")
        (pkg / "tools.py").write_text(
            textwrap.dedent(TOOLS_MODULE).format(package=package, tool_name=tool_name),
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "{package}"\nversion = "{version or "0.0.0"}"\n', encoding="utf-8"
        )
        if version is not None:
            dist = root / f"{package}-{version}.dist-info"
            dist.mkdir()
            (dist / "METADATA").write_text(
                f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n", encoding="utf-8"
            )
        monkeypatch.syspath_prepend(str(root))
        built.append(package)
        _forget(package)
        return root

    yield build
    for package in built:
        _forget(package)
    _distribution_identity.cache_clear()


def _forget(package):
    for name in [n for n in sys.modules if n == package or n.startswith(package + ".")]:
        del sys.modules[name]


@pytest.fixture(autouse=True)
def _clear_origin_cache():
    _distribution_identity.cache_clear()
    yield
    _distribution_identity.cache_clear()


def _pointed(definition):
    """The interface URI a tool's out-of-band data names."""
    return definition.meta["ui"]["resourceUri"]


def _tool(package):
    return importlib.import_module(f"{package}.tools").show_panel


def _compose(catalog, *packages):
    """Add tools to one catalog under one server identity, as MCPApp does."""
    for package in packages:
        catalog.add_tool(_tool(package), "Combined", toolkit_version="1.0.0")


def test_two_toolkits_sharing_a_document_path_do_not_collide(build_package):
    build_package("arcade_alpha", version="2.0.0", tool_name="ShowPanelAlpha")
    build_package("arcade_beta", version="3.1.0", tool_name="ShowPanelBeta")

    catalog = ToolCatalog()
    _compose(catalog, "arcade_alpha", "arcade_beta")

    assert len(catalog) == 2
    assert [registered.resource.uri for registered in catalog.resources] == [
        "ui://Alpha/2.0.0/panel.html",
        "ui://Beta/3.1.0/panel.html",
    ]


def test_each_pointer_names_the_uri_its_document_registered_under(build_package):
    """The pointer and the registration are two derivations that must not drift."""
    build_package("arcade_alpha", version="2.0.0", tool_name="ShowPanelAlpha")
    build_package("arcade_beta", version="3.1.0", tool_name="ShowPanelBeta")

    catalog = ToolCatalog()
    _compose(catalog, "arcade_alpha", "arcade_beta")

    for materialized in catalog:
        pointed = _pointed(materialized.definition)
        assert pointed in catalog.resources
        assert catalog.resources.get(pointed).resource.uri == pointed


def test_the_document_carries_the_shipping_toolkit_not_the_server(build_package):
    build_package("arcade_alpha", version="2.0.0")

    catalog = ToolCatalog()
    _compose(catalog, "arcade_alpha")

    definition = next(iter(catalog)).definition
    assert definition.toolkit.name == "Combined"
    assert _pointed(definition) == "ui://Alpha/2.0.0/panel.html"


def test_two_declarations_at_one_path_in_one_package_still_collide(build_package):
    root = build_package("arcade_alpha", version="2.0.0", ui_source=TWO_AT_ONE_PATH)
    (root / "arcade_alpha" / "tools.py").unlink()
    toolkit = Toolkit.from_directory(root)
    (root / "arcade_alpha" / "tools.py").write_text(
        textwrap.dedent(TOOLS_MODULE).format(package="arcade_alpha", tool_name="ShowPanel"),
        encoding="utf-8",
    )

    with pytest.raises(ToolkitLoadError) as raised:
        ToolCatalog().add_toolkit(toolkit)

    message = str(raised.value)
    assert "arcade_alpha.ui.first" in message
    assert "arcade_alpha.ui.second" in message


def test_a_package_that_is_not_installed_falls_back_to_the_server(build_package):
    build_package("loose_alpha")

    catalog = ToolCatalog()
    _compose(catalog, "loose_alpha")

    definition = next(iter(catalog)).definition
    assert _pointed(definition) == "ui://Combined/1.0.0/panel.html"


def test_the_toolkit_path_is_unchanged(build_package):
    """An installed toolkit ships its own documents, so its URIs do not move."""
    root = build_package("arcade_alpha", version="2.0.0")
    toolkit = Toolkit.from_directory(root)

    catalog = ToolCatalog()
    catalog.add_toolkit(toolkit)

    definition = next(iter(catalog)).definition
    assert definition.toolkit.name == "Alpha"
    assert _pointed(definition) == "ui://Alpha/2.0.0/panel.html"
    assert "ui://Alpha/2.0.0/panel.html" in catalog.resources
