import subprocess
import sys
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import urlopen

from arcade_cli.authn import OAuthCallbackServer, _open_browser, oauth_callback_server


def test_oauth_callback_server_success() -> None:
    state = "test-state"
    with oauth_callback_server(state, port=0) as server:
        url = f"{server.get_redirect_uri()}?code=abc123&state={state}"
        with urlopen(url) as response:
            assert response.status == 200
            response.read()
        assert server.wait_for_result(timeout=1.0) is True

    assert server.result["code"] == "abc123"


def test_oauth_callback_server_timeout() -> None:
    state = "test-timeout"
    with oauth_callback_server(state, port=0) as server:
        assert server.wait_for_result(timeout=0.05) is False

    assert "Timed out" in server.result["error"]


def test_oauth_callback_server_binds_to_loopback() -> None:
    """The callback server must bind to 127.0.0.1 (loopback) to avoid
    Windows Firewall prompts and ensure localhost is always reachable."""
    state = "test-bind"
    with oauth_callback_server(state, port=0) as server:
        assert server.httpd is not None
        host, _port = server.httpd.server_address
        assert host == "127.0.0.1", f"Expected 127.0.0.1 but got {host}"
        # Also confirm the redirect URI uses localhost.
        redirect = server.get_redirect_uri()
        assert redirect.startswith("http://localhost:")
        server.shutdown_server()


def test_oauth_callback_server_state_mismatch() -> None:
    """Requests with a mismatched state parameter should return an error."""
    state = "correct-state"
    with oauth_callback_server(state, port=0) as server:
        url = f"{server.get_redirect_uri()}?code=abc&state=wrong-state"
        try:
            with urlopen(url) as response:
                response.read()
        except HTTPError:
            pass  # Expected — handler returns 400 for state mismatch.
        server.wait_for_result(timeout=1.0)

    assert "error" in server.result


def test_oauth_callback_server_missing_code() -> None:
    """Requests without a code parameter should produce an error result."""
    state = "no-code-state"
    with oauth_callback_server(state, port=0) as server:
        url = f"{server.get_redirect_uri()}?state={state}"
        try:
            with urlopen(url) as response:
                response.read()
        except HTTPError:
            pass  # Expected — handler returns 400 for missing code.
        server.wait_for_result(timeout=1.0)

    assert "error" in server.result


def test_oauth_callback_server_wait_until_ready() -> None:
    """wait_until_ready() should return True once the server is listening."""
    state = "ready-test"
    server = OAuthCallbackServer(state, port=0)

    import threading

    t = threading.Thread(target=server.run_server, daemon=True)
    t.start()

    assert server.wait_until_ready(timeout=5.0) is True
    assert server.httpd is not None
    assert server.port != 0  # Ephemeral port was assigned.

    server.shutdown_server()
    t.join(timeout=2)


def test_oauth_callback_server_wait_until_ready_timeout() -> None:
    """wait_until_ready() should return False if the server never starts."""
    state = "ready-timeout"
    server = OAuthCallbackServer(state, port=0)
    # Don't start the server — ready_event never gets set.
    assert server.wait_until_ready(timeout=0.05) is False


