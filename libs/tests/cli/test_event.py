import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from arcade_cli.event import (
    EventFeedError,
    EventListenInterrupted,
    LocalDestinationError,
    app,
    build_forward_request,
    forward_until_accepted,
    generate_listen_secret,
    listen_for_events,
    resolve_local_target,
)
from standardwebhooks.webhooks import Webhook, WebhookVerificationError
from typer.testing import CliRunner

runner = CliRunner()


@pytest.mark.parametrize(
    ("url", "connect_url", "host_header"),
    [
        ("http://localhost:8788/events", "http://127.0.0.1:8788/events", "localhost:8788"),
        ("http://LOCALHOST:8788/events", "http://127.0.0.1:8788/events", "localhost:8788"),
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
        "http://192.168.1.5:8788/events",
        "http://localhost@evil.com/events",
        "http://localtest.me:8788/events",
        "http://localhost.evil.com:8788/events",
        "ftp://127.0.0.1:8788/events",
        "http://[::ffff:127.0.0.1]:8788/events",
        "http://127.1:8788/events",
        "http://2130706433:8788/events",
        "http://localhost.:8788/events",
        "http://[::]:8788/events",
        "http://[0:0:0:0:0:0:0:1]:8788/events",
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
        requests.append((
            url,
            kwargs["content"],
            kwargs["headers"],
            kwargs["timeout"],
            kwargs["follow_redirects"],  # type: ignore[arg-type]
        ))
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
                "items": [{"event": event_one, "cursor": "cursor-1"}],
                "next_cursor": "cursor-1",
            },
        ),
        httpx.Response(
            200,
            json={
                "items": [{"event": event_two, "cursor": "cursor-2"}],
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
            "whsec_c29tZS10ZXN0LXNlY3JldA==",
            get=get,
            post=post,
            sleep=delays.append,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=on_forwarded,
        )

    assert requested_cursors == ["latest", "latest", "cursor-1"]
    assert forwarded == ["evt_1", "evt_2"]
    assert delays == [1, 1]


def test_event_listen_command_exposes_context_secret_and_server_filters() -> None:
    with (
        patch("arcade_cli.event.get_auth_headers", return_value={"Authorization": "Bearer test"}),
        patch("arcade_cli.event.generate_listen_secret", return_value="whsec_session"),
        patch("arcade_cli.event.listen_for_events", side_effect=KeyboardInterrupt) as listen_mock,
    ):
        result = runner.invoke(
            app,
            [
                "--host",
                "engine.example.test",
                "listen",
                "--forward-to",
                "http://127.0.0.1:8765/hook",
                "--org",
                "org_1",
                "--project",
                "project_1",
                "--event-type",
                "gmail.message.received",
                "--user-id",
                "user_1",
            ],
        )

    assert result.exit_code == 0
    assert "org_1" in result.output
    assert "project_1" in result.output
    assert "whsec_session" in result.output
    assert "future" in result.output.lower()
    assert "https://engine.example.test" in result.output
    assert "event_type=gmail.message.received" in result.output
    assert "user_id=user_1" in result.output
    kwargs = listen_mock.call_args.kwargs
    assert listen_mock.call_args.args[0].endswith("/v1/orgs/org_1/projects/project_1/event-feed")
    assert kwargs["params"] == {
        "cursor": "latest",
        "event_type": "gmail.message.received",
        "user_id": "user_1",
    }


def test_event_command_is_registered_on_the_arcade_cli() -> None:
    from arcade_cli.main import cli

    with (
        patch("arcade_cli.main._credentials_file_contains_legacy", return_value=False),
        patch("arcade_cli.main.check_and_notify"),
        patch("arcade_cli.main.check_existing_login", return_value=True),
    ):
        result = runner.invoke(cli, ["event", "--help"])

    assert result.exit_code == 0
    assert "listen" in result.output


def test_redirect_is_reported_without_following_it() -> None:
    class RetryObserved(Exception):
        pass

    posts: list[str] = []
    retries: list[str] = []

    def post(url: str, **_kwargs: object) -> httpx.Response:
        posts.append(url)
        return httpx.Response(302, headers={"location": "https://example.com/events"})

    with pytest.raises(RetryObserved):
        forward_until_accepted(
            {"id": "evt_redirect", "type": "event.test", "time": "now", "data": {}},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            post=post,
            sleep=lambda _delay: (_ for _ in ()).throw(RetryObserved()),
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda reason, _delay: retries.append(reason),
        )

    assert posts == ["http://127.0.0.1:8788/events"]
    assert retries == [
        "event evt_redirect to http://127.0.0.1:8788/events: receiver returned HTTP 302"
    ]


def test_localhost_is_resolved_again_and_rebinding_stops_before_the_second_post() -> None:
    resolutions = [
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 8788))],
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.7", 8788))],
    ]
    posts: list[str] = []

    def post(url: str, **_kwargs: object) -> httpx.Response:
        posts.append(url)
        return httpx.Response(503)

    with (
        patch("arcade_cli.event.socket.getaddrinfo", side_effect=resolutions),
        pytest.raises(LocalDestinationError, match="non-loopback"),
    ):
        forward_until_accepted(
            {"id": "evt_rebind", "type": "event.test", "time": "now", "data": {}},
            "http://localhost:8788/events",
            generate_listen_secret(),
            post=post,
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
        )

    assert posts == ["http://127.0.0.1:8788/events"]


