"""Tests for evals_runner error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_cli.evals_runner import (
    ALL_FORMATS,
    CaptureTaskResult,
    EvalTaskResult,
    _run_capture_task,
    _run_eval_task,
    parse_output_formats,
    run_capture,
    run_evaluations,
)
from arcade_cli.utils import ModelSpec, Provider


class TestEvalTaskResult:
    """Test EvalTaskResult dataclass."""

    def test_from_success(self) -> None:
        """Test creating a successful result."""
        result = EvalTaskResult.from_success("test_suite", "gpt-4o", "openai", {"score": 0.9})
        assert result.success is True
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert result.result == {"score": 0.9}
        assert result.error is None
        assert result.error_type is None

    def test_from_error(self) -> None:
        """Test creating a failed result from an exception."""
        error = ValueError("Something went wrong")
        result = EvalTaskResult.from_error("test_suite", "gpt-4o", "openai", error)
        assert result.success is False
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert result.error == "Something went wrong"
        assert result.error_type == "ValueError"
        assert result.result is None

    def test_from_error_with_different_exception_types(self) -> None:
        """Test that error_type captures the correct exception class name."""
        errors = [
            (RuntimeError("runtime"), "RuntimeError"),
            (TypeError("type"), "TypeError"),
            (KeyError("key"), "KeyError"),
            (ConnectionError("conn"), "ConnectionError"),
        ]
        for error, expected_type in errors:
            result = EvalTaskResult.from_error("suite", "model", "openai", error)
            assert result.error_type == expected_type

    def test_display_name(self) -> None:
        """Test that display_name shows provider/model format."""
        result = EvalTaskResult.from_success("suite", "gpt-4o", "openai", {})
        assert result.display_name == "openai/gpt-4o"

        result2 = EvalTaskResult.from_success("suite", "claude-3-sonnet", "anthropic", {})
        assert result2.display_name == "anthropic/claude-3-sonnet"


class TestCaptureTaskResult:
    """Test CaptureTaskResult dataclass."""

    def test_from_success(self) -> None:
        """Test creating a successful capture result."""
        mock_captures = [MagicMock(), MagicMock()]
        result = CaptureTaskResult.from_success("test_suite", "gpt-4o", "openai", mock_captures)
        assert result.success is True
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert result.result == mock_captures
        assert result.error is None
        assert result.error_type is None

    def test_from_error(self) -> None:
        """Test creating a failed capture result."""
        error = RuntimeError("Capture failed")
        result = CaptureTaskResult.from_error("test_suite", "gpt-4o", "openai", error)
        assert result.success is False
        assert result.error == "Capture failed"
        assert result.error_type == "RuntimeError"
        assert result.result is None

    def test_display_name(self) -> None:
        """Test that display_name shows provider/model format."""
        result = CaptureTaskResult.from_success("suite", "gpt-4o", "openai", [])
        assert result.display_name == "openai/gpt-4o"


class TestRunEvalTask:
    """Test _run_eval_task error handling."""

    @pytest.mark.asyncio
    async def test_successful_task(self) -> None:
        """Test that successful task returns success result."""
        mock_suite = AsyncMock(return_value={"score": 0.95})
        mock_suite.__name__ = "test_suite"

        model_spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test-key")
        result = await _run_eval_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=1,
        )

        assert result.success is True
        assert result.result == {"score": 0.95}
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"

    @pytest.mark.asyncio
    async def test_failed_task_returns_error_result(self) -> None:
        """Test that failed task returns error result instead of raising."""
        mock_suite = AsyncMock(side_effect=ValueError("API error"))
        mock_suite.__name__ = "test_suite"

        model_spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test-key")
        result = await _run_eval_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=1,
        )

        assert result.success is False
        assert "API error" in result.error
        assert result.error_type == "ValueError"
        assert result.result is None

    @pytest.mark.asyncio
    async def test_passes_correct_arguments_to_suite(self) -> None:
        """Test that correct arguments are passed to the suite function."""
        mock_suite = AsyncMock(return_value={"score": 1.0})
        mock_suite.__name__ = "test_suite"

        model_spec = ModelSpec(provider=Provider.ANTHROPIC, model="claude-sonnet", api_key="my-key")
        await _run_eval_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=5,
            include_context=False,
        )

        mock_suite.assert_called_once_with(
            provider_api_key="my-key",
            model="claude-sonnet",
            max_concurrency=5,
            provider="anthropic",
            include_context=False,
        )


class TestRunCaptureTask:
    """Test _run_capture_task error handling."""

    @pytest.mark.asyncio
    async def test_successful_capture_task(self) -> None:
        """Test that successful capture task returns success result."""
        mock_captures = [MagicMock()]
        mock_suite = AsyncMock(return_value=mock_captures)
        mock_suite.__name__ = "capture_suite"

        model_spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test-key")
        result = await _run_capture_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=1,
            include_context=True,
        )

        assert result.success is True
        assert result.result == mock_captures

    @pytest.mark.asyncio
    async def test_failed_capture_task_returns_error_result(self) -> None:
        """Test that failed capture task returns error result."""
        mock_suite = AsyncMock(side_effect=ConnectionError("Network failed"))
        mock_suite.__name__ = "capture_suite"

        model_spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test-key")
        result = await _run_capture_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=1,
            include_context=False,
        )

        assert result.success is False
        assert "Network failed" in result.error
        assert result.error_type == "ConnectionError"

    @pytest.mark.asyncio
    async def test_capture_mode_passed(self) -> None:
        """Test that capture_mode and include_context are passed."""
        mock_suite = AsyncMock(return_value=[])
        mock_suite.__name__ = "capture_suite"

        model_spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="key")
        await _run_capture_task(
            suite_func=mock_suite,
            model_spec=model_spec,
            max_concurrent=2,
            include_context=True,
        )

        mock_suite.assert_called_once_with(
            provider_api_key="key",
            model="gpt-4o",
            max_concurrency=2,
            provider="openai",
            capture_mode=True,
            include_context=True,
        )


class TestRunEvaluationsErrorHandling:
    """Test run_evaluations handles partial failures."""

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self) -> None:
        """Test that one failing task doesn't stop others."""
        successful_suite = AsyncMock(return_value=MagicMock())
        successful_suite.__name__ = "success_suite"

        failing_suite = AsyncMock(side_effect=RuntimeError("Oops"))
        failing_suite.__name__ = "failing_suite"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        with (
            patch("arcade_cli.evals_runner.display_eval_results"),
            patch("arcade_cli.evals_runner.Progress") as mock_progress,
        ):
            # Mock Progress context manager
            mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.return_value.__exit__ = MagicMock(return_value=None)
            mock_progress.add_task = MagicMock(return_value=0)
            mock_progress.update = MagicMock()

            await run_evaluations(
                eval_suites=[successful_suite, failing_suite],
                model_specs=model_specs,
                max_concurrent=1,
                show_details=False,
                output_file=None,
                output_format="txt",
                failed_only=False,
                console=console,
            )

        # Verify both were attempted
        successful_suite.assert_called_once()
        failing_suite.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_failures_reports_none_completed(self) -> None:
        """Test appropriate message when all tasks fail."""
        failing_suite = AsyncMock(side_effect=RuntimeError("Oops"))
        failing_suite.__name__ = "failing_suite"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        await run_evaluations(
            eval_suites=[failing_suite],
            model_specs=model_specs,
            max_concurrent=1,
            show_details=False,
            output_file=None,
            output_format="txt",
            failed_only=False,
            console=console,
        )

        # Should print "No evaluations completed successfully" (with emoji)
        console.print.assert_any_call(
            "\n[bold red]❌ No evaluations completed successfully.[/bold red]"
        )

    @pytest.mark.asyncio
    async def test_failure_warning_displayed(self) -> None:
        """Test that failure warnings are displayed."""
        failing_suite = AsyncMock(side_effect=ValueError("Bad input"))
        failing_suite.__name__ = "bad_suite"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        await run_evaluations(
            eval_suites=[failing_suite],
            model_specs=model_specs,
            max_concurrent=1,
            show_details=False,
            output_file=None,
            output_format="txt",
            failed_only=False,
            console=console,
        )

        # Check that failure count is printed
        calls = [str(c) for c in console.print.call_args_list]
        assert any("1 evaluation(s) failed" in c for c in calls)

    @pytest.mark.asyncio
    async def test_all_success_no_failure_warning(self) -> None:
        """Test that no failure warning when all succeed."""
        successful_suite = AsyncMock(return_value=MagicMock())
        successful_suite.__name__ = "success_suite"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        with patch("arcade_cli.evals_runner.display_eval_results"):
            await run_evaluations(
                eval_suites=[successful_suite],
                model_specs=model_specs,
                max_concurrent=1,
                show_details=False,
                output_file=None,
                output_format="txt",
                failed_only=False,
                console=console,
            )

        # Check that no failure warning is printed
        calls = [str(c) for c in console.print.call_args_list]
        assert not any("failed" in c.lower() for c in calls)

    @pytest.mark.asyncio
    async def test_multiple_models_partial_failure(self) -> None:
        """Test partial failure with multiple models."""

        # Suite that fails on one model but succeeds on another
        async def conditional_suite(**kwargs):
            if kwargs["model"] == "bad-model":
                raise RuntimeError("Model not supported")
            return MagicMock()

        mock_suite = AsyncMock(side_effect=conditional_suite)
        mock_suite.__name__ = "conditional_suite"

        console = MagicMock()
        model_specs = [
            ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test"),
            ModelSpec(provider=Provider.OPENAI, model="bad-model", api_key="test"),
        ]

        with (
            patch("arcade_cli.evals_runner.display_eval_results"),
            patch("arcade_cli.evals_runner.Progress") as mock_progress,
        ):
            # Mock Progress context manager
            mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.return_value.__exit__ = MagicMock(return_value=None)
            mock_progress.add_task = MagicMock(return_value=0)
            mock_progress.update = MagicMock()

            await run_evaluations(
                eval_suites=[mock_suite],
                model_specs=model_specs,
                max_concurrent=1,
                show_details=False,
                output_file=None,
                output_format="txt",
                failed_only=False,
                console=console,
            )

        # Should have been called twice
        assert mock_suite.call_count == 2


