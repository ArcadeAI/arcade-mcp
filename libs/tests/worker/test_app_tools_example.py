"""The authored package survives the discovery path used by a managed worker."""

from pathlib import Path

import pytest
from arcade_core.schema import ToolCallRequest, ToolReference
from arcade_core.toolkit import Toolkit
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI
from fastapi.testclient import TestClient

EXAMPLE = Path(__file__).resolve().parents[3] / "examples/mcp_servers/app_tools"


@pytest.fixture
def example_worker(monkeypatch):
    monkeypatch.syspath_prepend(str(EXAMPLE / "src"))
    app = FastAPI()
    worker = FastAPIWorker(app=app, disable_auth=True)
    worker.register_toolkit(Toolkit.from_directory(EXAMPLE))
    with TestClient(app) as client:
        yield client


def test_preview_tool_points_to_a_readable_ui_document(example_worker):
    tools = example_worker.get("/worker/tools").json()
    preview = next((tool for tool in tools if tool["name"] == "PreviewGreeting"), None)
    assert preview is not None, "The deployable example must publish PreviewGreeting"
    uri = preview["_meta"]["ui"]["resourceUri"]
    resource = example_worker.post("/worker/resources/read", json={"uri": uri}).json()
    assert resource["contents"][0]["uri"] == uri
    assert resource["contents"][0]["mimeType"] == "text/html;profile=mcp-app"
    assert "Uppercase greeting" in resource["contents"][0]["text"]


def test_https_resource_keeps_its_separate_web_address(example_worker):
    resources = example_worker.post("/worker/resources/list", json={}).json()["resources"]
    guide = next(resource for resource in resources if resource["uri"].startswith("https:"))
    response = example_worker.post("/worker/resources/read", json={"uri": guide["uri"]})
    assert response.status_code == 200
    content = response.json()["contents"][0]
    version = Toolkit.from_directory(EXAMPLE).version
    assert content["uri"] == f"https://AppTools/{version}/author-guide"
    assert content["_meta"]["webUrl"] == "https://modelcontextprotocol.io/extensions/apps/overview"
    assert content["_meta"]["webUrl"] in content["text"]


def test_secondary_tool_declares_google_authorization(example_worker):
    tools = example_worker.get("/worker/tools").json()
    profile = next(tool for tool in tools if tool["name"] == "GoogleProfile")
    assert profile["requirements"]["authorization"]["provider_id"] == "google"
    assert profile["requirements"]["authorization"]["oauth2"]["scopes"] == [
        "https://www.googleapis.com/auth/userinfo.profile"
    ]


@pytest.mark.parametrize(
    ("tool", "expected"),
    [("PreviewGreeting", "Hello, Grace!"), ("UppercaseGreeting", "HELLO, GRACE!")],
)
def test_editor_actions_execute_real_tools(example_worker, tool, expected):
    request = ToolCallRequest(
        execution_id="app-example-test",
        tool=ToolReference(toolkit="AppTools", name=tool),
        inputs={"name": "Grace"},
    )
    response = example_worker.post("/worker/tools/invoke", json=request.model_dump())
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["output"]["value"] == expected
