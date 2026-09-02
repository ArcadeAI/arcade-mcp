"""Contract tests for the two resource endpoints on the worker protocol.

One rule governs both: the request body is the params object for the endpoint
and the response is its result object, both spelled as they go on the wire.

These assert the wire bytes rather than the Python objects, because a caller
decodes the bytes and a host that renders an interface compares some of them
with string equality.
"""

from typing import Annotated

import pytest
from arcade_core.resource_schema import Resource
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import ToolContext, tool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.trace import StatusCode

UI_MIME = "text/html;profile=example"
DRAFT_URI = "ui://Gmail/8.1.0/draft-review.html"
DRAFT_BODY = "<!DOCTYPE html><html><body>draft</body></html>"


@tool()
def sample_tool(context: ToolContext, x: Annotated[int, "x"]) -> Annotated[str, "output"]:
    """A sample tool."""
    return str(x)


def _worker(app: FastAPI, *, with_resources: bool) -> FastAPIWorker:
    worker = FastAPIWorker(app=app, disable_auth=True)
    worker.register_tool(sample_tool, toolkit_name="fixture_kit")
    if with_resources:
        worker.catalog.resources.add(
            Resource(uri=DRAFT_URI, name="Draft review", mimeType=UI_MIME), DRAFT_BODY
        )
    return worker


@pytest.fixture
def serving():
    app = FastAPI()
    _worker(app, with_resources=True)
    return TestClient(app)


@pytest.fixture
def empty():
    """A worker on this release that simply has no resources to serve."""
    app = FastAPI()
    _worker(app, with_resources=False)
    return TestClient(app)


@pytest.fixture
def secured():
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret="test-secret")  # noqa: S106
    worker.register_tool(sample_tool, toolkit_name="fixture_kit")
    return TestClient(app)


# --- the wire shape ---


def test_list_returns_a_result_object(serving):
    response = serving.post("/worker/resources/list", json={})

    assert response.status_code == 200
    assert response.json() == {
        "resources": [
            {"uri": DRAFT_URI, "name": "Draft review", "mimeType": UI_MIME},
        ]
    }


def test_read_returns_a_result_object(serving):
    response = serving.post("/worker/resources/read", json={"uri": DRAFT_URI})

    assert response.status_code == 200
    assert response.json() == {
        "contents": [{"uri": DRAFT_URI, "mimeType": UI_MIME, "text": DRAFT_BODY}]
    }


def test_absent_optional_fields_are_omitted_rather_than_null(serving):
    """The format omits them rather than sending null, so the wire stays clean."""
    listed = serving.post("/worker/resources/list", json={}).json()

    assert "nextCursor" not in listed
    assert "_meta" not in listed
    entry = listed["resources"][0]
    for absent in ("description", "annotations", "size", "icons", "title", "_meta"):
        assert absent not in entry, f"{absent} should be omitted, not null"


def test_the_ui_mime_type_survives_byte_for_byte(serving):
    """A host that renders an interface compares this with string equality.

    Asserted against the raw response body rather than the parsed JSON, because
    a space after the semicolon, a lowercased parameter, or an appended charset
    all survive parsing and all stop the host rendering.
    """
    body = serving.post("/worker/resources/read", json={"uri": DRAFT_URI}).text

    assert f'"mimeType":"{UI_MIME}"' in body
    assert "profile=example" in body
    assert "; profile" not in body
    assert "charset" not in body


def test_a_first_page_list_may_send_an_empty_body(serving):
    """The router coerces an absent body to {}."""
    response = serving.post("/worker/resources/list", content=b"")

    assert response.status_code == 200
    assert len(response.json()["resources"]) == 1