def test_perform_oauth_login_always_shows_auth_url() -> None:
    """perform_oauth_login should always surface the auth URL via on_status,
    even when _open_browser succeeds."""
    status_messages: list[str] = []

    def capture_status(msg: str) -> None:
        status_messages.append(msg)

    # We need to mock the entire OAuth flow since we can't hit a real coordinator.
    # The key thing to verify is that on_status receives the auth URL.
    with (
        patch("arcade_cli.authn.fetch_cli_config") as mock_config,
        patch("arcade_cli.authn.create_oauth_client"),
        patch("arcade_cli.authn.generate_authorization_url") as mock_gen_url,
        patch("arcade_cli.authn._open_browser") as mock_browser,
        patch("arcade_cli.authn.oauth_callback_server") as mock_server_ctx,
    ):
        # Set up mocks
        mock_config.return_value = MagicMock()
        mock_gen_url.return_value = ("https://example.com/auth?state=abc", "verifier123")
        mock_browser.return_value = True  # Browser "succeeded"

        # Mock the callback server context manager
        mock_server = MagicMock()
        mock_server.get_redirect_uri.return_value = "http://localhost:9999/callback"
        mock_server.result = {"error": "timeout for test"}  # Force an error exit
        mock_server.wait_for_result.return_value = False
        mock_server_ctx.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_server_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from arcade_cli.authn import OAuthLoginError, perform_oauth_login

        try:
            perform_oauth_login(
                "https://fake-coordinator.example.com",
                on_status=capture_status,
                callback_timeout_seconds=1,
            )
        except OAuthLoginError:
            pass  # Expected — our mock returns an error result.

    # Verify the auth URL was shown even though browser.open returned True.
    url_messages = [m for m in status_messages if "https://example.com/auth" in m]
    assert len(url_messages) >= 1, (
        f"Auth URL should appear in status messages. Got: {status_messages}"
    )
    assert any("Use this authorization link if needed" in m for m in status_messages)


def test_perform_oauth_login_shows_url_when_browser_fails() -> None:
    """When _open_browser fails, the URL should still be shown."""
    status_messages: list[str] = []

    def capture_status(msg: str) -> None:
        status_messages.append(msg)

    with (
        patch("arcade_cli.authn.fetch_cli_config") as mock_config,
        patch("arcade_cli.authn.create_oauth_client"),
        patch("arcade_cli.authn.generate_authorization_url") as mock_gen_url,
        patch("arcade_cli.authn._open_browser") as mock_browser,
        patch("arcade_cli.authn.oauth_callback_server") as mock_server_ctx,
    ):
        mock_config.return_value = MagicMock()
        mock_gen_url.return_value = ("https://example.com/auth?state=xyz", "verifier456")
        mock_browser.return_value = False  # Browser failed

        mock_server = MagicMock()
        mock_server.get_redirect_uri.return_value = "http://localhost:9999/callback"
        mock_server.result = {"error": "timeout for test"}
        mock_server.wait_for_result.return_value = False
        mock_server_ctx.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_server_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from arcade_cli.authn import OAuthLoginError, perform_oauth_login

        try:
            perform_oauth_login(
                "https://fake-coordinator.example.com",
                on_status=capture_status,
                callback_timeout_seconds=1,
            )
        except OAuthLoginError:
            pass

    url_messages = [m for m in status_messages if "https://example.com/auth" in m]
    assert len(url_messages) >= 1
    assert any("Use this authorization link if needed" in m for m in status_messages)
    # When browser fails, the message should say "Could not open a browser"
    browser_fail_msgs = [m for m in status_messages if "Could not open a browser" in m]
    assert len(browser_fail_msgs) >= 1


def test_perform_oauth_login_timeout_clamps_negative() -> None:
    """Negative --timeout values should be clamped to the default."""
    from arcade_cli.authn import DEFAULT_OAUTH_TIMEOUT_SECONDS

    status_messages: list[str] = []

    def capture_status(msg: str) -> None:
        status_messages.append(msg)

    with (
        patch("arcade_cli.authn.fetch_cli_config") as mock_config,
        patch("arcade_cli.authn.create_oauth_client"),
        patch("arcade_cli.authn.generate_authorization_url") as mock_gen_url,
        patch("arcade_cli.authn._open_browser") as mock_browser,
        patch("arcade_cli.authn.oauth_callback_server") as mock_server_ctx,
    ):
        mock_config.return_value = MagicMock()
        mock_gen_url.return_value = ("https://example.com/auth", "v")
        mock_browser.return_value = True

        mock_server = MagicMock()
        mock_server.get_redirect_uri.return_value = "http://localhost:9999/callback"
        mock_server.result = {"error": "timeout"}
        mock_server.wait_for_result.return_value = False
        mock_server_ctx.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_server_ctx.return_value.__exit__ = MagicMock(return_value=False)

        from arcade_cli.authn import OAuthLoginError, perform_oauth_login

        try:
            perform_oauth_login(
                "https://fake.example.com",
                on_status=capture_status,
                callback_timeout_seconds=-5,
            )
        except OAuthLoginError:
            pass

    # The timeout message should show the default, not -5.
    timeout_msgs = [m for m in status_messages if "timeout:" in m.lower()]
    assert any(str(DEFAULT_OAUTH_TIMEOUT_SECONDS) in m for m in timeout_msgs), (
        f"Expected default timeout {DEFAULT_OAUTH_TIMEOUT_SECONDS} in messages: {timeout_msgs}"
    )


