"""A resource's own ``_meta`` reaches both slots a client can read it from.

A host renders a document by reading the rendering contract off the read
response's contents, so the read is the slot that decides whether an interface
works. The listing carries it too, from the same authored value, so the two
cannot disagree about what a document asked for.
"""

import pytest
from arcade_core.resource_schema import BlobResourceContents, Resource, TextResourceContents
from arcade_core.resources import ResourceDeclaration, ResourceRegistry, resource

UI_META = {
    "ui": {
        "csp": {"connectDomains": ["https://api.example.com"]},
        "permissions": {"clipboardWrite": {}},
        "prefersBorder": False,
    }
}


def _registry_with(declaration):
    registry = ResourceRegistry()
    return registry, registry.declare(declaration, toolkit_name="Kit", toolkit_version="1.0.0")


def test_a_declared_meta_reaches_the_listing_and_the_read():
    @resource(path="panel.html", meta=UI_META)
    def panel() -> str:
        return "<!DOCTYPE html><p>panel</p>"

    _, registered = _registry_with(panel)

    assert registered.resource.meta == UI_META
    assert registered.contents.meta == UI_META


def test_a_blob_carries_it_too():
    @resource(path="icon.png", mime_type="image/png", meta=UI_META)
    def icon() -> bytes:
        return b"\x89PNG\r\n"

    _, registered = _registry_with(icon)

    assert isinstance(registered.contents, BlobResourceContents)
    assert registered.contents.meta == UI_META


def test_no_declared_meta_leaves_both_slots_absent():
    """Absent rather than an empty object, so the wire stays clean under exclude_none."""

    @resource(path="panel.html")
    def panel() -> str:
        return "<!DOCTYPE html><p>panel</p>"

    _, registered = _registry_with(panel)

    assert registered.resource.meta is None
    assert registered.contents.meta is None
    assert "_meta" not in registered.contents.model_dump(by_alias=True, exclude_none=True)
    assert "_meta" not in registered.resource.model_dump(by_alias=True, exclude_none=True)


def test_the_object_is_carried_verbatim():
    """The extension ships on its own schedule, so an unknown key must survive."""
    later = {"ui": {"somethingAddedLater": {"nested": [1, 2]}}}

    @resource(path="panel.html", meta=later)
    def panel() -> str:
        return "x"

    _, registered = _registry_with(panel)

    assert registered.contents.meta == later
    assert registered.resource.meta == later


def test_add_fills_exactly_the_slot_it_is_given():
    """The low-level path fills one slot at a time; fanning out belongs to declare."""
    registry = ResourceRegistry()

    listing_only = registry.add(
        Resource(uri="ui://Kit/1.0.0/a.html", name="a", mimeType="text/html", _meta=UI_META),
        "<p>a</p>",
    )
    assert listing_only.resource.meta == UI_META
    assert listing_only.contents.meta is None, "a listing _meta must not leak onto the contents"

    contents_only = registry.add(
        Resource(uri="ui://Kit/1.0.0/b.html", name="b", mimeType="text/html"),
        "<p>b</p>",
        contents_meta=UI_META,
    )
    assert contents_only.contents.meta == UI_META
    assert contents_only.resource.meta is None, "a contents _meta must not leak onto the listing"


@pytest.mark.parametrize("body", ["<p>text</p>", b"\x00\x01"])
def test_a_hand_built_declaration_carries_it(body):
    """The dataclass is public, so the field has to work without the decorator."""
    registry = ResourceRegistry()
    mime = "text/html" if isinstance(body, str) else "application/octet-stream"

    registered = registry.declare(
        ResourceDeclaration(
            path="hand.bin", name="hand", mime_type=mime, meta=UI_META, func=lambda: body
        ),
        toolkit_name="Kit",
        toolkit_version="1.0.0",
    )

    assert registered.contents.meta == UI_META


def test_a_text_document_keeps_its_body_alongside_the_meta():
    @resource(path="panel.html", meta=UI_META)
    def panel() -> str:
        return "<!DOCTYPE html><p>panel</p>"

    _, registered = _registry_with(panel)

    assert isinstance(registered.contents, TextResourceContents)
    assert registered.contents.text == "<!DOCTYPE html><p>panel</p>"