@pytest.mark.parametrize("body", [b"[]", b"false", b"0", b'""'])
def test_a_falsy_non_object_body_is_rejected(serving, body):
    """An explicit non-object body is malformed and must not read as empty params."""
    response = serving.post(
        "/worker/resources/list",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


# --- a worker with nothing to serve ---


def test_a_worker_with_no_resources_lists_an_empty_array(empty):
    response = empty.post("/worker/resources/list", json={})

    assert response.status_code == 200
    assert response.json() == {"resources": []}


def test_a_worker_with_no_resources_still_serves_its_tools(empty):
    response = empty.get("/worker/tools")

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- errors ---


def test_reading_an_unknown_uri_is_a_not_found_with_an_error_body(serving):
    response = serving.post("/worker/resources/read", json={"uri": "ui://Gmail/8.1.0/nope.html"})

    assert response.status_code == 404
    assert response.json()["code"] == -32002
    assert "nope.html" in response.json()["message"]


def test_a_read_without_a_uri_is_rejected_as_invalid_params(serving):
    response = serving.post("/worker/resources/read", json={})

    assert response.status_code == 400
    assert response.json()["code"] == -32602


def test_a_cursor_we_did_not_issue_is_rejected(serving):
    response = serving.post("/worker/resources/list", json={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.json()["code"] == -32602


# --- routing and auth ---


def test_both_endpoints_are_registered_and_are_post_only(serving):
    assert serving.post("/worker/resources/list", json={}).status_code == 200
    assert serving.post("/worker/resources/read", json={"uri": DRAFT_URI}).status_code == 200
    assert serving.get("/worker/resources/list").status_code == 405
    assert serving.get("/worker/resources/read").status_code == 405


def test_both_endpoints_require_the_worker_secret(secured):
    for path in ("/worker/resources/list", "/worker/resources/read"):
        anonymous = secured.post(path, json={"uri": DRAFT_URI})
        bad_token = secured.post(
            path, json={"uri": DRAFT_URI}, headers={"Authorization": "Bearer nope"}
        )

        assert anonymous.status_code in (401, 403), path
        assert bad_token.status_code in (401, 403), path


def test_both_endpoints_are_registered_under_the_worker_base_path(serving):
    """The suffix names the operation, so a caller builds the path from it."""
    routes = {r.path for r in serving.app.routes if hasattr(r, "path")}

    assert "/worker/resources/list" in routes
    assert "/worker/resources/read" in routes


# --- pagination ---


def test_a_cursor_walks_to_the_second_page():
    app = FastAPI()
    worker = _worker(app, with_resources=True)
    worker.catalog.resources.page_size = 1
    worker.catalog.resources.add(
        Resource(uri="ui://Gmail/8.1.0/other.html", name="Other", mimeType=UI_MIME), "x"
    )
    client = TestClient(app)

    first = client.post("/worker/resources/list", json={}).json()
    second = client.post("/worker/resources/list", json={"cursor": first["nextCursor"]}).json()

    assert len(first["resources"]) == 1
    assert len(second["resources"]) == 1
    assert first["resources"][0]["uri"] != second["resources"][0]["uri"]
    assert "nextCursor" not in second


# --- the worker's own faults stay the worker's own faults ---


def test_a_body_that_is_not_utf8_is_rejected_as_malformed(serving):
    """Undecodable bytes never reach json's own error, so the tuple must name them."""
    response = serving.post(
        "/worker/resources/read",
        content=b'{"uri": "\xff\xfe"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == -32602


def test_a_model_the_worker_fails_to_build_is_a_500_not_a_400():
    """The caller sent a valid read. Blaming it for the worker's own model is a lie."""
    app = FastAPI()
    worker = _worker(app, with_resources=True)

    def raise_from_inside(uri: str):
        Resource.model_validate({})

    worker.read_resource = raise_from_inside

    response = TestClient(app, raise_server_exceptions=False).post(
        "/worker/resources/read", json={"uri": DRAFT_URI}
    )

    assert response.status_code == 500


# --- spans ---


@pytest.fixture
def spans(monkeypatch):
    """Collect the spans the two components open, without touching the global provider."""
    from arcade_serve.core import components
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(
        components.trace, "get_tracer", lambda *a, **kw: provider.get_tracer(__name__)
    )
    return exporter


def _only_span(spans):
    finished = spans.get_finished_spans()
    assert len(finished) == 1
    return finished[0]


def test_an_unknown_uri_does_not_land_as_a_failed_span(serving, spans):
    """Rendering a stale interface is routine. It must not page anyone."""
    serving.post("/worker/resources/read", json={"uri": "ui://Gmail/8.1.0/nope.html"})

    span = _only_span(spans)
    assert span.status.status_code != StatusCode.ERROR
    assert span.events == ()
    assert span.attributes["outcome"] == "not_found"


def test_a_refused_cursor_does_not_land_as_a_failed_span(serving, spans):
    serving.post("/worker/resources/list", json={"cursor": "not-a-cursor"})

    span = _only_span(spans)
    assert span.status.status_code != StatusCode.ERROR
    assert span.attributes["outcome"] == "invalid_request"


def test_a_served_read_is_marked_a_success(serving, spans):
    serving.post("/worker/resources/read", json={"uri": DRAFT_URI})

    assert _only_span(spans).attributes["outcome"] == "success"


def test_an_unexpected_failure_still_lands_as_a_failed_span(spans):
    """Suppression covers the answers this endpoint gives, and nothing else."""
    app = FastAPI()
    worker = _worker(app, with_resources=True)

    def blow_up(uri: str):
        raise RuntimeError("disk gone")

    worker.read_resource = blow_up

    TestClient(app, raise_server_exceptions=False).post(
        "/worker/resources/read", json={"uri": DRAFT_URI}
    )

    span = _only_span(spans)
    assert span.status.status_code == StatusCode.ERROR
    assert [e.name for e in span.events] == ["exception"]
