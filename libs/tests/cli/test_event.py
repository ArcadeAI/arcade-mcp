from datetime import datetime, timezone

import httpx
import pytest
from arcade_cli.event import (
    LocalDestinationError,
    build_forward_request,
    forward_until_accepted,
    listen_for_events,
    resolve_local_target,
)
from standardwebhooks.webhooks import Webhook, WebhookVerificationError


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
    secret = "whsec_c29tZS10ZXN0LXNlY3JldA=="  # noqa: S105 - published test fixture
    event = {
        "id": "evt_123",
        "type": "gmail.message.received",
        "time": "2026-08-29T21:00:00Z",
        "data": {"subject": "CUSTOMER renewal"},
    }
    attempt_time = datetime.now(timezone.utc)

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
    with pytest.raises(WebhookVerificationError):
        Webhook(secret).verify(body + b" ", headers)


def test_forward_until_accepted_retries_one_event_serially_with_a_stable_identity() -> None:
    event = {
        "id": "evt_retry",
        "type": "order.created",
        "time": "2026-08-29T21:00:00Z",
        "data": {"order_id": "order_1"},
    }
    outcomes: list[Exception | int] = [httpx.ReadTimeout("ambiguous timeout"), 503, 204]
    requests: list[tuple[str, bytes, dict[str, str], float, bool]] = []

    def post(url: str, **kwargs: object) -> httpx.Response:
        requests.append(
            (
                url,
                kwargs["content"],
                kwargs["headers"],
                kwargs["timeout"],
                kwargs["follow_redirects"],  # type: ignore[arg-type]
            )
        )
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome)

    delays: list[float] = []
    retries: list[tuple[str, float]] = []
    attempt_time = datetime.now(timezone.utc)

    attempts = forward_until_accepted(
        event,
        "http://127.0.0.1:8765/hook",
        "whsec_c29tZS10ZXN0LXNlY3JldA==",
        post=post,
        sleep=delays.append,
        now=lambda: attempt_time,
        on_retry=lambda reason, delay: retries.append((reason, delay)),
    )

    assert attempts == 3
    assert delays == [1, 2]
    assert len(retries) == 2
    assert {request[2]["webhook-id"] for request in requests} == {"evt_retry"}
    assert len({request[1] for request in requests}) == 1
    assert all(request[3] == 20 for request in requests)
    assert all(request[4] is False for request in requests)


def test_listen_for_events_reconnects_from_the_last_acknowledged_cursor_in_order() -> None:
    event_one = {
        "id": "evt_1",
        "type": "event.one",
        "time": "2026-08-29T21:00:00Z",
        "data": {},
    }
    event_two = {
        "id": "evt_2",
        "type": "event.two",
        "time": "2026-08-29T21:00:01Z",
        "data": {},
    }
    feed_outcomes: list[Exception | httpx.Response] = [
        httpx.ConnectError("temporary disconnect"),
        httpx.Response(
            200,
            json={
                "items": [
                    {"event": event_one, "cursor": "cursor-1"},
                    {"event": event_two, "cursor": "cursor-2"},
                ],
                "next_cursor": "cursor-2",
            },
        ),
    ]
    requested_cursors: list[str] = []

    def get(_url: str, **kwargs: object) -> httpx.Response:
        requested_cursors.append(kwargs["params"]["cursor"])  # type: ignore[index]
        outcome = feed_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def post(_url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(204)

    class ProofComplete(Exception):
        pass

    forwarded: list[str] = []

    def on_forwarded(event: dict[str, object], _attempts: int) -> None:
        forwarded.append(str(event["id"]))
        if len(forwarded) == 2:
            raise ProofComplete

    delays: list[float] = []
    with pytest.raises(ProofComplete):
        listen_for_events(
            "https://api.example.test/v1/orgs/org/projects/project/event-feed",
            {"Authorization": "Bearer test"},
            {"cursor": "latest", "event_type": "event.one"},
            "http://127.0.0.1:8765/hook",
            "whsec_c29tZS10ZXN0LXNlY3JldA==",  # noqa: S106 - published test fixture
            get=get,
            post=post,
            sleep=delays.append,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=on_forwarded,
        )

    assert requested_cursors == ["latest", "latest"]
    assert forwarded == ["evt_1", "evt_2"]
    assert delays == [1]