class TestRunCaptureErrorHandling:
    """Test run_capture handles partial failures."""

    @pytest.mark.asyncio
    async def test_all_captures_fail_reports_none_completed(self) -> None:
        """Test appropriate message when all capture tasks fail."""
        failing_suite = AsyncMock(side_effect=RuntimeError("Capture failed"))
        failing_suite.__name__ = "failing_capture"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        await run_capture(
            eval_suites=[failing_suite],
            model_specs=model_specs,
            max_concurrent=1,
            include_context=False,
            output_file=None,
            output_format="json",
            console=console,
        )

        # Error message includes emoji
        console.print.assert_any_call(
            "\n[bold red]❌ No captures completed successfully.[/bold red]"
        )

    @pytest.mark.asyncio
    async def test_partial_capture_failure_continues(self) -> None:
        """Test that one failing capture doesn't stop others."""
        # Mock CaptureResult
        mock_capture = MagicMock()
        mock_capture.to_dict.return_value = {"test": "data"}
        mock_capture.captured_cases = []

        successful_suite = AsyncMock(return_value=[mock_capture])
        successful_suite.__name__ = "success_capture"

        failing_suite = AsyncMock(side_effect=RuntimeError("Oops"))
        failing_suite.__name__ = "failing_capture"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        with patch("arcade_cli.evals_runner.Progress") as mock_progress:
            # Mock Progress context manager
            mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.return_value.__exit__ = MagicMock(return_value=None)
            mock_progress.add_task = MagicMock(return_value=0)
            mock_progress.update = MagicMock()

            await run_capture(
                eval_suites=[successful_suite, failing_suite],
                model_specs=model_specs,
                max_concurrent=1,
                include_context=False,
                output_file=None,
                output_format="json",
                console=console,
            )

        # Both should have been attempted
        successful_suite.assert_called_once()
        failing_suite.assert_called_once()

        # Check failure warning was printed
        calls = [str(c) for c in console.print.call_args_list]
        assert any("1 capture(s) failed" in c for c in calls)

    @pytest.mark.asyncio
    async def test_capture_failure_details_displayed(self) -> None:
        """Test that capture failure details are shown."""
        failing_suite = AsyncMock(side_effect=ConnectionError("Network error"))
        failing_suite.__name__ = "network_capture"

        console = MagicMock()
        model_specs = [ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="test")]

        await run_capture(
            eval_suites=[failing_suite],
            model_specs=model_specs,
            max_concurrent=1,
            include_context=False,
            output_file=None,
            output_format="json",
            console=console,
        )

        # Check error details are printed
        calls = [str(c) for c in console.print.call_args_list]
        assert any("network_capture" in c for c in calls)
        assert any("ConnectionError" in c for c in calls)


