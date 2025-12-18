"""Tests for evaluation result formatters."""

import pytest
from arcade_cli.formatters import (
    FORMATTERS,
    EvalResultFormatter,
    HtmlFormatter,
    MarkdownFormatter,
    TextFormatter,
    get_formatter,
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


def make_mock_results(
    model: str = "gpt-4o",
    cases: list[dict] | None = None,
    suite_name: str = "test_eval_suite",
) -> list[list[dict]]:
    """Create mock evaluation results structure."""
    if cases is None:
        cases = [
            {
                "name": "test_case_1",
                "input": "Test input 1",
                "evaluation": MockEvaluation(passed=True, score=1.0),
            },
            {
                "name": "test_case_2",
                "input": "Test input 2",
                "evaluation": MockEvaluation(passed=False, score=0.5),
            },
        ]

    return [[{"model": model, "suite_name": suite_name, "rubric": "Test Rubric", "cases": cases}]]


class TestGetFormatter:
    """Tests for get_formatter function."""

    def test_get_text_formatter(self) -> None:
        """Should return TextFormatter for 'txt'."""
        formatter = get_formatter("txt")
        assert isinstance(formatter, TextFormatter)

    def test_get_markdown_formatter(self) -> None:
        """Should return MarkdownFormatter for 'md'."""
        formatter = get_formatter("md")
        assert isinstance(formatter, MarkdownFormatter)

    def test_case_insensitive(self) -> None:
        """Should be case-insensitive."""
        assert isinstance(get_formatter("TXT"), TextFormatter)
        assert isinstance(get_formatter("MD"), MarkdownFormatter)

    def test_invalid_format_raises_error(self) -> None:
        """Should raise ValueError for unknown format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            get_formatter("invalid")

    def test_fuzzy_matching_suggests_close_match(self) -> None:
        """Should suggest 'txt' when 'txtt' is provided."""
        with pytest.raises(ValueError) as excinfo:
            get_formatter("txtt")
        assert "Did you mean 'txt'?" in str(excinfo.value)

    def test_fuzzy_matching_suggests_html_for_htm(self) -> None:
        """Should suggest 'html' when 'htm' is provided."""
        with pytest.raises(ValueError) as excinfo:
            get_formatter("htm")
        assert "Did you mean 'html'?" in str(excinfo.value)

    def test_no_suggestion_for_completely_different_format(self) -> None:
        """Should not suggest anything for completely different format names."""
        with pytest.raises(ValueError) as excinfo:
            get_formatter("xyz123")
        assert "Did you mean" not in str(excinfo.value)
        assert "Supported formats:" in str(excinfo.value)


class TestFormattersRegistry:
    """Tests for FORMATTERS registry."""

    def test_registry_has_expected_formats(self) -> None:
        """Registry should contain txt and md formats."""
        assert "txt" in FORMATTERS
        assert "md" in FORMATTERS

    def test_registry_values_are_formatter_classes(self) -> None:
        """All registry values should be EvalResultFormatter subclasses."""
        for name, formatter_cls in FORMATTERS.items():
            assert issubclass(formatter_cls, EvalResultFormatter), f"{name} is not a formatter"


class TestTextFormatter:
    """Tests for TextFormatter."""

    def test_file_extension(self) -> None:
        """File extension should be 'txt'."""
        formatter = TextFormatter()
        assert formatter.file_extension == "txt"

    def test_format_basic_results(self) -> None:
        """Should format basic results correctly."""
        formatter = TextFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        assert "Model: gpt-4o" in output
        assert "PASSED test_case_1" in output
        assert "FAILED test_case_2" in output
        assert "Score: 100.00%" in output
        assert "Score: 50.00%" in output
        assert "Summary" in output
        assert "Total: 2" in output
        assert "Passed: 1" in output
        assert "Failed: 1" in output

    def test_format_with_warnings(self) -> None:
        """Should show warnings correctly."""
        cases = [
            {
                "name": "warned_case",
                "input": "Test",
                "evaluation": MockEvaluation(passed=False, warning=True, score=0.7),
            }
        ]
        formatter = TextFormatter()
        output = formatter.format(make_mock_results(cases=cases))

        assert "WARNED warned_case" in output
        assert "Warnings: 1" in output

    def test_format_with_details(self) -> None:
        """Should include detailed output when show_details=True."""
        cases = [
            {
                "name": "detailed_case",
                "input": "Detailed test input",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=0.9,
                    results=[
                        {
                            "field": "param1",
                            "match": True,
                            "score": 0.5,
                            "weight": 0.5,
                            "expected": "expected_val",
                            "actual": "actual_val",
                            "is_criticized": True,
                        }
                    ],
                ),
            }
        ]
        formatter = TextFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        assert "User Input: Detailed test input" in output
        assert "Details:" in output
        assert "param1:" in output
        assert "Expected: expected_val" in output
        assert "Actual: actual_val" in output

    def test_format_failed_only_with_original_counts(self) -> None:
        """Should show original counts with failed_only mode."""
        formatter = TextFormatter()
        results = make_mock_results()
        output = formatter.format(
            results,
            failed_only=True,
            original_counts=(10, 8, 2, 0),
        )

        assert "Showing only 2 failed evaluation(s)" in output
        assert "Total: 10" in output
        assert "Passed: 8" in output
        assert "Failed: 2" in output


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter."""

    def test_file_extension(self) -> None:
        """File extension should be 'md'."""
        formatter = MarkdownFormatter()
        assert formatter.file_extension == "md"

    def test_format_has_markdown_structure(self) -> None:
        """Should produce valid markdown structure."""
        formatter = MarkdownFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        # Check headers
        assert "# Evaluation Results" in output
        assert "## Summary" in output
        assert "## Results by Model" in output
        assert "### 🤖 gpt-4o" in output

        # Check table markers
        assert "|" in output
        assert "---" in output

    def test_format_summary_table(self) -> None:
        """Should include summary table with stats."""
        formatter = MarkdownFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        assert "| Metric | Count |" in output
        assert "| **Total** | 2 |" in output
        assert "| ✅ Passed | 1 |" in output
        assert "| ❌ Failed | 1 |" in output

    def test_format_results_table(self) -> None:
        """Should include results table per model."""
        formatter = MarkdownFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        assert "| Status | Case | Score |" in output
        assert "| ✅ | test_case_1 | 100.0% |" in output
        assert "| ❌ | test_case_2 | 50.0% |" in output

    def test_format_with_warnings_emoji(self) -> None:
        """Should use warning emoji for warned cases."""
        cases = [
            {
                "name": "warned_case",
                "input": "Test",
                "evaluation": MockEvaluation(passed=False, warning=True, score=0.7),
            }
        ]
        formatter = MarkdownFormatter()
        output = formatter.format(make_mock_results(cases=cases))

        assert "⚠️" in output

    def test_format_with_details_collapsible(self) -> None:
        """Should use collapsible details section."""
        cases = [
            {
                "name": "detailed_case",
                "input": "Test input",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=0.9,
                    results=[
                        {
                            "field": "param1",
                            "match": True,
                            "score": 0.5,
                            "weight": 0.5,
                            "expected": "exp",
                            "actual": "act",
                            "is_criticized": True,
                        }
                    ],
                ),
            }
        ]
        formatter = MarkdownFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        assert "<details>" in output
        assert "<summary>" in output
        assert "</details>" in output
        assert "#### detailed_case" in output

    def test_format_pass_rate(self) -> None:
        """Should include pass rate percentage."""
        formatter = MarkdownFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        assert "**Pass Rate:**" in output
        assert "50.0%" in output

    def test_format_escapes_pipe_in_case_names(self) -> None:
        """Should escape pipe characters in case names for tables."""
        cases = [
            {
                "name": "case|with|pipes",
                "input": "Test",
                "evaluation": MockEvaluation(passed=True, score=1.0),
            }
        ]
        formatter = MarkdownFormatter()
        output = formatter.format(make_mock_results(cases=cases))

        # Should escape pipes
        assert "case\\|with\\|pipes" in output

    def test_format_failed_only_shows_note(self) -> None:
        """Should show note when failed_only mode."""
        formatter = MarkdownFormatter()
        output = formatter.format(
            make_mock_results(),
            failed_only=True,
            original_counts=(10, 8, 2, 0),
        )

        assert "> ⚠️ **Note:**" in output
        assert "failed evaluation(s)" in output

    def test_format_includes_timestamp(self) -> None:
        """Should include generation timestamp."""
        formatter = MarkdownFormatter()
        output = formatter.format(make_mock_results())

        assert "**Generated:**" in output
        assert "UTC" in output


