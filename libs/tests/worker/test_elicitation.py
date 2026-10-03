import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
import pytest
from arcade_core.schema import ToolContext
from arcade_serve.fastapi.worker import FastAPIWorker
from arcade_tdk import tool
from fastapi import FastAPI
from fastapi.testclient import TestClient

invocations = []


@tool
async def request_input(
    context: ToolContext,
    mode: Annotated[str, "form or url"],
    timeout: Annotated[float, "The user response deadline in seconds"] = 300.0,
) -> Annotated[dict[str, Any], "The exact client response"]:
    """Request one input before returning its response."""
    invocations.append(mode)
    if mode == "url":
        response = await context.ui.elicit(
            "Approve",
            mode="url",
            url="https://example.com/approval",
            elicitation_id="approval",
            timeout=timeout,
        )
    else:
        response = await context.ui.elicit(
            "Confirm",
            schema={"type": "object", "properties": {"label": {"type": "string"}}},
            timeout=timeout,
        )
    return response.model_dump(exclude_none=True)


@pytest.fixture
def worker_client():
    invocations.clear()
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret=secrets.token_urlsafe(32))
    worker.register_tool(request_input, toolkit_name="Elicitation")
    worker.register_tool(request_input, toolkit_name="Other")
    app.state.worker = worker
    token = jwt.encode({"aud": "worker", "ver": "1"}, worker.secret, algorithm="HS256")
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.parametrize("mode", ["form", "url"])
@pytest.mark.parametrize("action", ["accept", "decline", "cancel"])
def test_worker_elicitation_round_trip(worker_client, mode, action):
    request = {
        "execution_id": "elicitation",
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": mode},
        "context": {"user_id": "alice"},
        "protocol": {
            "version": "2026-07-28",
            "capabilities": {"elicitation": {"form": {}, "url": {}}},
        },
    }
    first = worker_client.post("/worker/tools/invoke", json=request)
    assert first.status_code == 200
    result = first.json()["output"].get("external")
    assert result is not None, first.json()
    assert result["resultType"] == "input_required"
    assert len(result["inputRequests"]) == 1
    key, prompt = next(iter(result["inputRequests"].items()))
    assert prompt["method"] == "elicitation/create"
    assert prompt["params"]["message"] == ("Approve" if mode == "url" else "Confirm")
    response = {"action": action, "x-response": "preserve"}
    if mode == "form":
        response["content"] = {"label": "unchanged"}
    request["protocol"].update({
        "requestState": result["requestState"],
        "inputResponses": {key: response},
    })
    completed = worker_client.post("/worker/tools/invoke", json=request)
    assert completed.status_code == 200
    assert completed.json()["success"] is True, completed.json()
    assert completed.json()["output"]["value"] == response


@pytest.mark.parametrize(
    "mutation",
    ["user", "tool", "inputs", "tampered", "audience", "version", "missing_exp", "expired"],
)
def test_worker_rejects_invalid_continuation_before_tool_execution(worker_client, mutation):
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": "form"},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    state = first["requestState"]
    key = next(iter(first["inputRequests"]))
    if mutation == "user":
        request["context"]["user_id"] = "bob"
    elif mutation == "tool":
        request["tool"]["toolkit"] = "Other"
    elif mutation == "inputs":
        request["inputs"]["mode"] = "url"
    elif mutation == "tampered":
        state = "invalid." + state
    else:
        secret = worker_client.app.state.worker.secret
        claims = jwt.decode(state, secret, algorithms=["HS256"], audience="elicitation")
        if mutation == "audience":
            claims["aud"] = "worker"
        elif mutation == "version":
            claims["ver"] = 2
        elif mutation == "missing_exp":
            del claims["exp"]
        else:
            claims["exp"] = 1
        state = jwt.encode(claims, secret, algorithm="HS256")
    request["protocol"].update({
        "requestState": state,
        "inputResponses": {key: {"action": "accept", "content": {"label": "answer"}}},
    })
    rejected = worker_client.post("/worker/tools/invoke", json=request)
    assert rejected.status_code == 400, rejected.json()
    assert rejected.json()["code"] == -32602
    assert invocations == ["form"]


def test_worker_honors_tool_response_timeout(worker_client, monkeypatch):
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": "form", "timeout": 30.0},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    now = datetime.now(timezone.utc)
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    key = next(iter(first["inputRequests"]))
    request["protocol"].update({
        "requestState": first["requestState"],
        "inputResponses": {key: {"action": "accept", "content": {"label": "late"}}},
    })

    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return now + timedelta(seconds=31)

    monkeypatch.setattr(jwt.api_jwt, "datetime", Later)
    rejected = worker_client.post("/worker/tools/invoke", json=request)
    assert rejected.status_code == 400, rejected.json()
    assert invocations == ["form"]


def test_completed_input_does_not_require_a_fresh_capability(worker_client):
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": "form"},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {}}},
    }
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    key = next(iter(first["inputRequests"]))
    answer = {"action": "accept", "content": {"label": "done"}}
    request["protocol"].update({
        "capabilities": {},
        "requestState": first["requestState"],
        "inputResponses": {key: answer},
    })
    completed = worker_client.post("/worker/tools/invoke", json=request)
    assert completed.json()["output"]["value"] == answer
