"""The resource registry holds what a worker can serve for resources/*."""

import base64

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.resource_schema import BlobResourceContents, Resource, TextResourceContents
from arcade_core.resources import (
    InvalidCursorError,
    ResourceNotFoundError,
    ResourceRegistry,
    decode_cursor,
    encode_cursor,
)


def _resource(uri: str, mime: str | None = "text/html;profile=example") -> Resource:
    return Resource(uri=uri, name=uri.rsplit("/", 1)[-1], mimeType=mime)


def test_a_registered_resource_reads_back_as_text():
    registry = ResourceRegistry()
    registry.add(_resource("ui://Gmail/8.1.0/draft.html"), "<!DOCTYPE html>")

    found = registry.get("ui://Gmail/8.1.0/draft.html")

    assert isinstance(found.contents, TextResourceContents)
    assert found.contents.text == "<!DOCTYPE html>"
    assert found.contents.mimeType == "text/html;profile=example"
    assert found.contents.uri == "ui://Gmail/8.1.0/draft.html"


def test_bytes_are_registered_as_a_base64_blob():
    registry = ResourceRegistry()
    registry.add(_resource("res://Toolkit/1.0.0/logo.png", "image/png"), b"\x00\x01\x02")

    found = registry.get("res://Toolkit/1.0.0/logo.png")

    assert isinstance(found.contents, BlobResourceContents)
    assert found.contents.blob == base64.b64encode(b"\x00\x01\x02").decode()


def test_empty_text_and_empty_bytes_do_not_collapse_into_each_other():
    registry = ResourceRegistry()
    registry.add(_resource("res://a/1.0.0/t"), "")
    registry.add(_resource("res://a/1.0.0/b"), b"")

    assert isinstance(registry.get("res://a/1.0.0/t").contents, TextResourceContents)
    assert isinstance(registry.get("res://a/1.0.0/b").contents, BlobResourceContents)


def test_reading_an_unregistered_uri_is_a_typed_error():
    registry = ResourceRegistry()

    with pytest.raises(ResourceNotFoundError):
        registry.get("ui://Nope/1.0.0/missing.html")


def test_listing_is_ordered_by_uri_rather_than_by_insertion():
    """A worker can run as several processes, so a cursor has to mean the same thing in each."""
    registry = ResourceRegistry()
    for uri in ("ui://B/1.0.0/b.html", "ui://A/1.0.0/a.html", "ui://C/1.0.0/c.html"):
        registry.add(_resource(uri), "x")

    page, next_cursor = registry.list()

    assert [r.uri for r in page] == [
        "ui://A/1.0.0/a.html",
        "ui://B/1.0.0/b.html",
        "ui://C/1.0.0/c.html",
    ]
    assert next_cursor is None


def test_a_cursor_walks_every_resource_exactly_once():
    registry = ResourceRegistry(page_size=2)
    for i in range(5):
        registry.add(_resource(f"ui://A/1.0.0/{i}.html"), "x")

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        page, cursor = registry.list(cursor)
        seen.extend(r.uri for r in page)
        pages += 1
        if cursor is None:
            break

    assert pages == 3
    assert len(seen) == len(set(seen)) == 5


def test_the_last_page_reports_no_next_cursor():
    registry = ResourceRegistry(page_size=2)
    for i in range(4):
        registry.add(_resource(f"ui://A/1.0.0/{i}.html"), "x")

    _, cursor = registry.list()
    _, cursor = registry.list(cursor)

    assert cursor is None


def test_cursors_round_trip_and_stay_opaque():
    uri = "ui://Gmail/8.1.0/draft-review.html"

    assert decode_cursor(encode_cursor(uri)) == uri
    assert uri not in encode_cursor(uri)


def test_a_replica_resumes_a_page_it_did_not_issue():
    """The rolling deploy this cursor exists for: two replicas, different catalogs.

    A version lives in the URI, so mid-rollout the replica serving page two holds
    a different set than the one that served page one. An index into either list
    is a different position in the other.
    """
    old_replica = ResourceRegistry(page_size=2)
    new_replica = ResourceRegistry(page_size=2)
    shared = ["ui://A/1.0.0/a.html", "ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html"]
    for uri in shared:
        old_replica.add(_resource(uri), "x")
        new_replica.add(_resource(uri), "x")
    # The rollout is halfway: this replica already carries the new Math build,
    # and it sorts ahead of everything the other one holds.
    new_replica.add(_resource("ui://AA/2.0.0/new.html"), "x")

    first, cursor = old_replica.list()
    assert [r.uri for r in first] == ["ui://A/1.0.0/a.html", "ui://B/1.0.0/b.html"]

    second, _ = new_replica.list(cursor)

    # An offset of 2 into the new replica would have started at "ui://B", serving
    # it twice and never reaching "ui://C".
    assert [r.uri for r in second] == ["ui://C/1.0.0/c.html"]


