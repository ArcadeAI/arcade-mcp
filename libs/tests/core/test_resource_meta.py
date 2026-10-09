"""A resource's own ``_meta`` reaches both slots a client can read it from.

A host renders a document by reading the rendering contract off the read
response's contents, so the read is the slot that decides whether an interface
works. The listing carries it too, from the same authored value, so the two
cannot disagree about what a document asked for.
"""

import logging
from copy import deepcopy

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


@pytest.mark.parametrize(
    "directive, field",
    [("connect-src", "connectDomains"), ("script-src", "resourceDomains")],
)
def test_browser_csp_directives_warn_without_changing_the_resource(caplog, directive, field):
    meta = {"ui": {"csp": {directive: ["https://example.com"]}}}
    original_meta = deepcopy(meta)

    @resource(path="panel.html", meta=meta)
    def panel() -> str:
        return "<p>panel</p>"

    with caplog.at_level(logging.WARNING, logger="arcade_core.resources"):
        _, registered = _registry_with(panel)

    assert "ui://Kit/1.0.0/panel.html" in caplog.text
    assert directive in caplog.text
    assert f"_meta.ui.csp.{field}" in caplog.text
    assert meta == original_meta
    assert registered.resource.meta == original_meta
    assert registered.contents.meta == original_meta
    assert registered.contents.text == "<p>panel</p>"


@pytest.mark.parametrize(
    "meta",
    [
        None,
        UI_META,
        {"ui": {"csp": {"futureField": ["https://example.com"]}}},
        {"custom": {"connect-src": ["https://example.com"]}},
        {"ui": {"csp": "custom extension data"}},
        {"ui": "custom extension data"},
    ],
)
def test_other_resource_metadata_is_preserved_without_csp_warnings(caplog, meta):
    @resource(path="panel.html", meta=meta)
    def panel() -> str:
        return "<p>panel</p>"

    with caplog.at_level(logging.WARNING, logger="arcade_core.resources"):
        _, registered = _registry_with(panel)

    assert caplog.records == []
    assert registered.resource.meta == meta
    assert registered.contents.meta == meta


def test_registering_the_same_declaration_again_does_not_repeat_csp_warnings(caplog):
    @resource(path="panel.html", meta={"ui": {"csp": {"connect-src": []}}})
    def panel() -> str:
        return "<p>panel</p>"

    with caplog.at_level(logging.WARNING, logger="arcade_core.resources"):
        registry, registered = _registry_with(panel)
        registry.declare(panel, toolkit_name="Kit", toolkit_version="1.0.0")
        registry.list()
        registry.get(registered.resource.uri)

    assert len(caplog.records) == 1


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


def test_a_listing_meta_handed_to_add_does_not_leak_onto_the_contents():
    """The two are different slots, so nothing is copied between them.

    ``declare`` is the only thing that fills both, and it does so from one
    declared value rather than by copying one slot into the other.
    """
    registry = ResourceRegistry()

    registered = registry.add(
        Resource(uri="ui://Kit/1.0.0/a.html", name="a", mimeType="text/html", _meta=UI_META),
        "<p>a</p>",
    )

    assert registered.resource.meta == UI_META
    assert registered.contents.meta is None


def test_a_declaration_stays_hashable_when_it_carries_meta():
    """The class is frozen, so a compared dict field would make it unhashable."""

    @resource(path="panel.html", meta=UI_META)
    def panel() -> str:
        return "x"

    assert hash(panel) == hash(panel)
    assert panel in {panel}


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
