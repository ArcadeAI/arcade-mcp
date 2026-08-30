import ipaddress
import json
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx
import typer
from arcade_core.constants import PROD_ENGINE_HOST
from standardwebhooks.webhooks import Webhook

from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import compute_base_url, get_auth_headers

app = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

state = {
    "engine_url": compute_base_url(
        host=PROD_ENGINE_HOST, port=None, force_tls=False, force_no_tls=False
    )
}


class LocalDestinationError(ValueError):
    """The forwarding destination is not an explicit loopback URL."""


@dataclass(frozen=True)
class ResolvedLocalTarget:
    connect_url: str
    host_header: str


class EventFeedError(RuntimeError):
    """The Engine feed cannot be continued without developer action."""


def generate_listen_secret() -> str:
    return ""


@app.callback()
def main(
    host: str = typer.Option(PROD_ENGINE_HOST, "--host", "-h", help="The Arcade Engine host."),
    port: int | None = typer.Option(None, "--port", "-p", help="The Arcade Engine port."),
    force_tls: bool = typer.Option(False, "--tls", help="Force TLS for Arcade Engine."),
    force_no_tls: bool = typer.Option(False, "--no-tls", help="Disable TLS for Arcade Engine."),
) -> None:
    state["engine_url"] = compute_base_url(force_tls, force_no_tls, host, port)


@app.command("listen", help="Forward future project events to a local HTTP handler.")
def listen(
    forward_to: str = typer.Option(..., "--forward-to", help="Local HTTP receiver URL."),
    org_id: str | None = typer.Option(None, "--org", help="Organization ID."),
    project_id: str | None = typer.Option(None, "--project", help="Project ID."),
    event_type: str | None = typer.Option(None, "--event-type", help="Filter by event type."),
    source_type: str | None = typer.Option(None, "--source-type", help="Filter by source type."),
    source_id: str | None = typer.Option(None, "--source-id", help="Filter by source ID."),
    user_id: str | None = typer.Option(None, "--user-id", help="Filter by application user."),
    connection_id: str | None = typer.Option(
        None, "--connection-id", help="Filter by connected account."
    ),
    webhook_subscription_id: str | None = typer.Option(
        None, "--webhook-subscription-id", help="Mirror one webhook's captured matches."
    ),
) -> None:
    return None


def resolve_local_target(url: str) -> ResolvedLocalTarget:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise LocalDestinationError("forwarding URL is invalid") from exc

    host = parsed.hostname
    if (
        parsed.scheme != "http"
        or host is None
        or port is None
        or not 1 <= port <= 65535
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise LocalDestinationError(
            "forwarding URL must be HTTP, include an explicit port, and have no credentials"
        )

    normalized_host = host.lower()
    if normalized_host == "localhost":
        address = _resolve_localhost(port)
    elif normalized_host in {"127.0.0.1", "::1"}:
        address = normalized_host
    else:
        raise LocalDestinationError("forwarding URL must use localhost, 127.0.0.1, or [::1]")

    connect_host = f"[{address}]" if ":" in address else address
    original_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    connect_url = urlunsplit(
        SplitResult("http", f"{connect_host}:{port}", parsed.path, parsed.query, "")
    )
    return ResolvedLocalTarget(connect_url=connect_url, host_header=f"{original_host}:{port}")


def build_forward_request(
    event: dict[str, Any], secret: str, attempt_time: datetime
) -> tuple[bytes, dict[str, str]]:
    if attempt_time.tzinfo is None or attempt_time.utcoffset() is None:
        raise ValueError("attempt_time must include a UTC offset")
    body = json.dumps(
        {"type": event["type"], "timestamp": event["time"], "data": event["data"]},
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    webhook_id = str(event["id"])
    timestamp = str(int(attempt_time.timestamp()))
    signature = Webhook(secret).sign(webhook_id, attempt_time, body.decode())
    return body, {
        "content-type": "application/json",
        "webhook-id": webhook_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": signature,
        "webhook-replay": "false",
    }


def forward_until_accepted(
    event: dict[str, Any],
    forward_to: str,
    secret: str,
    *,
    post: Callable[..., httpx.Response],
    sleep: Callable[[float], None],
    now: Callable[[], datetime],
    on_retry: Callable[[str, float], None],
) -> int:
    delays = (1.0, 2.0, 4.0, 5.0)
    attempt = 0
    while True:
        attempt += 1
        target = resolve_local_target(forward_to)
        body, headers = build_forward_request(event, secret, now())
        headers["host"] = target.host_header
        try:
            response = post(
                target.connect_url,
                content=body,
                headers=headers,
                timeout=20.0,
                follow_redirects=False,
            )
            if 200 <= response.status_code < 300:
                return attempt
            reason = f"receiver returned HTTP {response.status_code}"
        except httpx.RequestError as exc:
            reason = str(exc) or type(exc).__name__

        delay = delays[min(attempt - 1, len(delays) - 1)]
        on_retry(reason, delay)
        sleep(delay)


def listen_for_events(
    feed_url: str,
    headers: dict[str, str],
    params: dict[str, str],
    forward_to: str,
    secret: str,
    *,
    get: Callable[..., httpx.Response],
    post: Callable[..., httpx.Response],
    sleep: Callable[[float], None],
    now: Callable[[], datetime],
    on_retry: Callable[[str, float], None],
    on_forwarded: Callable[[dict[str, Any], int], None],
) -> None:
    cursor = params.get("cursor", "latest")
    while True:
        request_params = {**params, "cursor": cursor}
        try:
            response = get(feed_url, headers=headers, params=request_params, timeout=20.0)
        except httpx.RequestError as exc:
            on_retry(str(exc) or "Engine disconnected", 1.0)
            sleep(1.0)
            continue

        if 400 <= response.status_code < 500:
            raise EventFeedError(_event_feed_error_message(response))
        if response.status_code >= 500:
            on_retry(f"Engine returned HTTP {response.status_code}", 1.0)
            sleep(1.0)
            continue

        payload = response.json()
        if not isinstance(payload, dict):
            raise EventFeedError("Engine returned an invalid event feed response")
        items = payload.get("items")
        next_cursor = payload.get("next_cursor")
        if not isinstance(items, list) or not isinstance(next_cursor, str):
            raise EventFeedError("Engine returned an invalid event feed response")

        for item in items:
            if not isinstance(item, dict):
                raise EventFeedError("Engine returned an invalid event feed item")
            event = item.get("event")
            item_cursor = item.get("cursor")
            if not isinstance(event, dict) or not isinstance(item_cursor, str):
                raise EventFeedError("Engine returned an invalid event feed item")
            attempts = forward_until_accepted(
                event,
                forward_to,
                secret,
                post=post,
                sleep=sleep,
                now=now,
                on_retry=on_retry,
            )
            cursor = item_cursor
            on_forwarded(event, attempts)

        cursor = next_cursor
        sleep(1.0)


def _event_feed_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("message"), str):
        return f"Engine rejected the event feed ({response.status_code}): {payload['message']}"
    return f"Engine rejected the event feed with HTTP {response.status_code}"


def _resolve_localhost(port: int) -> str:
    try:
        addresses = {
            str(info[4][0])
            for info in socket.getaddrinfo("localhost", port, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise LocalDestinationError("localhost could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
        raise LocalDestinationError("localhost resolved to a non-loopback address")
    return sorted(addresses, key=lambda address: (":" in address, address))[0]