def test_a_cursor_naming_a_uri_this_replica_lacks_still_resumes_after_it():
    """A resume point, not a lookup: the anchor does not have to be present."""
    registry = ResourceRegistry(page_size=10)
    for uri in ("ui://A/1.0.0/a.html", "ui://C/1.0.0/c.html"):
        registry.add(_resource(uri), "x")

    page, _ = registry.list(encode_cursor("ui://B/1.0.0/gone.html"))

    assert [r.uri for r in page] == ["ui://C/1.0.0/c.html"]


def test_a_resource_added_before_the_cursor_does_not_shift_the_next_page():
    """With an offset, inserting ahead of the cursor repeats an entry already served."""
    registry = ResourceRegistry(page_size=2)
    for uri in ("ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html", "ui://D/1.0.0/d.html"):
        registry.add(_resource(uri), "x")

    first, cursor = registry.list()
    assert [r.uri for r in first] == ["ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html"]

    registry.add(_resource("ui://A/1.0.0/a.html"), "x")
    second, _ = registry.list(cursor)

    assert [r.uri for r in second] == ["ui://D/1.0.0/d.html"]


@pytest.mark.parametrize(
    "bad",
    [
        "not-base64!!",
        "",
        "cGxhaW4",  # plain, no prefix
        "b2Zmc2V0OjA",  # offset:0, the encoding this replaced
        "YWZ0ZXI6",  # after:, naming nothing
    ],
)
def test_a_cursor_we_did_not_issue_is_rejected(bad):
    registry = ResourceRegistry()

    with pytest.raises(InvalidCursorError):
        decode_cursor(bad)
    if bad:
        with pytest.raises(InvalidCursorError):
            registry.list(bad)


def test_re_registering_a_uri_replaces_it():
    registry = ResourceRegistry()
    registry.add(_resource("ui://A/1.0.0/a.html"), "first")
    registry.add(_resource("ui://A/1.0.0/a.html"), "second")

    page, cursor = registry.list()

    assert len(registry) == 1
    assert registry.get("ui://A/1.0.0/a.html").contents.text == "second"
    # The ordered URI index is a separate structure from the dict, so a replace
    # that inserted a second time would leave a duplicate only listing reveals.
    assert len(page) == 1
    assert cursor is None


def test_each_catalog_owns_its_own_registry():
    first, second = ToolCatalog(), ToolCatalog()
    first.resources.add(_resource("ui://A/1.0.0/a.html"), "x")

    assert len(first.resources) == 1
    assert len(second.resources) == 0


@pytest.mark.parametrize("bad", [0, -1])
def test_a_nonpositive_page_size_is_refused(bad):
    """Zero pages forever on one cursor; a negative one emits a cursor we reject."""
    with pytest.raises(ValueError):
        ResourceRegistry(page_size=bad)

    registry = ResourceRegistry()
    with pytest.raises(ValueError):
        registry.page_size = bad


def test_membership_is_by_uri():
    registry = ResourceRegistry()
    registry.add(_resource("ui://Gmail/8.1.0/draft.html"), "<!DOCTYPE html>")

    assert "ui://Gmail/8.1.0/draft.html" in registry
    assert "ui://Gmail/8.1.0/missing.html" not in registry
    assert 42 not in registry


def test_contents_that_are_neither_text_nor_bytes_are_refused():
    registry = ResourceRegistry()

    with pytest.raises(TypeError) as caught:
        registry.add(_resource("ui://Gmail/8.1.0/draft.html"), {"not": "bytes"})

    assert "must be str or bytes" in str(caught.value)
    assert "dict" in str(caught.value)
    assert "ui://Gmail/8.1.0/draft.html" not in registry


def test_a_coroutine_is_refused_with_the_reason_it_cannot_work():
    """An async resource function reaches here already called, so the value is a coroutine."""

    async def build_it() -> str:
        return "<!DOCTYPE html>"

    coro = build_it()
    registry = ResourceRegistry()

    try:
        with pytest.raises(TypeError) as caught:
            registry.add(_resource("ui://Gmail/8.1.0/draft.html"), coro)
    finally:
        coro.close()

    assert "cannot return a coroutine" in str(caught.value)