class TestParseOutputFormats:
    """Tests for parse_output_formats function."""

    def test_single_format(self) -> None:
        """Should return a list with a single format."""
        console = MagicMock()
        assert parse_output_formats("md", console) == ["md"]
        assert parse_output_formats("txt", console) == ["txt"]
        assert parse_output_formats("html", console) == ["html"]
        assert parse_output_formats("json", console) == ["json"]

    def test_comma_separated_formats(self) -> None:
        """Should return a list of multiple formats."""
        console = MagicMock()
        assert parse_output_formats("md,html", console) == ["md", "html"]
        assert parse_output_formats("txt,md,html,json", console) == ["txt", "md", "html", "json"]

    def test_comma_separated_with_spaces(self) -> None:
        """Should handle spaces around commas."""
        console = MagicMock()
        assert parse_output_formats("md, html", console) == ["md", "html"]
        assert parse_output_formats(" md , html ", console) == ["md", "html"]

    def test_all_keyword(self) -> None:
        """Should return all formats for 'all' keyword."""
        console = MagicMock()
        assert parse_output_formats("all", console) == ALL_FORMATS
        assert parse_output_formats("ALL", console) == ALL_FORMATS
        assert parse_output_formats("All", console) == ALL_FORMATS

    def test_case_insensitive(self) -> None:
        """Should be case-insensitive."""
        console = MagicMock()
        assert parse_output_formats("MD", console) == ["md"]
        assert parse_output_formats("HTML,JSON", console) == ["html", "json"]

    def test_invalid_formats_raise_error(self) -> None:
        """Should raise ValueError for invalid formats (parse-time validation)."""
        console = MagicMock()

        with pytest.raises(ValueError, match="Invalid format.*invalid"):
            parse_output_formats("md,invalid", console)

        with pytest.raises(ValueError, match="Invalid format.*invalid"):
            parse_output_formats("invalid", console)

    def test_mixed_valid_invalid_raises(self) -> None:
        """Should raise ValueError when any invalid formats present."""
        with pytest.raises(ValueError, match="Invalid format"):
            parse_output_formats("md,foo,html,bar", MagicMock())

    def test_raises_on_invalid_formats(self) -> None:
        """Should raise ValueError when invalid formats are provided."""
        with pytest.raises(ValueError) as exc_info:
            parse_output_formats("xlsx,invalid", MagicMock())

        error_msg = str(exc_info.value)
        assert "Invalid format" in error_msg
        assert "xlsx" in error_msg
        assert "invalid" in error_msg

    def test_raises_on_partially_invalid_formats(self) -> None:
        """Should raise ValueError even when some valid formats exist."""
        with pytest.raises(ValueError) as exc_info:
            parse_output_formats("md,xlsx,html", MagicMock())

        error_msg = str(exc_info.value)
        assert "Invalid format" in error_msg
        assert "xlsx" in error_msg

    def test_no_error_when_all_valid(self) -> None:
        """Should not raise when all formats are valid."""
        console = MagicMock()
        result = parse_output_formats("md,html,json", console)
        assert result == ["md", "html", "json"]