# ---------------------------------------------------------------------------
# _open_browser() — CMD-window suppression on Windows
# ---------------------------------------------------------------------------


class TestOpenBrowser:
    """Tests for the _open_browser helper that suppresses CMD flash on Windows.

    On Windows the priority order is:
      1. ctypes ShellExecuteW (direct Win32 API, no console)
      2. rundll32 url.dll (GUI binary, no console)
      3. os.startfile (CPython wrapper)
      4. webbrowser.open (stdlib fallback)
    """

    def test_delegates_to_webbrowser_on_non_windows(self) -> None:
        """On non-Windows, _open_browser should use webbrowser.open."""
        with (
            patch.object(sys, "platform", "linux"),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.return_value = True
            result = _open_browser("https://example.com")
            assert result is True
            mock_wb.open.assert_called_once_with("https://example.com")

    def test_tries_ctypes_shellexecute_first_on_windows(self) -> None:
        """On Windows, _open_browser should try ctypes ShellExecuteW first."""
        import ctypes

        # On non-Windows, ctypes.windll doesn't exist; provide a mock
        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(return_value=42)
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with patch.object(sys, "platform", "win32"), patch.object(
            ctypes, "windll", mock_windll, create=True
        ):
            result = _open_browser("https://example.com")
            assert result is True

    def test_falls_back_to_rundll32_on_windows(self) -> None:
        """If ctypes fails, try rundll32 url.dll."""
        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen") as mock_popen,
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True) as mock_si_cls,
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", subprocess.DEVNULL),
        ):
            mock_si = MagicMock()
            mock_si.dwFlags = 0
            mock_si_cls.return_value = mock_si
            mock_popen.return_value = MagicMock()

            result = _open_browser("https://example.com")
            assert result is True
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0] == "rundll32"

    def test_falls_back_to_startfile_on_windows(self) -> None:
        """If ctypes and rundll32 fail, try os.startfile."""
        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen", side_effect=Exception("fail")),
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True, return_value=MagicMock()),
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", -1),
            patch("arcade_cli.authn.os.startfile", create=True) as mock_sf,
        ):
            result = _open_browser("https://example.com")
            assert result is True
            mock_sf.assert_called_once_with("https://example.com")

    def test_falls_back_to_webbrowser_if_all_else_fails_on_windows(self) -> None:
        """If ctypes, rundll32, and startfile all fail, use webbrowser.open."""
        import ctypes

        mock_shell32 = MagicMock()
        mock_shell32.ShellExecuteW = MagicMock(side_effect=Exception("ctypes failed"))
        mock_windll = MagicMock()
        mock_windll.shell32 = mock_shell32

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch("arcade_cli.authn.subprocess.Popen", side_effect=Exception("fail")),
            patch("arcade_cli.authn.subprocess.STARTUPINFO", create=True, return_value=MagicMock()),
            patch("arcade_cli.authn.subprocess.STARTF_USESHOWWINDOW", 1, create=True),
            patch("arcade_cli.authn.subprocess.DEVNULL", -1),
            patch("arcade_cli.authn.os.startfile", side_effect=OSError, create=True),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.return_value = True
            result = _open_browser("https://example.com")
            assert result is True
            mock_wb.open.assert_called_once()

    def test_returns_false_if_everything_fails(self) -> None:
        """If all methods fail, _open_browser should return False."""
        with (
            patch.object(sys, "platform", "linux"),
            patch("arcade_cli.authn.webbrowser") as mock_wb,
        ):
            mock_wb.open.side_effect = Exception("no browser")
            result = _open_browser("https://example.com")
            assert result is False
