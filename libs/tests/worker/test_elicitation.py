import hmac
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


@tool
async def request_twice(context: ToolContext) -> Annotated[list[dict[str, Any]], "Both responses"]:
    """Ask for a form, then request a separate external approval."""
    first = await context.ui.elicit("First", schema={"type": "object", "properties": {}})
    second = await context.ui.elicit(
        "Second", mode="url", url="https://example.com/approval", elicitation_id="second"
    )
    return [first.model_dump(exclude_none=True), second.model_dump(exclude_none=True)]


@pytest.fixture
def worker_client():
    invocations.clear()
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret=secrets.token_urlsafe(32))
    worker.register_tool(request_input, toolkit_name="Elicitation")
    worker.register_tool(request_input, toolkit_name="Other")
    worker.register_tool(request_twice, toolkit_name="Elicitation")
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
        secret = hmac.digest(
            worker_client.app.state.worker.secret.encode(), b"arcade-elicitation-state-v1", "sha256"
        )
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


@pytest.mark.parametrize("declare_url", [True, False])
def test_worker_replays_prior_inputs_and_checks_current_capabilities(worker_client, declare_url):
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestTwice"},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    key1 = next(iter(first["inputRequests"]))
    answer1 = {"action": "accept", "content": {"original": "first"}, "x-first": True}
    request["protocol"].update({
        "capabilities": {"elicitation": {"url": {}}} if declare_url else {},
        "requestState": first["requestState"],
        "inputResponses": {key1: answer1},
    })
    output = worker_client.post("/worker/tools/invoke", json=request).json()["output"]
    if not declare_url:
        assert output["protocol_error"]["code"] == -32021
        assert output["protocol_error"]["data"]["requiredCapabilities"] == {"elicitation": {"url": {}}}
        assert output.get("external") is None
        return
    second = output["external"]
    key2, prompt = next(iter(second["inputRequests"].items()))
    assert (key1, key2) == ("1", "2")
    assert prompt["params"]["mode"] == "url"
    assert prompt["params"]["message"] == "Second"
    answer2 = {"action": "cancel", "x-second": "preserve"}
    request["protocol"].update({
        "capabilities": {},
        "requestState": second["requestState"],
        "inputResponses": {key2: answer2},
    })
    final = worker_client.post("/worker/tools/invoke", json=request)
    assert final.json()["success"] is True, final.json()
    assert final.json()["output"]["value"] == [answer1, answer2]


@tool
async def ordinary() -> Annotated[str, "The ordinary tool result"]:
    """Return without asking the client for input."""
    return "ordinary result"


def test_weak_auth_secret_cannot_issue_state_but_ordinary_calls_work():
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret=secrets.token_urlsafe(4))
    worker.register_tool(request_input, toolkit_name="Elicitation")
    worker.register_tool(ordinary, toolkit_name="Elicitation")
    token = jwt.encode({"aud": "worker", "ver": "1"}, worker.secret, algorithm="HS256")
    request = {
        "tool": {"toolkit": "Elicitation", "name": "Ordinary"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        result = client.post("/worker/tools/invoke", json=request)
        assert result.json()["output"]["value"] == "ordinary result", result.json()
        request["tool"]["name"] = "RequestInput"
        request["inputs"] = {"mode": "form"}
        blocked = client.post("/worker/tools/invoke", json=request)
        assert blocked.json()["output"].get("external") is None, blocked.json()
        assert blocked.json()["output"]["error"] is not None


def test_continuation_uses_a_different_key_from_worker_auth(worker_client):
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": "form"},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            first["requestState"],
            worker_client.app.state.worker.secret,
            algorithms=["HS256"],
            audience="elicitation",
        )


def test_new_round_has_a_fresh_fifteen_minute_lifetime(worker_client, monkeypatch):
    import arcade_core.elicitation as runtime

    clock = {"now": datetime.now(timezone.utc)}

    class ControlledDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock["now"]

    monkeypatch.setattr(jwt.api_jwt, "datetime", ControlledDatetime)
    monkeypatch.setattr(runtime.time, "time", lambda: clock["now"].timestamp())
    request = {
        "tool": {"toolkit": "Elicitation", "name": "RequestTwice"},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {"elicitation": {"form": {}}}},
    }
    first = worker_client.post("/worker/tools/invoke", json=request).json()["output"]["external"]
    key1 = next(iter(first["inputRequests"]))
    answer1 = {"action": "accept", "content": {"label": "first"}}
    clock["now"] += timedelta(minutes=6)
    request["protocol"].update({
        "capabilities": {"elicitation": {"url": {}}},
        "requestState": first["requestState"],
        "inputResponses": {key1: answer1},
    })
    next_round = worker_client.post("/worker/tools/invoke", json=request)
    assert next_round.status_code == 200, next_round.json()
    second = next_round.json()["output"]["external"]
    key2 = next(iter(second["inputRequests"]))
    answer2 = {"action": "accept"}
    clock["now"] += timedelta(minutes=10)
    request["protocol"].update({
        "capabilities": {},
        "requestState": second["requestState"],
        "inputResponses": {key2: answer2},
    })
    final = worker_client.post("/worker/tools/invoke", json=request)
    assert final.status_code == 200, final.json()
    assert final.json()["output"]["value"] == [answer1, answer2]


@pytest.mark.parametrize("mode", ["form", "url"])
def test_worker_missing_mode_is_a_protocol_error(worker_client, mode):
    response = worker_client.post("/worker/tools/invoke", json={
        "tool": {"toolkit": "Elicitation", "name": "RequestInput"},
        "inputs": {"mode": mode},
        "context": {"user_id": "alice"},
        "protocol": {"version": "2026-07-28", "capabilities": {}},
    })
    assert response.status_code == 200
    body = response.json()
    error = body["output"].get("protocol_error")
    assert error is not None, "worker does not preserve the missing-mode protocol error"
    assert error["code"] == -32021
    assert error["data"]["requiredCapabilities"]["elicitation"] == {mode: {}}
    assert body["success"] is False
    assert body["output"].get("external") is None
    assert body["output"].get("value") is None
    assert invocations == [mode]
