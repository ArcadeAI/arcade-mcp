from datetime import datetime, timezone

import pytest
from arcade_cli.event import LocalDestinationError, build_forward_request, resolve_local_target
from standardwebhooks.webhooks import Webhook


@pytest.mark.parametrize(
    ("url", "connect_url", "host_header"),
    [
        ("http://127.0.0.1:8000/hook", "http://127.0.0.1:8000/hook", "127.0.0.1:8000"),
        ("http://[::1]:8000/hook", "http://[::1]:8000/hook", "[::1]:8000"),
    ],
)
def test_resolve_local_target_accepts_explicit_numeric_loopback(
    url: str, connect_url: str, host_header: str
) -> None:
    target = resolve_local_target(url)
    assert target.connect_url == connect_url
    assert target.host_header == host_header


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000/hook",
        "http://127.0.0.1/hook",
        "http://[::1]/hook",
        "http://0.0.0.0:8000/hook",
        "http://127.0.0.2:8000/hook",
        "http://example.com:8000/hook",
        "http://user@127.0.0.1:8000/hook",
    ],
)
def test_resolve_local_target_rejects_every_non_explicit_loopback_form(url: str) -> None:
    with pytest.raises(LocalDestinationError):
        resolve_local_target(url)


def test_build_forward_request_uses_the_production_envelope_and_signature() -> None:
    secret = "whsec_c29tZS10ZXN0LXNlY3JldA=="
    event = {
        "id": "evt_123",
        "type": "gmail.message.received",
        "time": "2026-08-29T21:00:00Z",
        "data": {"subject": "CUSTOMER renewal"},
    }
    attempt_time = datetime(2026, 8, 30, 4, 0, tzinfo=timezone.utc)

    body, headers = build_forward_request(event, secret, attempt_time)

    assert headers["webhook-id"] == "evt_123"
    assert headers["webhook-timestamp"] == str(int(attempt_time.timestamp()))
    assert headers["webhook-replay"] == "false"
    assert headers["content-type"] == "application/json"
    assert Webhook(secret).verify(body, headers) == {
        "type": "gmail.message.received",
        "timestamp": "2026-08-29T21:00:00Z",
        "data": {"subject": "CUSTOMER renewal"},
    }
    with pytest.raises(Exception):
        Webhook(secret).verify(body + b" ", headers)
