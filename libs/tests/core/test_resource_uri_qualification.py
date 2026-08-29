"""A resource URI carries the toolkit and its version.

The toolkit segment separates two toolkits packed into one worker image. The
version segment separates the same toolkit installed at two versions across two
workers, which is what keeps a tool and its interface in agreement.
"""

from urllib.parse import urlparse

import pytest
from arcade_core.resources import (
    InvalidResourcePathError,
    ResourceDeclaration,
    ResourceRegistry,
    qualify,
)


def test_a_declared_path_becomes_a_toolkit_qualified_uri():
    assert qualify("Gmail", "8.1.0", "draft-review.html") == "ui://Gmail/8.1.0/draft-review.html"


def test_the_scheme_is_carried_through_and_never_replaced():
    """A host that renders an interface requires ui:// and throws on anything else."""
    assert qualify("Gmail", "8.1.0", "a.html").startswith("ui://")
    assert qualify("Docs", "1.0.0", "llms.txt", scheme="docs") == "docs://Docs/1.0.0/llms.txt"
    assert "arcade://" not in qualify("Gmail", "8.1.0", "a.html")


def test_the_same_toolkit_at_two_versions_produces_two_uris():
    """A version 8 tool must not resolve to a version 7 interface."""
    assert qualify("Gmail", "8.1.0", "draft.html") != qualify("Gmail", "7.6.2", "draft.html")


def test_two_toolkits_cannot_collide_on_one_path():
    assert qualify("Gmail", "1.0.0", "index.html") != qualify("Slack", "1.0.0", "index.html")


@pytest.mark.parametrize(
    "path",
    ["draft.html", "/draft.html", "//draft.html", "ui/draft.html", "/ui//draft.html"],
)
def test_leading_and_repeated_slashes_normalize(path):
    uri = qualify("Gmail", "8.1.0", path)

    assert "//" not in uri[len("ui://") :]
    assert uri.startswith("ui://Gmail/8.1.0/")


def test_the_toolkit_segment_keeps_its_case():
    """Nothing on this path normalizes, and the reference host compares URIs exactly."""
    assert qualify("Gmail", "8.1.0", "a.html") == "ui://Gmail/8.1.0/a.html"


def test_a_qualified_uri_parses_as_a_uri():
    parsed = urlparse(qualify("Gmail", "8.1.0", "ui/draft-review.html"))

    assert parsed.scheme == "ui"
    assert parsed.netloc == "Gmail"
    assert parsed.path == "/8.1.0/ui/draft-review.html"


@pytest.mark.parametrize(
    ("toolkit", "version", "path"),
    [
        ("", "1.0.0", "a.html"),
        ("Gmail", "", "a.html"),
        ("Gmail", "1.0.0", ""),
        ("Gmail", "1.0.0", "///"),
    ],
)
def test_a_declaration_missing_an_identity_segment_is_rejected(toolkit, version, path):
    with pytest.raises(InvalidResourcePathError):
        qualify(toolkit, version, path)


@pytest.mark.parametrize("scheme", ["", ":", "//", "://"])
def test_a_declaration_with_no_scheme_left_is_rejected(scheme):
    """The separator is stripped before the check, so "://" is as empty as ""."""
    with pytest.raises(InvalidResourcePathError):
        qualify("Gmail", "8.1.0", "a.html", scheme=scheme)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("report?v=2.html", id="? opens a query"),
        pytest.param("report#top.html", id="# opens a fragment"),
        pytest.param("a\nb.html", id="a newline"),
        pytest.param("a\tb.html", id="a tab"),
        pytest.param("a\x00b.html", id="a NUL"),
    ],
)
def test_a_path_that_breaks_the_uri_is_rejected(path):
    """These fail at the point of reading, a long way from the declaration."""
    with pytest.raises(InvalidResourcePathError):
        qualify("Gmail", "8.1.0", path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("café.html", id="non-ascii"),
        pytest.param("a%20b.html", id="already percent-encoded"),
        pytest.param("a-b_c.d.html", id="punctuation a filename actually uses"),
        pytest.param("v2/report.html", id="a subdirectory"),
    ],
)
def test_a_path_a_toolkit_would_really_write_is_accepted(path):
    """The check above must not become a reason to reject ordinary filenames."""
    assert qualify("Gmail", "8.1.0", path).endswith(path)


@pytest.mark.parametrize("path", ["../secrets", "ui/../../etc/passwd", "./a.html"])
def test_a_traversing_path_is_rejected(path):
    with pytest.raises(InvalidResourcePathError):
        qualify("Gmail", "8.1.0", path)


def test_declaring_through_the_registry_qualifies_the_uri():
    registry = ResourceRegistry()
    declaration = ResourceDeclaration(
        path="draft-review.html",
        name="Draft review",
        mime_type="text/html;profile=example",
    )

    registered = registry.declare(
        declaration, "<!DOCTYPE html>", toolkit_name="Gmail", toolkit_version="8.1.0"
    )

    assert registered.resource.uri == "ui://Gmail/8.1.0/draft-review.html"
    assert registry.get("ui://Gmail/8.1.0/draft-review.html").contents.text == "<!DOCTYPE html>"


def test_the_contents_uri_matches_the_qualified_listing_uri():
    """A read that echoes a different URI than the listing breaks host-side caching."""
    registry = ResourceRegistry()
    registered = registry.declare(
        ResourceDeclaration(path="a.html", name="a"),
        "x",
        toolkit_name="Gmail",
        toolkit_version="8.1.0",
    )

    assert registered.contents.uri == registered.resource.uri
