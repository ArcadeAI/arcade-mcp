"""Minimal verified receiver for `arcade event listen`."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar, cast

from standardwebhooks.webhooks import Webhook, WebhookVerificationError


def verify_and_record(
    body: bytes,
    headers: dict[str, str],
    secret: str,
    seen: set[str],
) -> dict[str, Any] | None:
    event = cast(dict[str, Any], Webhook(secret).verify(body, headers))
    event_id = next(value for key, value in headers.items() if key.lower() == "webhook-id")
    if event_id in seen:
        return None
    seen.add(event_id)
    return event


class EventHandler(BaseHTTPRequestHandler):
    secret = ""
    seen: ClassVar[set[str]] = set()

    def do_POST(self) -> None:
        if self.path != "/events":
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers.get("content-length", "0")))
        try:
            event = verify_and_record(body, dict(self.headers.items()), self.secret, self.seen)
        except (WebhookVerificationError, StopIteration):
            self.send_error(400, "invalid webhook signature")
            return
        if event is not None:
            print(json.dumps(event, indent=2), flush=True)
        self.send_response(204)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


if __name__ == "__main__":
    EventHandler.secret = os.environ["ARCADE_WEBHOOK_SECRET"]
    print("Listening on http://127.0.0.1:8788/events", flush=True)
    try:
        HTTPServer(("127.0.0.1", 8788), EventHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
