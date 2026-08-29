import json
import threading
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from arcade_core.schema import ToolAuthorizationContext, ToolContext
from arcade_tdk.protected_api import ProtectedAPIOutcome, call_protected_api


@pytest.fixture
def protected_api_server() -> Generator[tuple[str, list[dict[str, Any]]], None, None]:
    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            requests.append({
                "authorization": self.headers.get("Authorization"),
                "path": self.path,
            })
            status_code = int(self.path.removeprefix("/"))
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "accepted"}).encode())

        def log_message(self, format_string: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_outcome", "expected_value"),
    [
        (200, ProtectedAPIOutcome.ACCEPTED, {"message": "accepted"}),
        (403, ProtectedAPIOutcome.AUTHORIZATION_DENIED, None),
        (503, ProtectedAPIOutcome.UNAVAILABLE, None),
    ],
)
async def test_call_protected_api_makes_one_authenticated_attempt(
    protected_api_server: tuple[str, list[dict[str, Any]]],
    status_code: int,
    expected_outcome: ProtectedAPIOutcome,
    expected_value: Any,
) -> None:
    base_url, requests = protected_api_server
    sentinel = "target-token-sentinel"
    context = ToolContext(authorization=ToolAuthorizationContext(token=sentinel))

    result = await call_protected_api(
        context,
        "POST",
        f"{base_url}/{status_code}",
        timeout=1,
    )

    assert result.outcome is expected_outcome
    assert result.value == expected_value
    assert requests == [
        {
            "authorization": "Bearer target-token-sentinel",
            "path": f"/{status_code}",
        }
    ]
