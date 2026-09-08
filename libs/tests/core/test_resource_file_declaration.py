"""A resource can name a file beside its module instead of reading it by hand.

The file is resolved against the declaring module and read once at
registration, as text for a text media type and as bytes otherwise, and the
resource takes the file's name as its path unless one is given.
"""

import sys
import textwrap

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ToolkitLoadError
from arcade_core.resource_schema import BlobResourceContents, TextResourceContents
from arcade_core.resources import UI_DOCUMENT_MIME_TYPE, resource
from arcade_core.toolkit import Toolkit

TOOLS_MODULE = '''
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

UI_MODULE = """
from arcade_core.resources import UI_DOCUMENT_MIME_TYPE, resource


@resource(file="dashboard.html", mime_type=UI_DOCUMENT_MIME_TYPE)
def dashboard() -> None: ...


@resource(file="icon.png", mime_type="image/png")
def icon() -> None: ...


@resource(path="nested/dash.html", file="dashboard.html", mime_type="text/html")
def nested() -> None: ...
"""

MISSING_MODULE = """
from arcade_core.resources import resource


@resource(file="missing.html", mime_type="text/html")
def missing() -> None: ...
"""


def _forget(package_name):
    for name in [n for n in sys.modules if n == package_name or n.startswith(package_name + ".")]:
        del sys.modules[name]


@pytest.fixture
def build_toolkit(tmp_path, monkeypatch):
    built = []

    def build(name, ui_source, files):
        root = tmp_path / name
        package = root / name
        package.mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "tools.py").write_text(textwrap.dedent(TOOLS_MODULE), encoding="utf-8")
        (package / "ui.py").write_text(textwrap.dedent(ui_source), encoding="utf-8")
        for filename, body in files.items():
            mode = "wb" if isinstance(body, bytes) else "w"
            with open(package / filename, mode) as handle:
                handle.write(body)
        monkeypatch.syspath_prepend(str(root))
        _forget(name)
        built.append(name)
        return Toolkit.from_directory(root)

    yield build
    for name in built:
        _forget(name)


FILES = {"dashboard.html": "<!DOCTYPE html><p>hi</p>", "icon.png": b"\x89PNG\r\n"}


def test_a_text_file_is_served_as_text_under_its_own_name(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", UI_MODULE, FILES))

    registered = catalog.resources.get("ui://Widgets/1.0.0/dashboard.html")

    assert isinstance(registered.contents, TextResourceContents)
    assert registered.contents.text == "<!DOCTYPE html><p>hi</p>"
    assert registered.contents.mimeType == UI_DOCUMENT_MIME_TYPE


def test_a_binary_file_is_served_as_a_blob(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", UI_MODULE, FILES))

    registered = catalog.resources.get("ui://Widgets/1.0.0/icon.png")

    assert isinstance(registered.contents, BlobResourceContents)
    assert registered.contents.blob == "iVBORw0K"


def test_a_given_path_wins_over_the_file_name(build_toolkit):
    catalog = ToolCatalog()
    catalog.add_toolkit(build_toolkit("arcade_widgets", UI_MODULE, FILES))

    assert "ui://Widgets/1.0.0/nested/dash.html" in catalog.resources


def test_a_missing_file_fails_the_toolkit(build_toolkit):
    toolkit = build_toolkit("arcade_widgets", MISSING_MODULE, {})

    with pytest.raises(ToolkitLoadError, match="missing.html"):
        ToolCatalog().add_toolkit(toolkit)


def test_a_declaration_needs_a_path_or_a_file():
    with pytest.raises(TypeError, match="path or a file"):
        resource()