class TestFormatterFailureReason:
    """Tests for handling failure reasons in formatters."""

    def test_text_formatter_shows_failure_reason(self) -> None:
        """TextFormatter should show failure reason."""
        cases = [
            {
                "name": "failed_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.0,
                    failure_reason="Tool not called",
                ),
            }
        ]
        formatter = TextFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        assert "Failure Reason: Tool not called" in output

    def test_markdown_formatter_shows_failure_reason(self) -> None:
        """MarkdownFormatter should show failure reason."""
        cases = [
            {
                "name": "failed_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.0,
                    failure_reason="Tool not called",
                ),
            }
        ]
        formatter = MarkdownFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        assert "**Failure Reason:** Tool not called" in output


class TestFormatterMultipleModels:
    """Tests for handling multiple models."""

    def test_text_formatter_multiple_models(self) -> None:
        """Should show all models in text output."""
        results = [
            [
                {
                    "model": "gpt-4o",
                    "rubric": "Rubric 1",
                    "cases": [
                        {
                            "name": "case1",
                            "input": "Test",
                            "evaluation": MockEvaluation(passed=True),
                        }
                    ],
                },
                {
                    "model": "claude-3-opus",
                    "rubric": "Rubric 2",
                    "cases": [
                        {
                            "name": "case2",
                            "input": "Test",
                            "evaluation": MockEvaluation(passed=False),
                        }
                    ],
                },
            ]
        ]
        formatter = TextFormatter()
        output = formatter.format(results)

        assert "Model: gpt-4o" in output
        assert "Model: claude-3-opus" in output

    def test_markdown_formatter_groups_by_model(self) -> None:
        """Should group results by model in markdown."""
        results = [
            [
                {
                    "model": "gpt-4o",
                    "rubric": "Rubric",
                    "cases": [
                        {"name": "c1", "input": "T", "evaluation": MockEvaluation(passed=True)}
                    ],
                },
                {
                    "model": "gpt-4o",  # Same model
                    "rubric": "Rubric",
                    "cases": [
                        {"name": "c2", "input": "T", "evaluation": MockEvaluation(passed=True)}
                    ],
                },
            ]
        ]
        formatter = MarkdownFormatter()
        output = formatter.format(results)

        # Should only have one header for gpt-4o
        assert output.count("### 🤖 gpt-4o") == 1
        # But both cases under it
        assert "c1" in output
        assert "c2" in output


