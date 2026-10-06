"""The worker surface reads resources off the catalog it was handed.

worker.catalog is the only object the server factory passes to the worker, so
anything the worker serves has to arrive on it.
"""

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.resource_schema import Resource, TextResourceContents
from arcade_core.resources import ResourceDeclaration, ResourceNotFoundError
from arcade_serve.core.base import BaseWorker
from arcade_serve.core.common import Worker


class _MinimalWorker(Worker):
    """A Worker written before resources existed."""

    def get_catalog(self):
        return []

    async def call_tool(self, request):
        raise NotImplementedError

    def health_check(self):
        return {"status": "ok"}


@pytest.fixture
def worker():
    built = BaseWorker(secret="test_secret")  # noqa: S106
    built.catalog = ToolCatalog()
    return built


def _add(catalog, uri, text="<!DOCTYPE html>"):
    catalog.resources.add(
        Resource(uri=uri, name=uri.rsplit("/", 1)[-1], mimeType="text/html;profile=example"), text
    )


def test_a_worker_with_no_resources_lists_an_empty_page(worker):
    result = worker.list_resources()

    assert result.resources == []
    assert result.nextCursor is None


def test_the_worker_lists_what_the_catalog_carries(worker):
    _add(worker.catalog, "ui://Gmail/8.1.0/draft.html")

    result = worker.list_resources()

    assert [r.uri for r in result.resources] == ["ui://Gmail/8.1.0/draft.html"]


def test_the_worker_adds_toolkit_provenance_to_declared_resources(worker):
    worker.catalog.resources.declare(
        ResourceDeclaration(
            path="preferences",
            name="preferences",
            title="Account settings",
            meta={"author": {"color": "blue"}, "arcade.dev/toolkit": {"name": "forged"}},
            func=lambda: "settings",
        ),
        toolkit_name="MicrosoftOutlookCalendar",
        toolkit_version="1.0.0",
    )

    listed = worker.list_resources().resources[0]

    assert listed.name == "preferences"
    assert listed.title == "Account settings"
    assert listed.meta == {
        "author": {"color": "blue"},
        "arcade.dev/toolkit": {"name": "MicrosoftOutlookCalendar"},
    }
    assert worker.catalog.resources.get(listed.uri).resource.meta == {
        "author": {"color": "blue"},
        "arcade.dev/toolkit": {"name": "forged"},
    }
    assert worker.read_resource(listed.uri).contents[0].meta == {"author": {"color": "blue"}}


def test_the_worker_strips_reserved_provenance_from_generic_resources(worker):
    worker.catalog.resources.add(
        Resource(
            uri="https://example.com/docs",
            name="docs",
            _meta={"author": True, "arcade.dev/toolkit": {"name": "forged"}},
        ),
        "docs",
    )

    listed = worker.list_resources().resources[0]

    assert listed.meta == {"author": True}


def test_the_worker_does_not_expose_metadata_when_only_reserved_provenance_remains(worker):
    worker.catalog.resources.add(
        Resource(
            uri="https://example.com/docs",
            name="docs",
            _meta={"arcade.dev/toolkit": {"name": "forged"}},
        ),
        "docs",
    )

    assert worker.list_resources().resources[0].meta is None


def test_the_worker_does_not_expose_reserved_provenance_when_reading(worker):
    registered = worker.catalog.resources.declare(
        ResourceDeclaration(
            path="preferences",
            name="preferences",
            meta={"arcade.dev/toolkit": {"name": "forged"}},
            func=lambda: "settings",
        ),
        toolkit_name="Gmail",
        toolkit_version="1.0.0",
    )

    assert worker.read_resource(registered.resource.uri).contents[0].meta is None


def test_the_worker_preserves_an_explicitly_empty_metadata_object(worker):
    worker.catalog.resources.add(
        Resource(uri="https://example.com/docs", name="docs", _meta={}),
        "docs",
    )

    listed = worker.list_resources().resources[0]

    assert listed.meta == {}


def test_reading_returns_the_registered_contents(worker):
    _add(worker.catalog, "ui://Gmail/8.1.0/draft.html", "<p>draft</p>")

    result = worker.read_resource("ui://Gmail/8.1.0/draft.html")

    assert len(result.contents) == 1
    assert isinstance(result.contents[0], TextResourceContents)
    assert result.contents[0].text == "<p>draft</p>"
    assert result.contents[0].mimeType == "text/html;profile=example"


def test_reading_an_unknown_uri_raises_not_found(worker):
    with pytest.raises(ResourceNotFoundError):
        worker.read_resource("ui://Gmail/8.1.0/missing.html")


def test_a_cursor_from_list_walks_to_the_next_page(worker):
    worker.catalog.resources.page_size = 1
    _add(worker.catalog, "ui://A/1.0.0/a.html")
    _add(worker.catalog, "ui://B/1.0.0/b.html")

    first = worker.list_resources()
    second = worker.list_resources(first.nextCursor)

    assert first.nextCursor is not None
    assert [r.uri for r in first.resources] == ["ui://A/1.0.0/a.html"]
    assert [r.uri for r in second.resources] == ["ui://B/1.0.0/b.html"]
    assert second.nextCursor is None


def test_a_worker_predating_resources_still_constructs_and_serves_nothing():
    """The reads are concrete, not abstract, so an older Worker keeps working."""
    legacy = _MinimalWorker()

    assert legacy.list_resources().resources == []
    with pytest.raises(KeyError):
        legacy.read_resource("ui://x/1.0.0/a.html")
