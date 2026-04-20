"""Tests for `parse_judge_model_spec` — the pure parser behind `--judge-model`.

The CLI command itself is hard to exercise without real Typer machinery;
the parser is a pure function so it's trivial to pin down. These tests
cover every branch the CLI cares about.
"""

from __future__ import annotations

import pytest
from arcade_cli.main import parse_judge_model_spec


class TestParseJudgeModelSpec:
    def test_none_returns_no_override(self) -> None:
        assert parse_judge_model_spec(None) == (None, None)

    def test_empty_string_returns_no_override(self) -> None:
        assert parse_judge_model_spec("") == (None, None)

    def test_whitespace_only_returns_no_override(self) -> None:
        assert parse_judge_model_spec("   ") == (None, None)

    def test_provider_and_model(self) -> None:
        assert parse_judge_model_spec("openai:gpt-4o") == ("openai", "gpt-4o")

    def test_anthropic_provider(self) -> None:
        assert parse_judge_model_spec("anthropic:claude-sonnet-4-6") == (
            "anthropic",
            "claude-sonnet-4-6",
        )

    def test_provider_is_lowercased(self) -> None:
        """Mixed-case providers are normalized — the CLI is forgiving here."""
        assert parse_judge_model_spec("OpenAI:gpt-4o") == ("openai", "gpt-4o")

    def test_whitespace_around_parts_is_trimmed(self) -> None:
        assert parse_judge_model_spec(" openai : gpt-4o ") == ("openai", "gpt-4o")

    def test_bare_model_defaults_provider_to_openai(self) -> None:
        """Documented behavior: 'no colon' means OpenAI provider."""
        assert parse_judge_model_spec("gpt-4o") == ("openai", "gpt-4o")

    def test_bare_model_trims_whitespace(self) -> None:
        assert parse_judge_model_spec("  gpt-4o  ") == ("openai", "gpt-4o")

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid --judge-model provider"):
            parse_judge_model_spec("google:gemini-pro")

    def test_unknown_provider_message_lists_supported(self) -> None:
        with pytest.raises(ValueError) as exc:
            parse_judge_model_spec("cohere:command-r")
        msg = str(exc.value)
        assert "openai" in msg
        assert "anthropic" in msg
        assert "cohere" in msg

    def test_missing_model_after_colon_raises(self) -> None:
        with pytest.raises(ValueError, match="must specify a model after"):
            parse_judge_model_spec("openai:")

    def test_whitespace_only_model_after_colon_raises(self) -> None:
        with pytest.raises(ValueError, match="must specify a model after"):
            parse_judge_model_spec("openai:   ")

    def test_model_with_internal_colons_preserved(self) -> None:
        """Only the FIRST colon is a delimiter — model names may contain
        their own colons (e.g. ollama-style tags)."""
        assert parse_judge_model_spec("openai:ft:gpt-4o:org:123") == (
            "openai",
            "ft:gpt-4o:org:123",
        )
