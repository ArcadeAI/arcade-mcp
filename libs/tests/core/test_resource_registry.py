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
    digest = "a" * 64

    assert decode_cursor(encode_cursor(uri, digest)) == (uri, digest)
    assert uri not in encode_cursor(uri, digest)


def test_a_replica_resumes_a_page_it_did_not_issue():
    """Replicas with the same catalog can register it in different orders."""
    old_replica = ResourceRegistry(page_size=2)
    new_replica = ResourceRegistry(page_size=2)
    shared = ["ui://A/1.0.0/a.html", "ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html"]
    for uri in shared:
        old_replica.add(_resource(uri), "x")
    for uri in reversed(shared):
        new_replica.add(_resource(uri), "x")

    first, cursor = old_replica.list()
    assert [r.uri for r in first] == ["ui://A/1.0.0/a.html", "ui://B/1.0.0/b.html"]

    second, last_cursor = new_replica.list(cursor)

    assert [r.uri for r in second] == ["ui://C/1.0.0/c.html"]
    assert last_cursor is None


def test_a_cursor_naming_an_unregistered_uri_is_rejected():
    registry = ResourceRegistry(page_size=1)
    for uri in ("ui://A/1.0.0/a.html", "ui://C/1.0.0/c.html"):
        registry.add(_resource(uri), "x")

    _, cursor = registry.list()
    _, digest = decode_cursor(cursor)

    with pytest.raises(InvalidCursorError, match="registered resource"):
        registry.list(encode_cursor("ui://B/1.0.0/gone.html", digest))


def test_a_changed_catalog_requires_a_fresh_listing():
    registry = ResourceRegistry(page_size=2)
    for uri in ("ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html", "ui://D/1.0.0/d.html"):
        registry.add(_resource(uri), "x")

    first, cursor = registry.list()
    assert [r.uri for r in first] == ["ui://B/1.0.0/b.html", "ui://C/1.0.0/c.html"]

    registry.add(_resource("ui://A/1.0.0/a.html"), "x")
    with pytest.raises(InvalidCursorError, match="catalog changed"):
        registry.list(cursor)

    first, cursor = registry.list()
    second, cursor = registry.list(cursor)
    assert [r.uri for r in first + second] == [
        f"ui://{name}/1.0.0/{name.lower()}.html" for name in "ABCD"
    ]
    assert cursor is None


@pytest.mark.parametrize(
    "other_uris",
    [
        [],
        ["ui://Math/1.0.0/a.html", "ui://Math/1.0.0/b.html"],
        ["ui://Math/2.0.0/b.html"],
    ],
)
def test_a_different_replica_cannot_silently_finish_a_partial_catalog(other_uris):
    first_replica = ResourceRegistry(page_size=1)
    for uri in ["ui://Math/2.0.0/a.html", "ui://Math/2.0.0/b.html"]:
        first_replica.add(_resource(uri), "x")
    other_replica = ResourceRegistry(page_size=1)
    for uri in other_uris:
        other_replica.add(_resource(uri), "x")

    _, cursor = first_replica.list()

    with pytest.raises(InvalidCursorError, match="catalog changed"):
        other_replica.list(cursor)


@pytest.mark.parametrize("change", ["description", "nested metadata", "extra field"])
def test_changing_a_listing_descriptor_invalidates_the_cursor(change):
    registry = ResourceRegistry(page_size=1)
    for uri in ["ui://a", "ui://b"]:
        registry.add(Resource(uri=uri, name=uri, _meta={"ui": {"prefersBorder": False}}), "x")
    _, cursor = registry.list()

    descriptor = registry.get("ui://a").resource
    if change == "description":
        descriptor.description = "A changed description"
    elif change == "nested metadata":
        descriptor.meta["ui"]["prefersBorder"] = True
    else:
        descriptor.model_extra["example.com/extension"] = {"revision": 2}

    with pytest.raises(InvalidCursorError, match="catalog changed"):
        registry.list(cursor)


def test_metadata_key_order_and_page_size_do_not_change_catalog_identity():
    first_replica = ResourceRegistry(page_size=1)
    other_replica = ResourceRegistry(page_size=2)
    for uri in ["ui://a", "ui://b", "ui://c"]:
        first_replica.add(Resource(uri=uri, name=uri, _meta={"a": {"x": 1, "y": 2}, "b": 3}), "x")
    for uri in ["ui://c", "ui://b", "ui://a"]:
        other_replica.add(Resource(uri=uri, name=uri, _meta={"b": 3, "a": {"y": 2, "x": 1}}), "x")

    _, cursor = first_replica.list()
    second, cursor = other_replica.list(cursor)

    assert [resource.uri for resource in second] == ["ui://b", "ui://c"]
    assert cursor is None


def test_changing_only_resource_contents_does_not_invalidate_a_listing():
    registry = ResourceRegistry(page_size=1)
    for uri in ["ui://a", "ui://b"]:
        registry.add(_resource(uri), "original")
    _, cursor = registry.list()
    registry.add(_resource("ui://b"), "replacement")

    second, cursor = registry.list(cursor)

    assert [resource.uri for resource in second] == ["ui://b"]
    assert registry.get("ui://b").contents.text == "replacement"
    assert cursor is None


@pytest.mark.parametrize(
    "bad",
    [
        "not-base64!!",
        "",
        "cGxhaW4",  # plain, no prefix
        "b2Zmc2V0OjA",  # offset:0, the encoding this replaced
        "YWZ0ZXI6",  # after:, naming nothing
        base64.urlsafe_b64encode(b"after:ui://A/1.0.0/a.html").decode(),
        base64.urlsafe_b64encode(b"catalog:invalid:ui://a").decode(),
        base64.urlsafe_b64encode(b"catalog:" + b"a" * 64 + b":").decode(),
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
