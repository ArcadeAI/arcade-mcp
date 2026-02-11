import datetime as _dt
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from arcade_cli.authn import (
    build_coordinator_url,
    create_oauth_client,
    exchange_code_for_tokens,
    fetch_cli_config,
    fetch_whoami,
    generate_authorization_url,
    save_credentials_from_whoami,
)

LOG_PATH = Path(__file__).with_name("login_probe.log")
CALLBACK_PORT = 9905


def _log(message: str) -> None:
    timestamp = _dt.datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp} {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def main() -> None:
    coordinator_url = build_coordinator_url("cloud.arcade.dev", None)
    cli_config = fetch_cli_config(coordinator_url)
    oauth_client = create_oauth_client(cli_config)
    expected_state = str(uuid.uuid4())

    redirect_uri = f"http://localhost:{CALLBACK_PORT}/callback"
    auth_url, code_verifier = generate_authorization_url(
        oauth_client, cli_config, redirect_uri, expected_state
    )

    _log(f"AUTH_URL={auth_url}")
    _log(f"REDIRECT_URI={redirect_uri}")
    _log(f"EXPECTED_STATE={expected_state}")

    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def _send(self, status: int, body: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            state = params.get("state", [None])[0]
            code = params.get("code", [None])[0]
            error = params.get("error", [None])[0]
            error_description = params.get("error_description", [None])[0]

            _log(
                "CALLBACK "
                f"path={parsed.path} "
                f"state={state} "
                f"code={'set' if code else 'none'} "
                f"error={error} "
                f"error_description={error_description}"
            )

            if state != expected_state:
                self._send(
                    400,
                    "Invalid state parameter. This may be a security issue.\n"
                    "This server is still waiting for a valid callback.\n",
                )
                return

            if error or error_description:
                result["error"] = error_description or error or "unknown_error"
                self._send(400, f"Login failed: {result['error']}\n")
                return

            if not code:
                self._send(400, "No authorization code received.\n")
                return

            result["code"] = code
            self._send(200, "Login callback received. You can close this tab.\n")
            threading.Thread(target=httpd.shutdown).start()

    try:
        httpd = HTTPServer(("", CALLBACK_PORT), Handler)
    except Exception as exc:  # pragma: no cover - diagnostic only
        _log(f"FAILED_TO_BIND port={CALLBACK_PORT} error={exc}")
        return

    _log(f"CALLBACK_SERVER_LISTENING port={CALLBACK_PORT}")

    httpd.serve_forever()

    if "code" not in result:
        _log("NO_CODE_RECEIVED; exiting without saving credentials.")
        return

    try:
        _log("EXCHANGE_CODE_FOR_TOKENS start")
        tokens = exchange_code_for_tokens(
            oauth_client,
            result["code"],
            redirect_uri,
            code_verifier,
        )
        _log("EXCHANGE_CODE_FOR_TOKENS done")
    except Exception as exc:  # pragma: no cover - diagnostic only
        _log(f"EXCHANGE_CODE_FOR_TOKENS failed error={exc}")
        return

    try:
        _log("FETCH_WHOAMI start")
        whoami = fetch_whoami(coordinator_url, tokens.access_token)
        _log("FETCH_WHOAMI done")
    except Exception as exc:  # pragma: no cover - diagnostic only
        _log(f"FETCH_WHOAMI failed error={exc}")
        return

    try:
        _log("SAVE_CREDENTIALS start")
        save_credentials_from_whoami(tokens, whoami, coordinator_url)
        _log("SAVE_CREDENTIALS done")
        _log(f"CREDENTIALS_SAVED email={whoami.email}")
    except Exception as exc:  # pragma: no cover - diagnostic only
        _log(f"SAVE_CREDENTIALS failed error={exc}")
        return


if __name__ == "__main__":
    main()