class TestHtmlFormatter:
    """Tests for HtmlFormatter with color support."""

    def test_file_extension(self) -> None:
        """File extension should be 'html'."""
        formatter = HtmlFormatter()
        assert formatter.file_extension == "html"

    def test_format_produces_valid_html_structure(self) -> None:
        """Should produce valid HTML structure."""
        formatter = HtmlFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "</html>" in output
        assert "<head>" in output
        assert "<body>" in output
        assert "<style>" in output

    def test_format_includes_css_colors(self) -> None:
        """Should include CSS color definitions."""
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results())

        # Check for color variables
        assert "--green:" in output
        assert "--red:" in output
        assert "--yellow:" in output
        assert "--blue:" in output
        assert "--purple:" in output

    def test_format_basic_results_with_status_classes(self) -> None:
        """Should include status classes for styling in summary table."""
        formatter = HtmlFormatter()
        results = make_mock_results()
        # Without details, should show summary table
        output = formatter.format(results, show_details=False)

        assert 'class="passed"' in output
        assert 'class="failed"' in output
        assert 'class="results-table"' in output

    def test_format_shows_suite_name(self) -> None:
        """Should display suite name in the output."""
        formatter = HtmlFormatter()
        results = make_mock_results(suite_name="my_custom_suite")
        output = formatter.format(results)

        # Should show suite section with suite name
        assert 'class="suite-section"' in output
        assert 'class="suite-header"' in output
        assert "my_custom_suite" in output

    def test_format_hides_summary_table_when_details_shown(self) -> None:
        """Should hide summary table when show_details=True to avoid duplication."""
        formatter = HtmlFormatter()
        results = make_mock_results()
        output = formatter.format(results, show_details=True)

        # Summary table should NOT be present
        assert 'class="results-table"' not in output
        # But expandable details should be
        assert 'class="case-expandable' in output

    def test_format_with_warnings_has_warned_class(self) -> None:
        """Should include warned class for warnings."""
        cases = [
            {
                "name": "warned_case",
                "input": "Test",
                "evaluation": MockEvaluation(passed=False, warning=True, score=0.7),
            }
        ]
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(cases=cases))

        assert 'class="warned"' in output
        assert "⚠️ WARNED" in output

    def test_format_escapes_html_special_chars(self) -> None:
        """Should escape HTML special characters."""
        cases = [
            {
                "name": "<script>alert('xss')</script>",
                "input": "Test <b>bold</b>",
                "evaluation": MockEvaluation(passed=True, score=1.0),
            }
        ]
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(cases=cases))

        # Should escape < and > in case name
        assert "&lt;script&gt;" in output
        # Raw script tags should NOT be present (XSS prevention)
        assert "<script>alert" not in output

    def test_format_includes_stats_grid(self) -> None:
        """Should include stats grid with counts."""
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results())

        assert 'class="stats-grid"' in output
        assert 'class="stat-card total"' in output
        assert 'class="stat-card passed"' in output

    def test_format_with_details_includes_collapsible(self) -> None:
        """Should include details/summary for collapsible sections."""
        cases = [
            {
                "name": "detailed_case",
                "input": "Test input",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=0.9,
                    results=[
                        {
                            "field": "param1",
                            "match": True,
                            "score": 0.5,
                            "weight": 0.5,
                            "expected": "exp",
                            "actual": "act",
                            "is_criticized": True,
                        }
                    ],
                ),
            }
        ]
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        # Each case should be individually expandable
        assert '<details class="case-expandable' in output
        assert '<summary class="case-summary">' in output
        assert "</details>" in output
        assert "detailed_case" in output

    def test_format_each_case_is_individually_expandable(self) -> None:
        """Each case result should be in its own collapsible element."""
        cases = [
            {"name": "case_1", "input": "T1", "evaluation": MockEvaluation(passed=True)},
            {"name": "case_2", "input": "T2", "evaluation": MockEvaluation(passed=False)},
            {
                "name": "case_3",
                "input": "T3",
                "evaluation": MockEvaluation(passed=False, warning=True),
            },
        ]
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        # Should have 3 separate expandable case elements
        assert output.count('<details class="case-expandable') == 3
        assert output.count("</details>") >= 3

    def test_format_shows_expand_hint_in_details_mode(self) -> None:
        """Should show hint about clicking to expand when details mode is on."""
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(), show_details=True)

        assert "expand-hint" in output
        assert "Click on any case below to expand details" in output

    def test_format_no_expand_hint_without_details(self) -> None:
        """Should not show expand hint when details mode is off."""
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(), show_details=False)

        # The hint text should not be in the output (even though CSS class may be defined)
        assert "Click on any case below to expand details" not in output

    def test_format_failure_reason_styled(self) -> None:
        """Should style failure reasons prominently."""
        cases = [
            {
                "name": "failed_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.0,
                    failure_reason="Tool not called",
                ),
            }
        ]
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results(cases=cases), show_details=True)

        assert "failure-reason" in output
        assert "Tool not called" in output

    def test_format_responsive_css(self) -> None:
        """Should include responsive CSS media query."""
        formatter = HtmlFormatter()
        output = formatter.format(make_mock_results())

        assert "@media" in output

    def test_get_formatter_returns_html(self) -> None:
        """get_formatter should return HtmlFormatter for 'html'."""
        formatter = get_formatter("html")
        assert isinstance(formatter, HtmlFormatter)

    def test_registry_includes_html(self) -> None:
        """FORMATTERS registry should include html."""
        assert "html" in FORMATTERS
        assert FORMATTERS["html"] is HtmlFormatter


