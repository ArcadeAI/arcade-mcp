"""Tests for evals_runner error handling."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from arcade_cli.evals_runner import (
    CaptureTaskResult,
    EvalTaskResult,
    _run_capture_task,
    _run_eval_task,
    run_capture,
    run_evaluations,
)


class TestEvalTaskResult:
    """Test EvalTaskResult dataclass."""

    def test_from_success(self) -> None:
        """Test creating a successful result."""
        result = EvalTaskResult.from_success("test_suite", "gpt-4o", {"score": 0.9})
        assert result.success is True
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.result == {"score": 0.9}
        assert result.error is None
        assert result.error_type is None

    def test_from_error(self) -> None:
        """Test creating a failed result from an exception."""
        error = ValueError("Something went wrong")
        result = EvalTaskResult.from_error("test_suite", "gpt-4o", error)
        assert result.success is False
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
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
            result = EvalTaskResult.from_error("suite", "model", error)
            assert result.error_type == expected_type


class TestCaptureTaskResult:
    """Test CaptureTaskResult dataclass."""

    def test_from_success(self) -> None:
        """Test creating a successful capture result."""
        mock_captures = [MagicMock(), MagicMock()]
        result = CaptureTaskResult.from_success("test_suite", "gpt-4o", mock_captures)
        assert result.success is True
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"
        assert result.result == mock_captures
        assert result.error is None
        assert result.error_type is None

    def test_from_error(self) -> None:
        """Test creating a failed capture result."""
        error = RuntimeError("Capture failed")
        result = CaptureTaskResult.from_error("test_suite", "gpt-4o", error)
        assert result.success is False
        assert result.error == "Capture failed"
        assert result.error_type == "RuntimeError"
        assert result.result is None


class TestRunEvalTask:
    """Test _run_eval_task error handling."""

    @pytest.mark.asyncio
    async def test_successful_task(self) -> None:
        """Test that successful task returns success result."""
        mock_suite = AsyncMock(return_value={"score": 0.95})
        mock_suite.__name__ = "test_suite"

        result = await _run_eval_task(
            suite_func=mock_suite,
            model="gpt-4o",
            provider_api_key="test-key",
            max_concurrent=1,
            provider="openai",
        )

        assert result.success is True
        assert result.result == {"score": 0.95}
        assert result.suite_name == "test_suite"
        assert result.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_failed_task_returns_error_result(self) -> None:
        """Test that failed task returns error result instead of raising."""
        mock_suite = AsyncMock(side_effect=ValueError("API error"))
        mock_suite.__name__ = "test_suite"

        result = await _run_eval_task(
            suite_func=mock_suite,
            model="gpt-4o",
            provider_api_key="test-key",
            max_concurrent=1,
            provider="openai",
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

        await _run_eval_task(
            suite_func=mock_suite,
            model="claude-sonnet",
            provider_api_key="my-key",
            max_concurrent=5,
            provider="anthropic",
        )

        mock_suite.assert_called_once_with(
            provider_api_key="my-key",
            model="claude-sonnet",
            max_concurrency=5,
            provider="anthropic",
        )


class TestRunCaptureTask:
    """Test _run_capture_task error handling."""

    @pytest.mark.asyncio
    async def test_successful_capture_task(self) -> None:
        """Test that successful capture task returns success result."""
        mock_captures = [MagicMock()]
        mock_suite = AsyncMock(return_value=mock_captures)
        mock_suite.__name__ = "capture_suite"

        result = await _run_capture_task(
            suite_func=mock_suite,
            model="gpt-4o",
            provider_api_key="test-key",
            max_concurrent=1,
            provider="openai",
            include_context=True,
        )

        assert result.success is True
        assert result.result == mock_captures

    @pytest.mark.asyncio
    async def test_failed_capture_task_returns_error_result(self) -> None:
        """Test that failed capture task returns error result."""
        mock_suite = AsyncMock(side_effect=ConnectionError("Network failed"))
        mock_suite.__name__ = "capture_suite"

        result = await _run_capture_task(
            suite_func=mock_suite,
            model="gpt-4o",
            provider_api_key="test-key",
            max_concurrent=1,
            provider="openai",
            include_context=False,
        )

        assert result.success is False
        assert "Network failed" in result.error
        assert result.error_type == "ConnectionError"

    @pytest.mark.asyncio
    async def test_passes_capture_mode_arguments(self) -> None:
        """Test that capture_mode and include_context are passed."""
        mock_suite = AsyncMock(return_value=[])
        mock_suite.__name__ = "capture_suite"

        await _run_capture_task(
            suite_func=mock_suite,
            model="gpt-4o",
            provider_api_key="key",
            max_concurrent=2,
            provider="openai",
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

        with patch("arcade_cli.evals_runner.display_eval_results"):
            with patch("arcade_cli.evals_runner.Progress") as mock_progress:
                # Mock Progress context manager
                mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
                mock_progress.return_value.__exit__ = MagicMock(return_value=None)
                mock_progress.add_task = MagicMock(return_value=0)
                mock_progress.update = MagicMock()

                await run_evaluations(
                    eval_suites=[successful_suite, failing_suite],
                    models_list=["gpt-4o"],
                    provider_api_key="test",
                    max_concurrent=1,
                    provider="openai",
                    show_details=False,
                    output_file=None,
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

        await run_evaluations(
            eval_suites=[failing_suite],
            models_list=["gpt-4o"],
            provider_api_key="test",
            max_concurrent=1,
            provider="openai",
            show_details=False,
            output_file=None,
            failed_only=False,
            console=console,
        )

        # Should print "No evaluations completed successfully"
        console.print.assert_any_call(
            "\n[bold red]No evaluations completed successfully.[/bold red]"
        )

    @pytest.mark.asyncio
    async def test_failure_warning_displayed(self) -> None:
        """Test that failure warnings are displayed."""
        failing_suite = AsyncMock(side_effect=ValueError("Bad input"))
        failing_suite.__name__ = "bad_suite"

        console = MagicMock()

        await run_evaluations(
            eval_suites=[failing_suite],
            models_list=["gpt-4o"],
            provider_api_key="test",
            max_concurrent=1,
            provider="openai",
            show_details=False,
            output_file=None,
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

        with patch("arcade_cli.evals_runner.display_eval_results"):
            await run_evaluations(
                eval_suites=[successful_suite],
                models_list=["gpt-4o"],
                provider_api_key="test",
                max_concurrent=1,
                provider="openai",
                show_details=False,
                output_file=None,
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

        with patch("arcade_cli.evals_runner.display_eval_results"):
            with patch("arcade_cli.evals_runner.Progress") as mock_progress:
                # Mock Progress context manager
                mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
                mock_progress.return_value.__exit__ = MagicMock(return_value=None)
                mock_progress.add_task = MagicMock(return_value=0)
                mock_progress.update = MagicMock()

                await run_evaluations(
                    eval_suites=[mock_suite],
                    models_list=["gpt-4o", "bad-model"],
                    provider_api_key="test",
                    max_concurrent=1,
                    provider="openai",
                    show_details=False,
                    output_file=None,
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

        await run_capture(
            eval_suites=[failing_suite],
            models_list=["gpt-4o"],
            provider_api_key="test",
            max_concurrent=1,
            provider="openai",
            include_context=False,
            capture_file=None,
            console=console,
        )

        console.print.assert_any_call(
            "\n[bold red]No captures completed successfully.[/bold red]"
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

        with patch("arcade_cli.evals_runner.Progress") as mock_progress:
            # Mock Progress context manager
            mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.return_value.__exit__ = MagicMock(return_value=None)
            mock_progress.add_task = MagicMock(return_value=0)
            mock_progress.update = MagicMock()

            await run_capture(
                eval_suites=[successful_suite, failing_suite],
                models_list=["gpt-4o"],
                provider_api_key="test",
                max_concurrent=1,
                provider="openai",
                include_context=False,
                capture_file=None,
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

        await run_capture(
            eval_suites=[failing_suite],
            models_list=["gpt-4o"],
            provider_api_key="test",
            max_concurrent=1,
            provider="openai",
            include_context=False,
            capture_file=None,
            console=console,
        )

        # Check error details are printed
        calls = [str(c) for c in console.print.call_args_list]
        assert any("network_capture" in c for c in calls)
        assert any("ConnectionError" in c for c in calls)
