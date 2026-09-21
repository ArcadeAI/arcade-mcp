"""Requests say which CLI sent them.

An installation that reports a status older clients mishandle needs to tell
them apart. Which statuses an installation can report depends on the deployment
provider behind it, so the CLI cannot decide this for itself -- it can only make
the question answerable.
"""

from importlib import metadata

from arcade_cli.utils import cli_version_headers, get_auth_headers


class TestVersionHeaders:
    def test_the_installed_version_is_advertised(self):
        assert cli_version_headers()["X-Arcade-CLI-Version"] == metadata.version("arcade-mcp")

    def test_the_user_agent_names_the_cli(self):
        assert cli_version_headers()["User-Agent"].startswith("arcade-cli/")

    def test_unattended_requests_carry_it(self, monkeypatch):
        monkeypatch.setenv("ARCADE_URL", "https://engine.internal.example")
        monkeypatch.setenv("ARCADE_API_KEY", "key")
        headers = get_auth_headers()
        assert headers["Authorization"] == "Bearer key"
        assert headers["X-Arcade-CLI-Version"] == metadata.version("arcade-mcp")
