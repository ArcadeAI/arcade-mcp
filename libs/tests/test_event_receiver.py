import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest
from arcade_cli.event import build_forward_request
from standardwebhooks.webhooks import WebhookVerificationError


def load_example() -> ModuleType:
    path = Path(__file__).parents[2] / "examples" / "event_receiver.py"
    spec = importlib.util.spec_from_file_location("event_receiver", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_documented_receiver_verifies_and_deduplicates_the_exact_request() -> None:
    receiver = load_example()
    secret = "whsec_c29tZS10ZXN0LXNlY3JldA=="  # noqa: S105 - published test fixture
    event = {
        "id": "evt_documented",
        "type": "gmail.message.received",
        "time": "2026-08-29T21:00:00Z",
        "data": {"subject": "CUSTOMER renewal"},
    }
    body, headers = build_forward_request(event, secret, datetime.now(timezone.utc))
    seen: set[str] = set()

    assert receiver.verify_and_record(body, headers, secret, seen) == {
        "type": "gmail.message.received",
        "timestamp": "2026-08-29T21:00:00Z",
        "data": {"subject": "CUSTOMER renewal"},
    }
    assert receiver.verify_and_record(body, headers, secret, seen) is None

    with pytest.raises(WebhookVerificationError):
        receiver.verify_and_record(body + b" ", headers, secret, set())
