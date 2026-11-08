"""Usage telemetry must never carry raw CLI arguments (DEP-716, VDP F-2).

These tests run real commands through the tracked CLI with the PostHog-backed
usage service mocked, then check every captured payload for the sensitive value.
"""

import json
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.main import cli
from arcade_cli.usage.command_tracker import command_tracker
from arcade_cli.usage.constants import EVENT_CLI_COMMAND_FAILED
from arcade_core.usage.constants import PROP_ERROR_MESSAGE
from typer.testing import CliRunner

SECRET_VALUE = "super-secret-value-8f3a"  # noqa: S105
API_KEY = "sk-test-leaky-key-5c71"

runner = CliRunner()


@pytest.fixture
def captured_events() -> Iterator[MagicMock]:
    """Enable tracking and replace the usage service with a mock."""
    mock_service = MagicMock()
    mock_identity = MagicMock()
    mock_identity.anon_id = "anon-123"
    mock_identity.should_alias.return_value = False
    mock_identity.get_distinct_id.return_value = "anon-123"
    with (
        patch("arcade_cli.usage.command_tracker.is_tracking_enabled", return_value=True),
        patch.object(command_tracker, "usage_service", mock_service),
        patch.object(command_tracker, "identity", mock_identity),
        patch.object(command_tracker, "_get_org_project_context", return_value=(None, None)),
        # Commands that need an Arcade session would stop at the login check first.
        patch("arcade_cli.main._credentials_file_contains_legacy", return_value=False),
        patch("arcade_cli.main.check_existing_login", return_value=True),
    ):
        yield mock_service


def _failed_payloads(mock_service: MagicMock) -> list[dict]:
    payloads = []
    for call in mock_service.capture.call_args_list:
        if call.args[0] == EVENT_CLI_COMMAND_FAILED:
            payloads.append(call.kwargs["properties"])
    return payloads


def test_secret_set_with_empty_key_does_not_send_value(captured_events: MagicMock) -> None:
    result = runner.invoke(cli, ["secret", "set", f"={SECRET_VALUE}"])

    assert result.exit_code != 0
    payloads = _failed_payloads(captured_events)
    assert payloads, "expected a failed-command event"
    assert SECRET_VALUE not in json.dumps(payloads)
    # The user still learns what went wrong, without the value echoed back.
    assert "KEY=VALUE" in result.output
    assert SECRET_VALUE not in result.output


def test_evals_api_key_without_provider_does_not_send_key(
    captured_events: MagicMock, tmp_path
) -> None:
    result = runner.invoke(cli, ["evals", str(tmp_path), "--api-key", API_KEY])

    assert result.exit_code != 0
    payloads = _failed_payloads(captured_events)
    assert payloads, "expected a failed-command event"
    assert API_KEY not in json.dumps(payloads)
    assert "provider:key" in result.output
    assert API_KEY not in result.output


def test_failed_command_reports_exception_type_only(captured_events: MagicMock) -> None:
    runner.invoke(cli, ["secret", "set", f"={SECRET_VALUE}"])

    payloads = _failed_payloads(captured_events)
    assert payloads[0][PROP_ERROR_MESSAGE] == "BadParameter"


def test_group_callback_failure_does_not_send_error_text(captured_events: MagicMock) -> None:
    """Callback failures (login checks and the like) go through a second tracking path."""
    import typer
    from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
    from arcade_cli.utils import CLIError

    app = TrackedTyper(cls=TrackedTyperGroup)

    @app.callback()
    def main(ctx: typer.Context) -> None:
        raise CLIError("Callback failed", ValueError(SECRET_VALUE))

    @app.command()
    def run() -> None:
        pass

    result = runner.invoke(app, ["run"])

    assert result.exit_code != 0
    payloads = _failed_payloads(captured_events)
    assert payloads, "expected a failed-command event"
    assert SECRET_VALUE not in json.dumps(payloads)
    assert payloads[0][PROP_ERROR_MESSAGE] == "CLIError"
