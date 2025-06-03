import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs

import yaml
from rich.console import Console

from arcade_cli.constants import (
    ARCADE_CONFIG_PATH,
    CREDENTIALS_FILE_PATH,
    LOGIN_FAILED_HTML,
    LOGIN_SUCCESS_HTML,
)

console = Console()


class LoginCallbackHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, state: str, **kwargs):  # type: ignore[no-untyped-def]
        self.state = state  # Simple CSRF protection
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 Argument `format` is shadowing a Python builtin
        # Override to suppress logging to stdout
        pass

    def _parse_login_response(self) -> tuple[str, str, str] | None:
        # Parse the query string from the URL
        query_string = self.path.split("?", 1)[-1]
        params = parse_qs(query_string)
        returned_state = params.get("state", [None])[0]

        if returned_state != self.state:
            console.print(
                "❌ Login failed: Invalid login attempt. Please try again.", style="bold red"
            )
            return None

        api_key = params.get("api_key", [None])[0] or ""
        email = params.get("email", [None])[0] or ""
        warning = params.get("warning", [None])[0] or ""

        return api_key, email, warning

    def _handle_login_response(self) -> bool:
        result = self._parse_login_response()
        if result is None:
            return False
        api_key, email, warning = result

        if warning:
            console.print(warning, style="bold yellow")

        # If API key and email are received, store them in a file
        if not api_key or not email:
            console.print(
                "❌ Login failed: No credentials received. Please try again.", style="bold red"
            )
            return False

        # ensure the ARCADE_CONFIG_PATH directory exists
        if not os.path.exists(ARCADE_CONFIG_PATH):
            os.makedirs(ARCADE_CONFIG_PATH, exist_ok=True)

        # TODO don't overwrite existing config
        new_config = {"cloud": {"api": {"key": api_key}, "user": {"email": email}}}
        with open(CREDENTIALS_FILE_PATH, "w") as f:
            yaml.dump(new_config, f)

        # Send a success response to the browser
        console.print(
            f"""✅ Hi there, {email}!

Your Arcade API key is: {api_key}
Stored in: {CREDENTIALS_FILE_PATH}""",
            style="bold green",
        )
        return True

    def do_GET(self) -> None:  # This naming is correct, required by BaseHTTPRequestHandler
        success = self._handle_login_response()
        if success:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(LOGIN_SUCCESS_HTML)
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(LOGIN_FAILED_HTML)

        # Always shut down the server so it doesn't keep running
        threading.Thread(target=self.server.shutdown).start()


class LocalAuthCallbackServer:
    def __init__(self, state: str, port: int = 9905):
        self.state = state
        self.port = port
        self.httpd: HTTPServer | None = None

    def run_server(self) -> None:
        # Initialize and run the server
        server_address = ("", self.port)
        handler = lambda *args, **kwargs: LoginCallbackHandler(*args, state=self.state, **kwargs)
        self.httpd = HTTPServer(server_address, handler)
        self.httpd.serve_forever()

    def shutdown_server(self) -> None:
        # Shut down the server gracefully
        if self.httpd:
            self.httpd.shutdown()


def check_existing_login(suppress_message: bool = False) -> bool:
    """
    Check if the user is already logged in by verifying the config file.

    Args:
        suppress_message (bool): If True, suppress the logged in message.

    Returns:
        bool: True if the user is already logged in, False otherwise.
    """
    if not os.path.exists(CREDENTIALS_FILE_PATH):
        return False

    if os.path.exists(CREDENTIALS_FILE_PATH):
        try:
            with open(CREDENTIALS_FILE_PATH) as f:
                config: dict[str, Any] = yaml.safe_load(f)
            cloud_config = config.get("cloud", {})
            api_key = cloud_config.get("api", {}).get("key")
            email = cloud_config.get("user", {}).get("email")

            if api_key and email:
                if not suppress_message:
                    console.print(f"You're already logged in as {email}. ", style="bold green")
                return True
        except yaml.YAMLError:
            console.print(
                f"Error: Invalid configuration file at {CREDENTIALS_FILE_PATH}", style="bold red"
            )
        except Exception as e:
            console.print(f"Error: Unable to read configuration file: {e!s}", style="bold red")

    return True
