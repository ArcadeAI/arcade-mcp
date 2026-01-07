"""Additional edge case tests for formatters to ensure robustness."""

from arcade_cli.formatters import (
    HtmlFormatter,
    JsonFormatter,
    MarkdownFormatter,
    TextFormatter,
)


class MockEvaluation:
    """Mock EvaluationResult for testing."""

    def __init__(
        self,
        passed: bool = True,
        warning: bool = False,
        score: float = 1.0,
        failure_reason: str | None = None,
        results: list[dict] | None = None,
    ):
        self.passed = passed
        self.warning = warning
        self.score = score
        self.failure_reason = failure_reason
        self.results = results or []


def make_empty_results() -> list[list[dict]]:
    """Create empty evaluation results."""
    return [[{"model": "gpt-4o", "suite_name": "empty_suite", "rubric": "Test", "cases": []}]]


class TestFormatterEdgeCases:
    """Test edge cases that might not be covered elsewhere."""

    def test_empty_results_all_formatters(self) -> None:
        """All formatters should handle empty results gracefully."""
        results = make_empty_results()

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            output = formatter.format(results)
            assert output  # Should produce some output
            assert "0" in output or "Total: 0" in output.lower() or '"total_cases": 0' in output

    def test_failed_only_with_zero_original_total(self) -> None:
        """Should handle original_counts with zero total without crashing."""
        results = make_empty_results()
        # Edge case: original_counts with 0 total (shouldn't happen in practice but should be safe)
        original_counts = (0, 0, 0, 0)

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            # Should not raise ZeroDivisionError
            output = formatter.format(results, failed_only=True, original_counts=original_counts)
            assert output  # Should produce some output

    def test_failed_only_with_empty_results_but_nonzero_original(self) -> None:
        """Should handle case where filtered results are empty but original had cases."""
        results = make_empty_results()
        # All cases were filtered out, but there were originally 5 cases (all passed)
        original_counts = (5, 5, 0, 0)

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            output = formatter.format(results, failed_only=True, original_counts=original_counts)
            assert output
            # Should show original counts
            assert "5" in output

    def test_all_formatters_handle_none_original_counts(self) -> None:
        """All formatters should handle None original_counts gracefully."""
        results = [[{
            "model": "gpt-4o",
            "suite_name": "test",
            "rubric": "Test",
            "cases": [{
                "name": "test_case",
                "input": "test",
                "evaluation": MockEvaluation(passed=False, score=0.0),
            }],
        }]]

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            # Should not crash with None original_counts
            output = formatter.format(results, failed_only=True, original_counts=None)
            assert output

    def test_comparative_with_missing_track_data(self) -> None:
        """Comparative formatters should handle missing track gracefully."""
        # Create comparative result where one track is missing data
        results = [[
            {
                "model": "gpt-4o",
                "suite_name": "Test Suite [track_a]",
                "track_name": "track_a",
                "rubric": None,
                "cases": [{
                    "name": "test_case",
                    "input": "test",
                    "evaluation": MockEvaluation(passed=True, score=1.0),
                }],
            },
            {
                "model": "gpt-4o",
                "suite_name": "Test Suite [track_b]",
                "track_name": "track_b",
                "rubric": None,
                "cases": [],  # Empty cases for this track
            },
        ]]

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            output = formatter.format(results)
            assert output
            # Should mention both tracks
            assert "track_a" in output
            assert "track_b" in output

    def test_html_formatter_escapes_all_special_chars(self) -> None:
        """HTML formatter must escape all special characters to prevent XSS."""
        results = [[{
            "model": "gpt-4o<script>alert('xss')</script>",
            "suite_name": "Suite & Test",
            "rubric": "Test",
            "cases": [{
                "name": "<img src=x onerror=alert(1)>",
                "input": "test' OR '1'='1",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.0,
                    failure_reason="Error: <script>malicious</script>",
                ),
            }],
        }]]

        formatter = HtmlFormatter()
        output = formatter.format(results)

        # Should NOT contain raw script tags or other unescaped HTML
        assert "<script>" not in output
        assert "onerror" not in output or "&" in output  # Should be escaped
        # Should contain escaped versions
        assert "&lt;script&gt;" in output or "&lt;" in output
        assert "&amp;" in output  # & should be escaped

    def test_json_formatter_produces_valid_json_for_all_cases(self) -> None:
        """JSON formatter must always produce valid JSON."""
        import json

        test_cases = [
            make_empty_results(),
            [[{
                "model": "test",
                "suite_name": "test",
                "rubric": None,
                "cases": [{
                    "name": "test",
                    "input": "test with \"quotes\" and \n newlines",
                    "evaluation": MockEvaluation(passed=True),
                }],
            }]],
        ]

        formatter = JsonFormatter()
        for results in test_cases:
            output = formatter.format(results)
            # Should be valid JSON (this will raise if invalid)
            parsed = json.loads(output)
            assert isinstance(parsed, dict)
            assert "summary" in parsed

    def test_formatters_with_suite_name_none(self) -> None:
        """Formatters should handle None suite_name gracefully."""
        results = [[{
            "model": "gpt-4o",
            "suite_name": None,  # Explicitly None
            "rubric": "Test",
            "cases": [{
                "name": "test_case",
                "input": "test",
                "evaluation": MockEvaluation(passed=True),
            }],
        }]]

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            output = formatter.format(results)
            assert output
            # Should use fallback name
            assert "Unnamed Suite" in output or "unnamed" in output.lower()

    def test_pass_rate_calculation_edge_cases(self) -> None:
        """Test pass rate calculation in various edge cases."""
        # Case 1: All passed
        results_all_passed = [[{
            "model": "gpt-4o",
            "suite_name": "test",
            "rubric": "Test",
            "cases": [
                {"name": f"case_{i}", "input": "test", "evaluation": MockEvaluation(passed=True)}
                for i in range(5)
            ],
        }]]

        # Case 2: All failed
        results_all_failed = [[{
            "model": "gpt-4o",
            "suite_name": "test",
            "rubric": "Test",
            "cases": [
                {"name": f"case_{i}", "input": "test", "evaluation": MockEvaluation(passed=False, score=0.0)}
                for i in range(5)
            ],
        }]]

        formatter = JsonFormatter()

        # All passed should show 100% pass rate
        output_passed = formatter.format(results_all_passed)
        assert "100" in output_passed or "100.0" in output_passed

        # All failed should show 0% pass rate
        output_failed = formatter.format(results_all_failed)
        assert '"pass_rate": 0' in output_failed or '"pass_rate": 0.0' in output_failed

    def test_comparative_with_none_evaluation(self) -> None:
        """Comparative formatters should handle None evaluation gracefully."""
        # Simulate a track result with missing evaluation (edge case)
        # This could happen if there was an error during evaluation
        # Note: In real usage, group_comparative_by_case would build the tracks dict
        # from cases, so we need to test this at the formatting level where
        # the track might not have evaluation data
        results = [[
            {
                "model": "gpt-4o",
                "suite_name": "Test Suite [track_a]",
                "track_name": "track_a",
                "rubric": None,
                "cases": [{
                    "name": "test_case",
                    "input": "test",
                    "evaluation": MockEvaluation(passed=True, score=1.0, results=[
                        {
                            "field": "test",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "test",
                            "actual": "test",
                        }
                    ]),
                }],
            },
            # track_b exists but has no cases (edge case where data is missing)
        ]]

        # All formatters should handle missing track data without crashing
        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            output = formatter.format(results)
            # Should produce output
            assert output
            # Should show the track that exists
            assert "track_a" in output or "Track" in output or "test_case" in output

    def test_comparative_with_no_results_in_evaluation(self) -> None:
        """Comparative formatters should handle evaluation without results field."""
        results = [[
            {
                "model": "gpt-4o",
                "suite_name": "Test Suite [track_a]",
                "track_name": "track_a",
                "rubric": None,
                "cases": [{
                    "name": "test_case",
                    "input": "test",
                    "evaluation": MockEvaluation(passed=True, score=1.0, results=[]),  # Empty results
                }],
            },
        ]]

        for formatter_class in [TextFormatter, MarkdownFormatter, HtmlFormatter, JsonFormatter]:
            formatter = formatter_class()
            # Should not crash with empty results
            output = formatter.format(results, show_details=True)
            assert output
