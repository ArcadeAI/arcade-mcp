from unittest.mock import Mock

from arcade_cli.main import cli
from arcade_cli.utils import filter_failed_evaluations
from arcade_evals.eval import EvaluationResult
from typer.testing import CliRunner

runner = CliRunner()


def create_mock_evaluation_result(passed: bool, warning: bool, score: float) -> Mock:
    """Create a mock EvaluationResult with the specified properties."""
    evaluation = Mock(spec=EvaluationResult)
    evaluation.passed = passed
    evaluation.warning = warning
    evaluation.score = score
    evaluation.failure_reason = None
    evaluation.results = []
    return evaluation


def test_filter_failed_evaluations_mixed_results() -> None:
    """Test filtering logic with mixed passed, failed, and warned cases."""
    all_evaluations = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Passed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
                        ),
                    },
                    {
                        "name": "Warning Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=True, score=0.85
                        ),
                    },
                    {
                        "name": "Failed Case 1",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.3
                        ),
                    },
                    {
                        "name": "Failed Case 2",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.2
                        ),
                    },
                ],
            }
        ]
    ]

    filtered_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Verify original counts
    assert original_counts == (4, 1, 2, 1)

    # Verify filtered results only contain failed cases
    assert len(filtered_evaluations) == 1
    assert len(filtered_evaluations[0]) == 1
    assert len(filtered_evaluations[0][0]["cases"]) == 2
    assert filtered_evaluations[0][0]["cases"][0]["name"] == "Failed Case 1"
    assert filtered_evaluations[0][0]["cases"][1]["name"] == "Failed Case 2"


def test_filter_failed_evaluations_all_passed() -> None:
    """Test filtering when all cases passed (should return empty)."""
    all_evaluations = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Passed Case 1",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
                        ),
                    },
                    {
                        "name": "Passed Case 2",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.98
                        ),
                    },
                ],
            }
        ]
    ]

    filtered_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Verify original counts
    assert original_counts == (2, 2, 0, 0)

    # Verify filtered results are empty (no failed cases)
    assert len(filtered_evaluations) == 0


def test_filter_failed_evaluations_multiple_suites() -> None:
    """Test filtering with multiple eval suites."""
    all_evaluations = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric 1",
                "cases": [
                    {
                        "name": "Passed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
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
        ],
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric 2",
                "cases": [
                    {
                        "name": "Failed Case 2",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.2
                        ),
                    },
                ],
            }
        ],
    ]

    filtered_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Verify original counts
    assert original_counts == (3, 1, 2, 0)

    # Verify filtered results
    assert len(filtered_evaluations) == 2
    assert len(filtered_evaluations[0][0]["cases"]) == 1
    assert len(filtered_evaluations[1][0]["cases"]) == 1


def test_filter_failed_evaluations_multiple_models() -> None:
    """Test filtering with multiple models in same suite."""
    all_evaluations = [
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
            },
            {
                "model": "gpt-3.5-turbo",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Passed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
                        ),
                    },
                    {
                        "name": "Failed Case 2",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=False, warning=False, score=0.2
                        ),
                    },
                ],
            },
        ]
    ]

    filtered_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Verify original counts
    assert original_counts == (3, 1, 2, 0)

    # Verify filtered results - should have both models with failed cases
    assert len(filtered_evaluations) == 1
    assert len(filtered_evaluations[0]) == 2  # Both models have failed cases
    assert len(filtered_evaluations[0][0]["cases"]) == 1  # First model has 1 failed
    assert len(filtered_evaluations[0][1]["cases"]) == 1  # Second model has 1 failed


def test_filter_failed_evaluations_model_with_no_failed() -> None:
    """Test filtering when one model has no failed cases."""
    all_evaluations = [
        [
            {
                "model": "gpt-4o",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "Passed Case",
                        "input": "Test input",
                        "evaluation": create_mock_evaluation_result(
                            passed=True, warning=False, score=0.95
                        ),
                    },
                ],
            },
            {
                "model": "gpt-3.5-turbo",
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
            },
        ]
    ]

    filtered_evaluations, original_counts = filter_failed_evaluations(all_evaluations)

    # Verify original counts
    assert original_counts == (2, 1, 1, 0)

    # Verify filtered results - only second model should be included
    assert len(filtered_evaluations) == 1
    assert len(filtered_evaluations[0]) == 1  # Only one model with failed cases
    assert filtered_evaluations[0][0]["model"] == "gpt-3.5-turbo"
    assert len(filtered_evaluations[0][0]["cases"]) == 1


# --- CLI Capture Mode Flag Tests ---


def test_evals_help_shows_capture_flag() -> None:
    """Test that --capture flag is documented in help."""
    result = runner.invoke(cli, ["evals", "--help"])
    assert result.exit_code == 0
    assert "--capture" in result.output
    assert "capture mode" in result.output.lower()


def test_evals_help_shows_add_context_flag() -> None:
    """Test that --add-context flag is documented in help."""
    result = runner.invoke(cli, ["evals", "--help"])
    assert result.exit_code == 0
    assert "--add-context" in result.output


def test_evals_help_shows_file_flag() -> None:
    """Test that --file flag is documented in help."""
    result = runner.invoke(cli, ["evals", "--help"])
    assert result.exit_code == 0
    assert "--file" in result.output


def test_evals_help_shows_format_flag() -> None:
    """Test that --format flag is documented in help."""
    result = runner.invoke(cli, ["evals", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "txt" in result.output
    assert "md" in result.output
    assert "html" in result.output
