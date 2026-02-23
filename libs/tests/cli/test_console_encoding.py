"""Tests for the console.py encoding safety layer.

These tests verify that _needs_utf8() and _configure_windows_utf8()
behave correctly and do not crash, even when the console encoding
would be cp1252 (the default on many Western-European Windows installs).
"""

from __future__ import annotations

import io
import os
import sys
from unittest.mock import patch

import pytest
from arcade_cli.console import _configure_windows_utf8, _needs_utf8

# ---------------------------------------------------------------------------
# _needs_utf8()
# ---------------------------------------------------------------------------


class TestNeedsUtf8:
    """Unit tests for _needs_utf8()."""

    @pytest.mark.parametrize(
        "encoding, expected",
        [
            ("utf-8", False),
            ("UTF-8", False),
            ("utf8", False),
            ("UTF8", False),
            ("cp1252", True),
            ("ascii", True),
            ("latin-1", True),
            ("", True),
            (None, True),
        ],
    )
    def test_known_encodings(self, encoding: str | None, expected: bool) -> None:
        assert _needs_utf8(encoding) is expected


# ---------------------------------------------------------------------------
# _configure_windows_utf8()
# ---------------------------------------------------------------------------


class TestConfigureWindowsUtf8:
    """Tests for _configure_windows_utf8()."""

    def test_noop_on_non_windows(self) -> None:
        """On non-Windows platforms the function should be a no-op."""
        with patch.object(sys, "platform", "linux"):
            # Should not raise and not change anything.
            _configure_windows_utf8()

    def test_reconfigures_when_cp1252(self) -> None:
        """Simulate a cp1252 stdout on 'win32' and verify reconfigure is called."""
        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
        ):
            _configure_windows_utf8()

            # After reconfiguration the streams should be utf-8.
            assert fake_stdout.encoding.lower().replace("-", "") == "utf8"
            assert fake_stderr.encoding.lower().replace("-", "") == "utf8"

    def test_sets_pythonioencoding_env(self) -> None:
        """When reconfiguring, PYTHONIOENCODING should be set as a fallback."""
        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        env_copy = os.environ.copy()
        env_copy.pop("PYTHONIOENCODING", None)

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
            patch.dict(os.environ, env_copy, clear=True),
        ):
            _configure_windows_utf8()
            assert os.environ.get("PYTHONIOENCODING") == "utf-8"

    def test_does_not_override_existing_pythonioencoding(self) -> None:
        """If PYTHONIOENCODING is already set, don't overwrite it."""
        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
            patch.dict(os.environ, {"PYTHONIOENCODING": "ascii"}, clear=False),
        ):
            _configure_windows_utf8()
            # Should keep the existing value.
            assert os.environ["PYTHONIOENCODING"] == "ascii"

    def test_no_crash_when_reconfigure_missing(self) -> None:
        """Streams without a reconfigure method should not crash."""

        class FakeStream:
            encoding = "cp1252"
            # No reconfigure attribute.

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", FakeStream()),
            patch.object(sys, "stderr", FakeStream()),
        ):
            # Should not raise.
            _configure_windows_utf8()

    def test_noop_when_already_utf8(self) -> None:
        """If both streams are already utf-8, nothing should be reconfigured."""
        fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")

        reconfigure_called = False
        original_reconfigure = fake_stdout.reconfigure

        def tracking_reconfigure(**kwargs):
            nonlocal reconfigure_called
            reconfigure_called = True
            return original_reconfigure(**kwargs)

        fake_stdout.reconfigure = tracking_reconfigure  # type: ignore[assignment]

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stderr),
        ):
            _configure_windows_utf8()
            assert not reconfigure_called, "reconfigure should not be called when already utf-8"

    def test_emoji_output_after_reconfigure(self) -> None:
        """After reconfiguring a cp1252 stream, writing emoji should not crash."""
        buf = io.BytesIO()
        fake_stdout = io.TextIOWrapper(buf, encoding="cp1252")

        with (
            patch.object(sys, "platform", "win32"),
            patch.object(sys, "stdout", fake_stdout),
            patch.object(sys, "stderr", fake_stdout),
        ):
            _configure_windows_utf8()
            # Now write emoji — should not raise UnicodeEncodeError.
            fake_stdout.write("Hello! \u2705 \U0001f680 Done.\n")
            fake_stdout.flush()

        output = buf.getvalue().decode("utf-8")
        assert "\u2705" in output
        assert "\U0001f680" in output
