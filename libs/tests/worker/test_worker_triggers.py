"""GET /worker/triggers — trigger-type declarations served on the worker protocol."""

import pytest
from arcade_core.triggers import TriggerType
from arcade_serve.fastapi.worker import FastAPIWorker
from fastapi import FastAPI
from fastapi.testclient import TestClient


def webhook_type() -> TriggerType:
    return TriggerType(
        slug="slack.message.received",
        name="Message received",
        description="Fires when a message arrives in a subscribed channel.",
        kind="webhook",
        config_schema={
            "type": "object",
            "properties": {"channel": {"type": "string"}},
            "required": ["channel"],
        },
        payload_schema={"type": "object"},
        sample_payload={"channel": "C123", "text": "hi"},
        version="1",
        verification={"scheme": "slack_v0"},
        normalize_handler="Slack.NormalizeMessageEvent",
    )


def poll_type() -> TriggerType:
    return TriggerType(
        slug="gmail.message.received",
        name="Email received",
        description="Fires when a new email lands in the inbox.",
        kind="poll",
        config_schema={"type": "object"},
        payload_schema={"type": "object"},
        sample_payload={"message_id": "18c4f2", "history_id": "12345"},
        version="1",
        poll_handler="Gmail.PollHistory",
        default_interval=60,
        dedupe="greatest",
    )


@pytest.fixture
def test_app():
    return FastAPI()


@pytest.fixture
def worker_no_auth(test_app):
    worker = FastAPIWorker(app=test_app, disable_auth=True)
    worker.register_trigger_types([webhook_type(), poll_type()])
    return worker


@pytest.fixture
def client_no_auth(test_app, worker_no_auth):
    return TestClient(test_app)


def test_unauthenticated_request_is_rejected():
    app = FastAPI()
    worker = FastAPIWorker(app=app, secret="test-secret")  # noqa: S106
    worker.register_trigger_types([webhook_type()])
    client = TestClient(app)

    response = client.get("/worker/triggers", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def test_no_declarations_yields_an_empty_envelope():
    app = FastAPI()
    FastAPIWorker(app=app, disable_auth=True)
    client = TestClient(app)

    response = client.get("/worker/triggers")

    assert response.status_code == 200
    assert response.json() == {"trigger_types": []}


def test_declared_trigger_types_are_served_with_complete_fields(client_no_auth):
    response = client_no_auth.get("/worker/triggers")

    assert response.status_code == 200
    served = {t["slug"]: t for t in response.json()["trigger_types"]}
    assert set(served) == {"slack.message.received", "gmail.message.received"}

    webhook = served["slack.message.received"]
    assert webhook["kind"] == "webhook"
    assert webhook["config_schema"]["required"] == ["channel"]
    assert webhook["payload_schema"] == {"type": "object"}
    assert webhook["sample_payload"] == {"channel": "C123", "text": "hi"}
    assert webhook["version"] == "1"
    assert webhook["verification"] == {"scheme": "slack_v0"}
    assert webhook["normalize_handler"] == "Slack.NormalizeMessageEvent"

    poll = served["gmail.message.received"]
    assert poll["kind"] == "poll"
    assert poll["poll_handler"] == "Gmail.PollHistory"
    assert poll["default_interval"] == 60
    assert poll["dedupe"] == "greatest"
