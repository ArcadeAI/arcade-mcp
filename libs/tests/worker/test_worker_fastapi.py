from typing import Annotated

import pytest
from arcade_core.schema import ToolCallRequest, ToolContext, ToolReference
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import tool
from fastapi import FastAPI
from fastapi.testclient import TestClient


@tool()
def sample_tool_fastapi(
    context: ToolContext, x: Annotated[int, "x"], y: Annotated[str, "y"]
) -> Annotated[str, "output"]:
    """A sample tool for FastAPI tests."""
    return f"{y}-{x}"


# Define tool at module level to avoid indentation issues with getsource
@tool()
def error_throwing_tool(
    context: ToolContext,
    a: Annotated[int, "a", "Input integer a"],  # Added description for parameter
) -> int:
    """This tool throws a ValueError."""  # Added description for tool
    raise ValueError("Test execution error")


@pytest.fixture
def test_app():
    return FastAPI()


@pytest.fixture
def worker_secret():
    return "test-secret-fastapi"


@pytest.fixture
def fastapi_worker(test_app, worker_secret):
    worker = FastAPIWorker(app=test_app, secret=worker_secret)
    worker.register_tool(sample_tool_fastapi, toolkit_name="fastapi_kit")
    return worker


@pytest.fixture
def fastapi_worker_no_auth(test_app):
    worker = FastAPIWorker(app=test_app, disable_auth=True)
    worker.register_tool(sample_tool_fastapi, toolkit_name="fastapi_kit")
    return worker


@pytest.fixture
def client(test_app, fastapi_worker):  # Use the worker fixture to ensure routes are registered
    return TestClient(test_app)


@pytest.fixture
def client_no_auth(test_app, fastapi_worker_no_auth):
    return TestClient(test_app)


# --- FastAPIWorker Tests ---


def test_fastapi_worker_registers_routes(client, fastapi_worker):
    # Check if routes exist by trying to access them (even if auth fails)
    response = client.get(f"{fastapi_worker.base_path}/health")
    assert response.status_code != 404  # Should be 200

    response = client.get(f"{fastapi_worker.base_path}/tools")
    assert response.status_code != 404  # Should be 403 without auth

    # Prepare a dummy request body for invoke
    tool_ref = ToolReference(toolkit="FastapiKit", name="SampleToolFastapi")
    request_body = ToolCallRequest(
        execution_id="test", tool=tool_ref, inputs={"x": 1, "y": "test"}
    ).model_dump()

    response = client.post(f"{fastapi_worker.base_path}/tools/invoke", json=request_body)
    assert response.status_code != 404  # Should be 403 without auth


# --- Route Tests (using TestClient) ---


# Health Check
def test_health_check_route(client, worker_secret):
    response = client.get("/worker/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "tool_count": "1"}


def test_health_check_route_no_auth(client_no_auth):
    response = client_no_auth.get("/worker/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "tool_count": "1"}


# Catalog
def test_get_catalog_route_no_auth_header(client):
    response = client.get("/worker/tools")
    assert response.status_code == 403
    assert "Not authenticated" in response.text


def test_get_catalog_route_invalid_auth_header(client, worker_secret):
    response = client.get("/worker/tools", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401  # Unauthorized
    # Updated expected error message based on last run
    assert "Invalid token. Error: Not enough segments" in response.text


def test_get_catalog_route_no_auth_worker(client_no_auth):
    response = client_no_auth.get("/worker/tools")
    assert response.status_code == 200
    catalog = response.json()
    assert isinstance(catalog, list)
    assert len(catalog) == 1
    assert catalog[0]["name"] == "SampleToolFastapi"


# Call Tool
@pytest.fixture
def call_tool_payload():
    tool_ref = ToolReference(toolkit="FastapiKit", name="SampleToolFastapi")
    return ToolCallRequest(
        execution_id="fastapi-test-exec", tool=tool_ref, inputs={"x": 123, "y": "hello"}
    ).model_dump()


def test_call_tool_route_no_auth_header(client, call_tool_payload):
    response = client.post("/worker/tools/invoke", json=call_tool_payload)
    assert response.status_code == 403


def test_call_tool_route_invalid_auth_header(client, worker_secret, call_tool_payload):
    response = client.post(
        "/worker/tools/invoke",
        json=call_tool_payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_call_tool_route_no_auth_worker(client_no_auth, call_tool_payload):
    response = client_no_auth.post("/worker/tools/invoke", json=call_tool_payload)
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["output"]["value"] == "hello-123"


def test_call_tool_route_tool_not_found(client_no_auth, call_tool_payload):
    call_tool_payload["tool"]["name"] = "NonExistentTool"
    call_tool_payload["tool"]["toolkit"] = "FastapiKit"

    with pytest.raises(ValueError):
        _ = client_no_auth.post(
            "/worker/tools/invoke",
            json=call_tool_payload,
        )
        # The handler catches the ValueError and returns a 500 internal server error
        # Ideally, this might be a 404 or 400, but BaseWorker.call_tool raises ValueError
        # which isn't automatically mapped to a 4xx by FastAPI unless handled explicitly.
        # TODO fix this.
