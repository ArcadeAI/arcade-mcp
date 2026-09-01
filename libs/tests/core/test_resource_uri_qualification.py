"""A resource URI carries the toolkit and its version.

The toolkit segment separates two toolkits packed into one worker image. The
version segment separates the same toolkit installed at two versions across two
workers, which is what keeps a tool and its interface in agreement.
"""

from urllib.parse import unquote, urlparse, urlunparse

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
        pytest.param("a\nb.html", id="a newline"),
        pytest.param("a\tb.html", id="a tab"),
        pytest.param("a\x00b.html", id="a NUL"),
    ],
)
def test_a_path_carrying_a_control_character_is_rejected(path):
    """Encodable, but never meant. A control character in a filename is corruption."""
    with pytest.raises(InvalidResourcePathError):
        qualify("Gmail", "8.1.0", path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("café.html", id="non-ascii"),
        pytest.param("a b.html", id="a space"),
        pytest.param("50%.html", id="a percent"),
        pytest.param("report?v=2.html", id="a question mark"),
        pytest.param("report#top.html", id="a hash"),
        pytest.param("a%20b.html", id="something already percent-encoded"),
        pytest.param("a-b_c.d.html", id="punctuation a filename actually uses"),
        pytest.param("v2/report.html", id="a subdirectory"),
    ],
)
def test_a_path_survives_the_trip_as_the_author_wrote_it(path):
    """The URI a parser hands back has to decode to the path that was declared.

    Asserting the raw path is still a substring would pass on a URI no parser
    accepts, which is how ``50%.html`` and ``a b.html`` got through before.
    """
    uri = qualify("Gmail", "8.1.0", path)
    parsed = urlparse(uri)

    assert uri == urlunparse(parsed), "a URI a parser rewrites is not the one we registered"
    assert unquote(parsed.path) == f"/8.1.0/{path}"


@pytest.mark.parametrize(
    ("toolkit", "version", "scheme"),
    [
        pytest.param("Gmail", "8.1.0", "ui://Slack/9.0.0", id="a scheme carrying an authority"),
        pytest.param("Gmail", "8.1.0", "1ui", id="a scheme not starting with a letter"),
        pytest.param("Gmail", "8.1.0", "ht tp", id="a scheme with a space"),
        pytest.param("My Toolkit", "8.1.0", "ui", id="a toolkit name with a space"),
        pytest.param("Gmail?v2", "8.1.0", "ui", id="a toolkit name opening a query"),
        pytest.param("Gmail", "8.1.0/x", "ui", id="a version eating a path segment"),
    ],
)
def test_the_uris_identity_is_refused_rather_than_encoded(toolkit, version, scheme):
    """Encoding these would answer under a name nobody asked for.

    ``ui://Slack/9.0.0`` as a scheme parses with host ``Slack``, so a Gmail
    declaration serves under another toolkit's authority. A "/" in the version
    makes it eat a path segment, so ``("8.1.0/x", "a.html")`` and
    ``("8.1.0", "x/a.html")`` collide on one URI.
    """
    with pytest.raises(InvalidResourcePathError):
        qualify(toolkit, version, "a.html", scheme=scheme)


@pytest.mark.parametrize(
    "version",
    [
        pytest.param("1.0.0", id="release"),
        pytest.param("1.0.0a1", id="PEP 440 alpha"),
        pytest.param("1.0.0.post1", id="PEP 440 post"),
        pytest.param("1.0.0.dev0", id="PEP 440 dev"),
        pytest.param("1.0.0+build.5", id="semver build metadata"),
        pytest.param("1.0.0+local_abc", id="PEP 440 local version"),
        pytest.param("1.0.0-rc.1", id="semver prerelease"),
        pytest.param("1!1.0.0", id="PEP 440 epoch"),
    ],
)
def test_a_version_a_real_toolkit_ships_is_accepted(version):
    """`ToolkitDefinition` takes all of these, so refusing one here would load a
    toolkit's tools and drop its resources."""
    assert qualify("Gmail", version, "a.html") == f"ui://Gmail/{version}/a.html"


def test_a_version_cannot_eat_a_path_segment():
    """The collision the check above prevents, stated as the equality it used to satisfy."""
    with pytest.raises(InvalidResourcePathError):
        qualify("Gmail", "8.1.0/x", "a.html")

    assert qualify("Gmail", "8.1.0", "x/a.html") == "ui://Gmail/8.1.0/x/a.html"


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