def test_each_listen_session_uses_an_independent_secret() -> None:
    first_secret = generate_listen_secret()
    second_secret = generate_listen_secret()
    event = {"id": "evt_secret", "type": "event.test", "time": "now", "data": {}}

    body, headers = build_forward_request(event, second_secret, datetime.now(timezone.utc))

    assert first_secret != second_secret
    assert Webhook(second_secret).verify(body, headers)["type"] == "event.test"
    with pytest.raises(WebhookVerificationError):
        Webhook(first_secret).verify(body, headers)


def test_terminal_engine_auth_failure_stops_without_forwarding_or_retrying() -> None:
    requests: list[str] = []
    forwards: list[str] = []
    retries: list[str] = []

    def get(url: str, **_kwargs: object) -> httpx.Response:
        requests.append(url)
        return httpx.Response(401, json={"message": "authentication required"})

    def post(url: str, **_kwargs: object) -> httpx.Response:
        forwards.append(url)
        return httpx.Response(204)

    with pytest.raises(EventFeedError, match="authentication required"):
        listen_for_events(
            "https://engine.example.test/event-feed",
            {"Authorization": "Bearer expired"},
            {"cursor": "latest"},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            get=get,
            post=post,
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda reason, _delay: retries.append(reason),
            on_forwarded=lambda _event, _attempts: None,
        )

    assert len(requests) == 1
    assert forwards == []
    assert retries == []


def test_interrupting_a_blocked_handoff_names_the_unforwarded_event() -> None:
    response = httpx.Response(
        200,
        json={
            "items": [
                {
                    "event": {
                        "id": "evt_blocked",
                        "type": "event.test",
                        "time": "now",
                        "data": {},
                    },
                    "cursor": "cursor-1",
                }
            ],
            "next_cursor": "cursor-1",
        },
    )

    with pytest.raises(EventListenInterrupted, match="evt_blocked"):
        listen_for_events(
            "https://engine.example.test/event-feed",
            {},
            {"cursor": "latest"},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            get=lambda _url, **_kwargs: response,
            post=lambda _url, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=lambda _event, _attempts: None,
        )


def test_listener_accepts_the_engine_openapi_response_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "engine_event_feed_response.json"
    payload = json.loads(fixture_path.read_text())
    response = httpx.Response(200, json=payload)

    class ContractProved(Exception):
        pass

    forwarded: list[str] = []

    def post(_url: str, **kwargs: object) -> httpx.Response:
        forwarded.append(str(kwargs["headers"]["webhook-id"]))  # type: ignore[index]
        return httpx.Response(204)

    with pytest.raises(ContractProved):
        listen_for_events(
            "https://engine.example.test/event-feed",
            {},
            {"cursor": "latest"},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            get=lambda _url, **_kwargs: response,
            post=post,
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=lambda _event, _attempts: (_ for _ in ()).throw(ContractProved()),
        )

    assert forwarded == ["evt_contract"]


def test_listener_continues_from_the_engine_empty_page_fixture() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    responses = [
        httpx.Response(200, json=json.loads((fixture_dir / name).read_text()))
        for name in (
            "engine_event_feed_empty_response.json",
            "engine_event_feed_response.json",
        )
    ]
    requested_cursors: list[str] = []

    def get(_url: str, **kwargs: object) -> httpx.Response:
        requested_cursors.append(kwargs["params"]["cursor"])  # type: ignore[index]
        return responses.pop(0)

    class ProofComplete(Exception):
        pass

    with pytest.raises(ProofComplete):
        listen_for_events(
            "https://engine.example.test/event-feed",
            {},
            {"cursor": "latest"},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            get=get,
            post=lambda _url, **_kwargs: httpx.Response(204),
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=lambda _event, _attempts: (_ for _ in ()).throw(ProofComplete()),
        )

    assert requested_cursors == ["latest", "cursor_empty_page"]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not json"),
        httpx.Response(
            200,
            json={
                "items": [
                    {
                        "event": {"type": "event.missing-id", "time": "now", "data": {}},
                        "cursor": "cursor-1",
                    }
                ],
                "next_cursor": "cursor-1",
            },
        ),
    ],
)
def test_listener_stops_cleanly_on_an_invalid_engine_response(response: httpx.Response) -> None:
    with pytest.raises(EventFeedError, match="invalid event feed"):
        listen_for_events(
            "https://engine.example.test/event-feed",
            {},
            {"cursor": "latest"},
            "http://127.0.0.1:8788/events",
            generate_listen_secret(),
            get=lambda _url, **_kwargs: response,
            post=lambda _url, **_kwargs: httpx.Response(204),
            sleep=lambda _delay: None,
            now=lambda: datetime.now(timezone.utc),
            on_retry=lambda _reason, _delay: None,
            on_forwarded=lambda _event, _attempts: None,
        )
