import tempfile
from pathlib import Path
from unittest.mock import Mock

from arcade_cli.display import display_eval_results
from arcade_evals.eval import EvaluationResult


def create_mock_evaluation_result(passed: bool, warning: bool, score: float) -> Mock:
    """Create a mock EvaluationResult with the specified properties."""
    evaluation = Mock(spec=EvaluationResult)
    evaluation.passed = passed
    evaluation.warning = warning
    evaluation.score = score
    evaluation.failure_reason = None
    evaluation.results = []
    return evaluation


def test_display_eval_results_normal() -> None:
    """Test normal display without filtering."""
    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Test Case 1",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
                        ),
                    },
                    {
                        "name": "Test Case 2",
                        "input": "Test input 2",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.5
                        ),
                    },
                ],
            }
        ]
    ]

    # Should not raise any exceptions
    display_eval_results(results, show_details=False)


def test_display_eval_results_with_failed_only() -> None:
    """Test display with failed_only flag and original counts."""
    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Failed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.3
                        ),
                    },
                ],
            }
        ]
    ]

    # Original counts: 3 total, 1 passed, 1 failed, 1 warned
    original_counts = (3, 1, 1, 1)

    # Should not raise any exceptions
    display_eval_results(
        results,
        show_details=False,
        failed_only=True,
        original_counts=original_counts,
    )


def test_display_eval_results_with_output_file() -> None:
    """Test display with output file."""
    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Test Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.9
                        ),
                    },
                ],
            }
        ]
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_output.txt"

        display_eval_results(
            results,
            show_details=False,
            output_file=str(output_file),
        )

        # Verify file was created
        assert output_file.exists()

        # Verify file contains some expected content
        content = output_file.read_text()
        assert "Model:" in content or "gpt-4o" in content


def test_display_eval_results_with_output_file_and_failed_only() -> None:
    """Test display with both output file and failed_only flag."""
    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Failed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.2
                        ),
                    },
                ],
            }
        ]
    ]

    original_counts = (5, 3, 1, 1)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test_output.txt"

        display_eval_results(
            results,
            show_details=False,
            output_file=str(output_file),
            failed_only=True,
            original_counts=original_counts,
        )

        # Verify file was created
        assert output_file.exists()

        # Verify file contains disclaimer and summary
        content = output_file.read_text()
        assert "failed-only" in content.lower() or "failed evaluation" in content.lower()
        assert "Total: 5" in content  # Should show original total


def test_display_eval_results_creates_parent_directories() -> None:
    """Test that output file creates parent directories if they don't exist."""
    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Test Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.9
                        ),
                    },
                ],
            }
        ]
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "nested" / "path" / "test_output.txt"

        # Parent directories don't exist yet
        assert not output_file.parent.exists()

        display_eval_results(
            results,
            show_details=False,
            output_file=str(output_file),
        )

        # Parent directories should be created
        assert output_file.parent.exists()
        assert output_file.exists()


def test_display_eval_results_with_warnings() -> None:
    """Test display with cases that have warnings."""
    results: list = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Warning Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=True, score=0.85
                        ),
                    },
                    {
                        "name": "Failed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.3
                        ),
                    },
                ],
            }
        ]
    ]

    # Should not raise any exceptions
    display_eval_results(results, show_details=False)


def test_display_eval_results_empty_results() -> None:
    """Test display with empty results."""
    results: list = []

    # Should not raise any exceptions
    display_eval_results(results, show_details=False)


def test_display_eval_results_with_details() -> None:
    """Test display with show_details=True."""
    evaluation = create_mock_evaluation_result(passed=True, warning=False, score=0.95)
    evaluation.results = [
        {
            "field": "test_field",
            "match": True,
            "score": 1.0,
            "weight": 1.0,
            "expected": "expected_value",
            "actual": "actual_value",
            "is_criticized": True,
        }
    ]

    results = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Test Case",
                        "input": "Test input",
                        "evaluation": evaluation,
                    },
                ],
            }
        ]
    ]

    # Should not raise any exceptions
    display_eval_results(results, show_details=True)