class TestSharedUtilities:
    """Tests for shared utility functions in base.py."""

    def test_truncate_field_value_within_limit(self) -> None:
        """Should not truncate values within limit."""
        from arcade_cli.formatters.base import truncate_field_value

        short_value = "short string"
        result = truncate_field_value(short_value)
        assert result == short_value

    def test_truncate_field_value_exceeds_limit(self) -> None:
        """Should truncate values exceeding limit."""
        from arcade_cli.formatters.base import truncate_field_value

        long_value = "x" * 100
        result = truncate_field_value(long_value, max_length=60)
        assert len(result) == 60
        assert result.endswith("...")

    def test_truncate_field_value_custom_limit(self) -> None:
        """Should respect custom max_length."""
        from arcade_cli.formatters.base import truncate_field_value

        value = "hello world"
        result = truncate_field_value(value, max_length=8)
        assert len(result) == 8
        assert result == "hello..."

    def test_truncate_field_value_at_boundary(self) -> None:
        """Should handle exactly at boundary."""
        from arcade_cli.formatters.base import truncate_field_value

        value = "x" * 60
        result = truncate_field_value(value, max_length=60)
        assert result == value  # Exactly at limit, no truncation

    def test_group_results_by_model_basic(self) -> None:
        """Should group results by model and suite."""
        from arcade_cli.formatters.base import group_results_by_model

        results = make_mock_results(model="gpt-4o", suite_name="test_suite")
        model_groups, passed, failed, warned, total = group_results_by_model(results)

        assert "gpt-4o" in model_groups
        assert "test_suite" in model_groups["gpt-4o"]
        assert total == 2  # Two cases from make_mock_results

    def test_group_results_by_model_multiple_models(self) -> None:
        """Should correctly separate multiple models."""
        from arcade_cli.formatters.base import group_results_by_model

        results = [
            [
                {
                    "model": "gpt-4o",
                    "suite_name": "suite_a",
                    "cases": [{"name": "c1", "evaluation": MockEvaluation(passed=True)}],
                },
                {
                    "model": "claude-3",
                    "suite_name": "suite_b",
                    "cases": [{"name": "c2", "evaluation": MockEvaluation(passed=False)}],
                },
            ]
        ]
        model_groups, passed, failed, warned, total = group_results_by_model(results)

        assert len(model_groups) == 2
        assert "gpt-4o" in model_groups
        assert "claude-3" in model_groups
        assert passed == 1
        assert failed == 1
        assert total == 2

    def test_group_results_by_model_suite_name_fallback(self) -> None:
        """Should fall back to 'Unnamed Suite' when suite_name is missing."""
        from arcade_cli.formatters.base import group_results_by_model

        results = [
            [
                {
                    "model": "gpt-4o",
                    # No suite_name, no rubric
                    "cases": [{"name": "c1", "evaluation": MockEvaluation(passed=True)}],
                }
            ]
        ]
        model_groups, _, _, _, _ = group_results_by_model(results)

        assert "Unnamed Suite" in model_groups["gpt-4o"]

    def test_group_results_counts_warnings(self) -> None:
        """Should correctly count warnings."""
        from arcade_cli.formatters.base import group_results_by_model

        results = [
            [
                {
                    "model": "gpt-4o",
                    "suite_name": "suite",
                    "cases": [
                        {"name": "c1", "evaluation": MockEvaluation(passed=True, warning=False)},
                        {"name": "c2", "evaluation": MockEvaluation(passed=False, warning=True)},
                        {"name": "c3", "evaluation": MockEvaluation(passed=False, warning=False)},
                    ],
                }
            ]
        ]
        _, passed, failed, warned, total = group_results_by_model(results)

        assert passed == 1
        assert warned == 1
        assert failed == 1
        assert total == 3
