"""Tests for evaluation result formatters."""

import json

import pytest
from arcade_cli.formatters import (
    FORMATTERS,
    EvalResultFormatter,
    HtmlFormatter,
    JsonFormatter,
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
        """Should show all models in multi-model output."""
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

        # Multi-model format shows models in summary table
        assert "MULTI-MODEL EVALUATION RESULTS" in output
        assert "gpt-4o" in output
        assert "claude-3-opus" in output

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


# =============================================================================
# COMPARATIVE EVALUATION TESTS
# =============================================================================


def make_comparative_results(
    model: str = "gpt-4o",
    suite_name: str = "Test Suite",
    track_cases: dict[str, list[dict]] | None = None,
) -> list[list[dict]]:
    """Create mock comparative evaluation results structure.

    Args:
        model: The model name.
        suite_name: Base suite name (will have track suffix added).
        track_cases: Dict of track_name -> list of cases. If None, uses default.

    Returns:
        Results in the format produced by _convert_comparative_to_cli_format.
    """
    if track_cases is None:
        # Default: two tracks, same case
        track_cases = {
            "track_a": [
                {
                    "name": "create_issue",
                    "input": "Create a bug issue",
                    "evaluation": MockEvaluation(
                        passed=True,
                        score=1.0,
                        results=[
                            {
                                "field": "title",
                                "match": True,
                                "score": 1.0,
                                "weight": 1.0,
                                "expected": "Bug Issue",
                                "actual": "Bug Issue",
                                "is_criticized": True,
                            },
                            {
                                "field": "description",
                                "match": True,
                                "score": 1.0,
                                "weight": 1.0,
                                "expected": "A bug",
                                "actual": "A bug",
                                "is_criticized": True,
                            },
                        ],
                    ),
                }
            ],
            "track_b": [
                {
                    "name": "create_issue",
                    "input": "Create a bug issue",
                    "evaluation": MockEvaluation(
                        passed=True,
                        score=0.9,
                        results=[
                            {
                                "field": "title",
                                "match": True,
                                "score": 1.0,
                                "weight": 1.0,
                                "expected": "Bug Issue",
                                "actual": "Bug Issue",
                                "is_criticized": True,
                            },
                            {
                                "field": "description",
                                "match": False,
                                "score": 0.8,
                                "weight": 1.0,
                                "expected": "A bug",
                                "actual": "A bug report",
                                "is_criticized": True,
                            },
                        ],
                    ),
                }
            ],
        }

    # Build results like _convert_comparative_to_cli_format produces
    results: list[list[dict]] = []
    for track_name, cases in track_cases.items():
        results.append([
            {
                "model": model,
                "suite_name": f"{suite_name} [{track_name}]",
                "track_name": track_name,
                "rubric": None,
                "cases": cases,
            }
        ])

    return results


# =============================================================================
# REALISTIC MCP SERVER DEFINITIONS FOR COMPARATIVE TESTS
# =============================================================================

# Simulates 3 MCP servers that provide Linear integration with different implementations:
# 1. linear_official - Official Linear MCP server (uses Linear's native tool names)
# 2. linear_arcade   - Arcade's Linear toolkit (uses Arcade naming conventions)
# 3. linear_community - Community/custom implementation (alternative naming)

MCP_SERVER_LINEAR_OFFICIAL: dict = {
    "name": "linear_official",
    "description": "Official Linear MCP Server",
    "tools": [
        {
            "name": "linear_create_issue",
            "description": "Create a new issue in Linear",
            "parameters": {
                "title": {"type": "string", "required": True},
                "description": {"type": "string", "required": False},
                "team_id": {"type": "string", "required": True},
                "priority": {"type": "integer", "required": False, "enum": [0, 1, 2, 3, 4]},
                "assignee_id": {"type": "string", "required": False},
            },
        },
        {
            "name": "linear_update_issue",
            "description": "Update an existing issue",
            "parameters": {
                "issue_id": {"type": "string", "required": True},
                "title": {"type": "string", "required": False},
                "state_id": {"type": "string", "required": False},
                "priority": {"type": "integer", "required": False},
            },
        },
        {
            "name": "linear_list_issues",
            "description": "List issues with filters",
            "parameters": {
                "team_id": {"type": "string", "required": False},
                "state": {"type": "string", "required": False},
                "assignee_id": {"type": "string", "required": False},
                "limit": {"type": "integer", "required": False, "default": 50},
            },
        },
    ],
}

MCP_SERVER_LINEAR_ARCADE: dict = {
    "name": "linear_arcade",
    "description": "Arcade Linear Toolkit",
    "tools": [
        {
            "name": "Linear_CreateIssue",
            "description": "Create a new issue in Linear workspace",
            "parameters": {
                "title": {"type": "string", "required": True},
                "description": {"type": "string", "required": False},
                "team_key": {"type": "string", "required": True},
                "priority_level": {
                    "type": "string",
                    "required": False,
                    "enum": ["urgent", "high", "medium", "low", "none"],
                },
                "assignee_email": {"type": "string", "required": False},
            },
        },
        {
            "name": "Linear_UpdateIssue",
            "description": "Update an existing Linear issue",
            "parameters": {
                "issue_identifier": {"type": "string", "required": True},
                "title": {"type": "string", "required": False},
                "state_name": {"type": "string", "required": False},
                "priority_level": {"type": "string", "required": False},
            },
        },
        {
            "name": "Linear_ListIssues",
            "description": "Search and list issues",
            "parameters": {
                "team_key": {"type": "string", "required": False},
                "status": {"type": "string", "required": False},
                "assignee_email": {"type": "string", "required": False},
                "max_results": {"type": "integer", "required": False, "default": 25},
            },
        },
    ],
}

MCP_SERVER_LINEAR_COMMUNITY: dict = {
    "name": "linear_community",
    "description": "Community Linear Integration",
    "tools": [
        {
            "name": "createLinearIssue",
            "description": "Creates an issue in Linear",
            "parameters": {
                "name": {"type": "string", "required": True},  # Different param name!
                "body": {"type": "string", "required": False},  # Different param name!
                "team": {"type": "string", "required": True},
                "urgency": {
                    "type": "string",
                    "required": False,
                    "enum": ["critical", "high", "normal", "low"],
                },
                "owner": {"type": "string", "required": False},
            },
        },
        {
            "name": "updateLinearIssue",
            "description": "Updates a Linear issue",
            "parameters": {
                "id": {"type": "string", "required": True},
                "name": {"type": "string", "required": False},
                "status": {"type": "string", "required": False},
                "urgency": {"type": "string", "required": False},
            },
        },
        {
            "name": "searchLinearIssues",
            "description": "Search for issues",
            "parameters": {
                "team": {"type": "string", "required": False},
                "status": {"type": "string", "required": False},
                "owner": {"type": "string", "required": False},
                "count": {"type": "integer", "required": False, "default": 20},
            },
        },
    ],
}


def make_mcp_server_comparative_results(
    model: str = "gpt-4o",
    suite_name: str = "Linear MCP Comparison",
) -> list[list[dict]]:
    """Create comparative results simulating 3 different MCP servers for Linear.

    This represents a realistic use case: comparing how well an LLM works with
    different MCP server implementations that serve the same purpose.
    """
    # Each server has different tool names and parameter conventions
    track_cases = {
        # Official Linear MCP - uses integer priority, state_id
        "linear_official": [
            {
                "name": "create_bug_issue",
                "input": "Create a high priority bug: 'API timeout errors'",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=1.0,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "linear_create_issue",
                            "actual": "linear_create_issue",
                            "is_criticized": True,
                        },
                        {
                            "field": "title",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "API timeout errors",
                            "actual": "API timeout errors",
                            "is_criticized": True,
                        },
                        {
                            "field": "priority",
                            "match": True,
                            "score": 1.0,
                            "weight": 0.8,
                            "expected": 1,  # integer priority
                            "actual": 1,
                            "is_criticized": True,
                        },
                    ],
                ),
            },
            {
                "name": "update_issue_status",
                "input": "Mark issue LIN-123 as done",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=1.0,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "linear_update_issue",
                            "actual": "linear_update_issue",
                            "is_criticized": True,
                        },
                        {
                            "field": "issue_id",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "LIN-123",
                            "actual": "LIN-123",
                            "is_criticized": True,
                        },
                    ],
                ),
            },
        ],
        # Arcade Linear - uses string priority_level, state_name
        "linear_arcade": [
            {
                "name": "create_bug_issue",
                "input": "Create a high priority bug: 'API timeout errors'",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=0.95,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "Linear_CreateIssue",
                            "actual": "Linear_CreateIssue",
                            "is_criticized": True,
                        },
                        {
                            "field": "title",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "API timeout errors",
                            "actual": "API timeout errors",
                            "is_criticized": True,
                        },
                        {
                            "field": "priority_level",
                            "match": True,
                            "score": 0.8,
                            "weight": 0.8,
                            "expected": "high",  # string priority
                            "actual": "high",
                            "is_criticized": True,
                        },
                    ],
                ),
            },
            {
                "name": "update_issue_status",
                "input": "Mark issue LIN-123 as done",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=1.0,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "Linear_UpdateIssue",
                            "actual": "Linear_UpdateIssue",
                            "is_criticized": True,
                        },
                        {
                            "field": "issue_identifier",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "LIN-123",
                            "actual": "LIN-123",
                            "is_criticized": True,
                        },
                    ],
                ),
            },
        ],
        # Community Linear - uses name/body instead of title/description
        "linear_community": [
            {
                "name": "create_bug_issue",
                "input": "Create a high priority bug: 'API timeout errors'",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.7,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "createLinearIssue",
                            "actual": "createLinearIssue",
                            "is_criticized": True,
                        },
                        {
                            "field": "name",  # Different field name!
                            "match": False,
                            "score": 0.5,
                            "weight": 1.0,
                            "expected": "API timeout errors",
                            "actual": "Bug: API timeout",  # LLM confused by param name
                            "is_criticized": True,
                        },
                        {
                            "field": "urgency",
                            "match": False,
                            "score": 0.0,
                            "weight": 0.8,
                            "expected": "high",
                            "actual": "critical",  # Wrong mapping
                            "is_criticized": True,
                        },
                    ],
                ),
            },
            {
                "name": "update_issue_status",
                "input": "Mark issue LIN-123 as done",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=0.9,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "updateLinearIssue",
                            "actual": "updateLinearIssue",
                            "is_criticized": True,
                        },
                        {
                            "field": "id",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "LIN-123",
                            "actual": "LIN-123",
                            "is_criticized": True,
                        },
                        {
                            "field": "status",
                            "match": False,
                            "score": 0.8,
                            "weight": 0.5,
                            "expected": "done",
                            "actual": "completed",  # Slight mismatch
                            "is_criticized": True,
                        },
                    ],
                ),
            },
        ],
    }

    # Build results
    results: list[list[dict]] = []
    for track_name, cases in track_cases.items():
        results.append([
            {
                "model": model,
                "suite_name": f"{suite_name} [{track_name}]",
                "track_name": track_name,
                "rubric": None,
                "cases": cases,
            }
        ])

    return results


class TestComparativeHelpers:
    """Tests for comparative evaluation helper functions."""

    def test_is_comparative_result_true(self) -> None:
        """Should return True for results with track_name."""
        from arcade_cli.formatters.base import is_comparative_result

        results = make_comparative_results()
        assert is_comparative_result(results) is True

    def test_is_comparative_result_false(self) -> None:
        """Should return False for regular results without track_name."""
        from arcade_cli.formatters.base import is_comparative_result

        results = make_mock_results()
        assert is_comparative_result(results) is False

    def test_extract_base_suite_name(self) -> None:
        """Should extract base suite name by removing track suffix."""
        from arcade_cli.formatters.base import _extract_base_suite_name

        assert _extract_base_suite_name("My Suite [track_a]", "track_a") == "My Suite"
        assert _extract_base_suite_name("Suite [foo]", "foo") == "Suite"
        # Should not change if suffix doesn't match
        assert _extract_base_suite_name("Suite [other]", "track_a") == "Suite [other]"

    def test_group_comparative_by_case(self) -> None:
        """Should group comparative results by model, suite, and case."""
        from arcade_cli.formatters.base import group_comparative_by_case

        results = make_comparative_results()
        groups, passed, failed, warned, total, suite_track_order = group_comparative_by_case(
            results
        )

        # Check structure
        assert "gpt-4o" in groups
        assert "Test Suite" in groups["gpt-4o"]
        assert "create_issue" in groups["gpt-4o"]["Test Suite"]

        # Check case data
        case_data = groups["gpt-4o"]["Test Suite"]["create_issue"]
        assert "tracks" in case_data
        assert "track_a" in case_data["tracks"]
        assert "track_b" in case_data["tracks"]
        assert case_data["input"] == "Create a bug issue"

        # Check stats (2 cases total: 1 per track)
        assert total == 2
        assert passed == 2
        assert failed == 0

        # Check track order per suite
        assert "Test Suite" in suite_track_order
        assert suite_track_order["Test Suite"] == ["track_a", "track_b"]

    def test_compute_track_differences(self) -> None:
        """Should compute which fields differ from baseline."""
        from arcade_cli.formatters.base import compute_track_differences, group_comparative_by_case

        results = make_comparative_results()
        groups, _, _, _, _, suite_track_order = group_comparative_by_case(results)

        case_data = groups["gpt-4o"]["Test Suite"]["create_issue"]
        track_order = suite_track_order["Test Suite"]
        differences = compute_track_differences(case_data, track_order)

        # track_a is baseline, so no differences for it
        assert "track_a" not in differences

        # track_b should have 'description' as different
        assert "track_b" in differences
        assert "description" in differences["track_b"]
        assert "title" not in differences["track_b"]  # title matched


class TestComparativeMarkdownFormatter:
    """Tests for comparative markdown formatting."""

    def test_comparative_format_header(self) -> None:
        """Should have comparative header."""
        formatter = MarkdownFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "# Comparative Evaluation Results" in output
        assert "Tracks compared:" in output
        assert "`track_a`" in output
        assert "`track_b`" in output

    def test_comparative_format_suite_tracks(self) -> None:
        """Should show suite-specific tracks."""
        formatter = MarkdownFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        # Suite should show its tracks
        assert "**Tracks:** `track_a`, `track_b`" in output

    def test_comparative_format_case_comparison_table(self) -> None:
        """Should show case comparison table with all tracks."""
        formatter = MarkdownFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "##### Case: create_issue" in output
        assert "| Track | Status | Score | Differences |" in output
        assert "`track_a`" in output
        assert "`track_b`" in output
        assert "*(baseline)*" in output

    def test_comparative_format_shows_differences(self) -> None:
        """Should show which fields differ between tracks."""
        formatter = MarkdownFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        # track_b should show description as different
        assert "`description`" in output

    def test_comparative_format_with_details(self) -> None:
        """Should include collapsible details per track."""
        formatter = MarkdownFormatter()
        results = make_comparative_results()
        output = formatter.format(results, show_details=True)

        assert "<details>" in output
        assert "<summary>" in output
        assert "track_a" in output
        assert "track_b" in output


class TestComparativeTextFormatter:
    """Tests for comparative text formatting."""

    def test_comparative_format_header(self) -> None:
        """Should have comparative header."""
        formatter = TextFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "COMPARATIVE EVALUATION RESULTS" in output
        assert "track_a vs track_b" in output

    def test_comparative_format_ascii_table(self) -> None:
        """Should show ASCII comparison table."""
        formatter = TextFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "COMPARISON" in output
        assert "Track" in output
        assert "Status" in output
        assert "Score" in output
        assert "track_a" in output
        assert "track_b" in output

    def test_comparative_format_with_details(self) -> None:
        """Should include per-track details."""
        formatter = TextFormatter()
        results = make_comparative_results()
        output = formatter.format(results, show_details=True)

        assert "[track_a] Details:" in output
        assert "[track_b] Details:" in output


class TestMcpServerComparison:
    """Tests for realistic MCP server comparison scenarios."""

    def test_mcp_server_definitions_exist(self) -> None:
        """Should have 3 MCP server definitions with tools."""
        assert MCP_SERVER_LINEAR_OFFICIAL["name"] == "linear_official"
        assert MCP_SERVER_LINEAR_ARCADE["name"] == "linear_arcade"
        assert MCP_SERVER_LINEAR_COMMUNITY["name"] == "linear_community"

        # Each should have at least 3 tools
        assert len(MCP_SERVER_LINEAR_OFFICIAL["tools"]) >= 3
        assert len(MCP_SERVER_LINEAR_ARCADE["tools"]) >= 3
        assert len(MCP_SERVER_LINEAR_COMMUNITY["tools"]) >= 3

    def test_mcp_servers_have_different_tool_names(self) -> None:
        """Different MCP servers should have different tool naming conventions."""
        official_tools = [t["name"] for t in MCP_SERVER_LINEAR_OFFICIAL["tools"]]
        arcade_tools = [t["name"] for t in MCP_SERVER_LINEAR_ARCADE["tools"]]
        community_tools = [t["name"] for t in MCP_SERVER_LINEAR_COMMUNITY["tools"]]

        # Verify different naming conventions
        assert "linear_create_issue" in official_tools  # snake_case with prefix
        assert "Linear_CreateIssue" in arcade_tools  # PascalCase with prefix
        assert "createLinearIssue" in community_tools  # camelCase

    def test_mcp_servers_have_different_param_names(self) -> None:
        """Different MCP servers may use different parameter names for same concept."""
        # Get create issue tool from each server
        official_create = next(
            t for t in MCP_SERVER_LINEAR_OFFICIAL["tools"] if "create" in t["name"].lower()
        )
        arcade_create = next(
            t for t in MCP_SERVER_LINEAR_ARCADE["tools"] if "create" in t["name"].lower()
        )
        community_create = next(
            t for t in MCP_SERVER_LINEAR_COMMUNITY["tools"] if "create" in t["name"].lower()
        )

        # Official uses "title", Arcade uses "title", Community uses "name"
        assert "title" in official_create["parameters"]
        assert "title" in arcade_create["parameters"]
        assert "name" in community_create["parameters"]  # Different!

        # Different priority representations
        assert "priority" in official_create["parameters"]  # integer
        assert "priority_level" in arcade_create["parameters"]  # string enum
        assert "urgency" in community_create["parameters"]  # different name entirely

    def test_mcp_server_comparative_results_structure(self) -> None:
        """Should create proper comparative results from 3 MCP servers."""
        from arcade_cli.formatters.base import group_comparative_by_case

        results = make_mcp_server_comparative_results()
        groups, passed, failed, warned, total, suite_track_order = group_comparative_by_case(
            results
        )

        # Should have 3 tracks (one per MCP server)
        assert "Linear MCP Comparison" in suite_track_order
        tracks = suite_track_order["Linear MCP Comparison"]
        assert len(tracks) == 3
        assert "linear_official" in tracks
        assert "linear_arcade" in tracks
        assert "linear_community" in tracks

        # Should have 6 total cases (2 cases × 3 servers)
        assert total == 6

        # Community server has failures (score-based, not all passed)
        assert passed == 5
        assert failed == 1

    def test_mcp_server_markdown_shows_all_servers(self) -> None:
        """Markdown output should show all 3 MCP servers being compared."""
        formatter = MarkdownFormatter()
        results = make_mcp_server_comparative_results()
        output = formatter.format(results)

        # Should show all three servers
        assert "`linear_official`" in output
        assert "`linear_arcade`" in output
        assert "`linear_community`" in output

        # Should show cases
        assert "create_bug_issue" in output
        assert "update_issue_status" in output

        # Should show the failed community server
        assert "❌" in output  # Failed status for community

    def test_mcp_server_comparison_shows_differences(self) -> None:
        """Should highlight differences between MCP server implementations."""
        from arcade_cli.formatters.base import compute_track_differences, group_comparative_by_case

        results = make_mcp_server_comparative_results()
        groups, _, _, _, _, suite_track_order = group_comparative_by_case(results)

        suite = "Linear MCP Comparison"
        case_data = groups["gpt-4o"][suite]["create_bug_issue"]
        track_order = suite_track_order[suite]

        differences = compute_track_differences(case_data, track_order)

        # linear_official is baseline (first), so not in differences
        assert "linear_official" not in differences

        # linear_arcade uses priority_level instead of priority
        # (different field name = different from baseline)
        assert "linear_arcade" in differences

        # linear_community has name/urgency mismatches
        assert "linear_community" in differences
        assert "name" in differences["linear_community"]

    def test_mcp_server_text_format_shows_servers(self) -> None:
        """Text output should properly display all MCP servers."""
        formatter = TextFormatter()
        results = make_mcp_server_comparative_results()
        output = formatter.format(results)

        assert "linear_official" in output
        assert "linear_arcade" in output
        assert "linear_community" in output
        assert "PASSED" in output
        assert "FAILED" in output

    def test_mcp_server_html_format_shows_servers(self) -> None:
        """HTML output should display all MCP servers with proper styling."""
        formatter = HtmlFormatter()
        results = make_mcp_server_comparative_results()
        output = formatter.format(results)

        assert "linear_official" in output
        assert "linear_arcade" in output
        assert "linear_community" in output
        assert "track-badge" in output
        assert "diff-field" in output  # Should show differences


class TestComparativeHtmlFormatter:
    """Tests for comparative HTML formatting."""

    def test_comparative_format_structure(self) -> None:
        """Should have comparative HTML structure."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "Comparative Evaluation Results" in output
        assert "comparative-badge" in output
        assert "COMPARATIVE" in output

    def test_comparative_format_track_badges(self) -> None:
        """Should show track badges."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "track-badge" in output
        assert "track_a" in output
        assert "track_b" in output

    def test_comparative_format_comparison_table(self) -> None:
        """Should have comparison table."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "comparison-table" in output
        assert "baseline" in output

    def test_comparative_format_diff_fields(self) -> None:
        """Should highlight different fields."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        assert "diff-field" in output
        assert "description" in output

    def test_comparative_format_with_details_has_tabs(self) -> None:
        """Should include tabbed details per track."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results, show_details=True)

        assert "track-tabs" in output
        assert "track-tab" in output
        assert "track-panel" in output

    def test_comparative_format_has_tab_script(self) -> None:
        """Should include JavaScript for tab switching."""
        formatter = HtmlFormatter()
        results = make_comparative_results()
        output = formatter.format(results, show_details=True)

        assert "<script>" in output
        assert "track-tab" in output


# =============================================================================
# JSON FORMATTER TESTS
# =============================================================================


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    def test_file_extension(self) -> None:
        """Should return 'json' as file extension."""
        formatter = JsonFormatter()
        assert formatter.file_extension == "json"

    def test_format_produces_valid_json(self) -> None:
        """Should produce valid JSON output."""
        formatter = JsonFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        # Should be valid JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_format_includes_summary(self) -> None:
        """Should include summary statistics."""
        formatter = JsonFormatter()
        results = make_mock_results()
        output = formatter.format(results)

        parsed = json.loads(output)
        assert "summary" in parsed
        assert "total_cases" in parsed["summary"]
        assert "passed" in parsed["summary"]
        assert "failed" in parsed["summary"]
        assert "pass_rate" in parsed["summary"]

    def test_format_includes_model_results(self) -> None:
        """Should include model results structure."""
        formatter = JsonFormatter()
        results = make_mock_results(model="gpt-4o")
        output = formatter.format(results)

        parsed = json.loads(output)
        assert "models" in parsed
        assert "gpt-4o" in parsed["models"]

    def test_format_includes_suite_name(self) -> None:
        """Should include suite name."""
        formatter = JsonFormatter()
        results = make_mock_results(suite_name="MyTestSuite")
        output = formatter.format(results)

        parsed = json.loads(output)
        assert "MyTestSuite" in parsed["models"]["gpt-4o"]["suites"]

    def test_format_includes_case_data(self) -> None:
        """Should include case data."""
        formatter = JsonFormatter()
        cases = [
            {
                "name": "my_test_case",
                "input": "Test user input",
                "evaluation": MockEvaluation(passed=True, score=0.95),
            }
        ]
        results = make_mock_results(cases=cases)
        output = formatter.format(results)

        parsed = json.loads(output)
        suite_data = parsed["models"]["gpt-4o"]["suites"]["test_eval_suite"]
        assert "cases" in suite_data

    def test_format_with_details_includes_critic_results(self) -> None:
        """Should include critic details when show_details=True."""
        formatter = JsonFormatter()
        cases = [
            {
                "name": "detailed_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=1.0,
                    results=[
                        {
                            "field": "tool_selection",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "create_issue",
                            "actual": "create_issue",
                        }
                    ],
                ),
            }
        ]
        results = make_mock_results(cases=cases)
        output = formatter.format(results, show_details=True)

        parsed = json.loads(output)
        # Find the case data
        suite_data = parsed["models"]["gpt-4o"]["suites"]["test_eval_suite"]
        # In comparative mode, cases are in a dict
        if isinstance(suite_data.get("cases"), dict):
            case_data = suite_data["cases"]["detailed_case"]["tracks"]["default"]
        else:
            case_data = suite_data["cases"][0]

        assert "details" in case_data
        assert case_data["details"][0]["field"] == "tool_selection"

    def test_format_without_details_excludes_critic_results(self) -> None:
        """Should not include critic details when show_details=False."""
        formatter = JsonFormatter()
        cases = [
            {
                "name": "no_details_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=True,
                    score=1.0,
                    results=[
                        {
                            "field": "test",
                            "match": True,
                            "score": 1.0,
                            "weight": 1.0,
                            "expected": "x",
                            "actual": "x",
                        }
                    ],
                ),
            }
        ]
        results = make_mock_results(cases=cases)
        output = formatter.format(results, show_details=False)

        parsed = json.loads(output)
        suite_data = parsed["models"]["gpt-4o"]["suites"]["test_eval_suite"]
        if isinstance(suite_data.get("cases"), dict):
            case_data = suite_data["cases"]["no_details_case"]["tracks"]["default"]
        else:
            case_data = suite_data["cases"][0]

        assert "details" not in case_data

    def test_format_includes_failure_reason(self) -> None:
        """Should include failure reason when present."""
        formatter = JsonFormatter()
        cases = [
            {
                "name": "failed_case",
                "input": "Test",
                "evaluation": MockEvaluation(
                    passed=False,
                    score=0.0,
                    failure_reason="Tool selection mismatch",
                ),
            }
        ]
        results = make_mock_results(cases=cases)
        output = formatter.format(results)

        parsed = json.loads(output)
        suite_data = parsed["models"]["gpt-4o"]["suites"]["test_eval_suite"]
        if isinstance(suite_data.get("cases"), dict):
            case_data = suite_data["cases"]["failed_case"]["tracks"]["default"]
        else:
            case_data = suite_data["cases"][0]

        assert case_data["status"] == "failed"
        assert case_data["failure_reason"] == "Tool selection mismatch"

    def test_get_formatter_returns_json(self) -> None:
        """Should return JsonFormatter for 'json' format."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JsonFormatter)

    def test_registry_includes_json(self) -> None:
        """Should have 'json' in FORMATTERS registry."""
        assert "json" in FORMATTERS
        assert FORMATTERS["json"] == JsonFormatter


class TestComparativeJsonFormatter:
    """Tests for JSON formatter with comparative evaluation results."""

    def test_comparative_format_includes_tracks(self) -> None:
        """Should include track information for comparative results."""
        formatter = JsonFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        parsed = json.loads(output)
        assert parsed["type"] == "comparative_evaluation"
        assert "tracks" in parsed

    def test_comparative_format_groups_by_case(self) -> None:
        """Should group results by case name across tracks."""
        formatter = JsonFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        parsed = json.loads(output)
        # Find the suite
        suite_data = list(parsed["models"].values())[0]["suites"]
        suite = list(suite_data.values())[0]

        # Cases should be grouped
        assert "cases" in suite
        assert isinstance(suite["cases"], dict)

    def test_comparative_format_includes_per_track_results(self) -> None:
        """Should include results for each track within a case."""
        formatter = JsonFormatter()
        results = make_comparative_results()
        output = formatter.format(results)

        parsed = json.loads(output)
        suite_data = list(parsed["models"].values())[0]["suites"]
        suite = list(suite_data.values())[0]
        case = list(suite["cases"].values())[0]

        assert "tracks" in case
        # Should have track1 and track2
        assert len(case["tracks"]) == 2

    def test_comparative_format_with_details(self) -> None:
        """Should include detailed results per track when show_details=True."""
        formatter = JsonFormatter()
        results = make_comparative_results()
        output = formatter.format(results, show_details=True)

        parsed = json.loads(output)
        suite_data = list(parsed["models"].values())[0]["suites"]
        suite = list(suite_data.values())[0]
        case = list(suite["cases"].values())[0]

        # Each track should have details
        for track_name, track_data in case["tracks"].items():
            assert "details" in track_data


# =============================================================================
# MULTI-MODEL EVALUATION FORMATTING TESTS
# =============================================================================


def make_multi_model_results() -> list[list[dict]]:
    """Create mock multi-model evaluation results."""
    return [
        # Model 1 results
        [
            {
                "model": "gpt-4o",
                "suite_name": "TestSuite",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "case_1",
                        "input": "Test input 1",
                        "evaluation": MockEvaluation(passed=True, score=1.0),
                    },
                    {
                        "name": "case_2",
                        "input": "Test input 2",
                        "evaluation": MockEvaluation(passed=False, score=0.5),
                    },
                ],
            }
        ],
        # Model 2 results
        [
            {
                "model": "gpt-4-turbo",
                "suite_name": "TestSuite",
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "case_1",
                        "input": "Test input 1",
                        "evaluation": MockEvaluation(passed=True, score=0.95),
                    },
                    {
                        "name": "case_2",
                        "input": "Test input 2",
                        "evaluation": MockEvaluation(passed=True, score=0.85),
                    },
                ],
            }
        ],
    ]


class TestMultiModelEvalHelpers:
    """Tests for multi-model eval helper functions."""

    def test_is_multi_model_eval_true(self) -> None:
        """Should detect multiple models."""
        from arcade_cli.formatters.base import is_multi_model_eval

        results = make_multi_model_results()
        assert is_multi_model_eval(results) is True

    def test_is_multi_model_eval_false(self) -> None:
        """Should detect single model."""
        from arcade_cli.formatters.base import is_multi_model_eval

        results = make_mock_results(model="gpt-4o")
        assert is_multi_model_eval(results) is False

    def test_group_eval_for_comparison(self) -> None:
        """Should group results by suite, case, and model."""
        from arcade_cli.formatters.base import group_eval_for_comparison

        results = make_multi_model_results()
        comparison_data, model_order, per_model_stats = group_eval_for_comparison(results)

        # Check model order
        assert model_order == ["gpt-4o", "gpt-4-turbo"]

        # Check per-model stats
        assert per_model_stats["gpt-4o"]["passed"] == 1
        assert per_model_stats["gpt-4o"]["failed"] == 1
        assert per_model_stats["gpt-4-turbo"]["passed"] == 2
        assert per_model_stats["gpt-4-turbo"]["failed"] == 0

        # Check comparison data structure
        assert "TestSuite" in comparison_data
        assert "case_1" in comparison_data["TestSuite"]
        assert "case_2" in comparison_data["TestSuite"]

        # Check both models present for each case
        assert "gpt-4o" in comparison_data["TestSuite"]["case_1"]
        assert "gpt-4-turbo" in comparison_data["TestSuite"]["case_1"]

    def test_find_best_model(self) -> None:
        """Should find model with highest score."""
        from arcade_cli.formatters.base import find_best_model

        case_models = {
            "model-a": {"evaluation": MockEvaluation(score=0.8)},
            "model-b": {"evaluation": MockEvaluation(score=0.95)},
            "model-c": {"evaluation": MockEvaluation(score=0.7)},
        }

        best, score = find_best_model(case_models)
        assert best == "model-b"
        assert score == 0.95

    def test_find_best_model_tie(self) -> None:
        """Should return 'Tie' when multiple models have same score."""
        from arcade_cli.formatters.base import find_best_model

        case_models = {
            "model-a": {"evaluation": MockEvaluation(score=0.9)},
            "model-b": {"evaluation": MockEvaluation(score=0.9)},
        }

        best, score = find_best_model(case_models)
        assert best == "Tie"
        assert score == 0.9


class TestMultiModelMarkdownFormatter:
    """Tests for multi-model markdown formatting."""

    def test_multi_model_comparison_table(self) -> None:
        """Should show comparison table when multiple models."""
        formatter = MarkdownFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        # Should have multi-model header
        assert "Multi-Model Evaluation Results" in output

        # Should list models
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output

        # Should have per-model summary table
        assert "| Model |" in output
        assert "Pass Rate" in output

        # Should have cross-model comparison section
        assert "Cross-Model Comparison" in output

        # Should show best model
        assert "Best Overall" in output

    def test_multi_model_shows_best_per_case(self) -> None:
        """Should show best model per case in comparison table."""
        formatter = MarkdownFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        # The comparison table should have a Best column
        assert "| Best |" in output

    def test_single_model_uses_regular_format(self) -> None:
        """Should use regular format for single model."""
        formatter = MarkdownFormatter()
        results = make_mock_results(model="gpt-4o")
        output = formatter.format(results)

        # Should NOT have multi-model header
        assert "Multi-Model Evaluation Results" not in output
        # Should have regular header
        assert "# Evaluation Results" in output


class TestMultiModelTextFormatter:
    """Tests for multi-model text formatting."""

    def test_multi_model_text_output(self) -> None:
        """Should show comparison table when multiple models."""
        formatter = TextFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        # Should have multi-model header
        assert "MULTI-MODEL EVALUATION RESULTS" in output

        # Should list models
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output

        # Should have per-model summary section
        assert "PER-MODEL SUMMARY" in output
        assert "Pass Rate" in output

        # Should have cross-model comparison section
        assert "CROSS-MODEL COMPARISON" in output

        # Should show best model
        assert "Best Overall" in output

    def test_single_model_uses_regular_text_format(self) -> None:
        """Should use regular format for single model."""
        formatter = TextFormatter()
        results = make_mock_results(model="gpt-4o")
        output = formatter.format(results)

        # Should NOT have multi-model header
        assert "MULTI-MODEL EVALUATION RESULTS" not in output
        # Should have case results
        assert "test_case_1" in output


class TestMultiModelHtmlFormatter:
    """Tests for multi-model HTML formatting."""

    def test_multi_model_html_output(self) -> None:
        """Should show comparison table when multiple models."""
        formatter = HtmlFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        # Should have multi-model title
        assert "Multi-Model Evaluation Results" in output

        # Should have per-model summary
        assert "Per-Model Summary" in output

        # Should list models in table
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output

        # Should have cross-model comparison
        assert "Cross-Model Comparison" in output

        # Should show best overall
        assert "Best Overall" in output

    def test_multi_model_html_has_styles(self) -> None:
        """Should include multi-model specific styles."""
        formatter = HtmlFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        # Should have comparison table styles
        assert ".comparison-table" in output
        assert ".best-model" in output

    def test_single_model_uses_regular_html_format(self) -> None:
        """Should use regular format for single model."""
        formatter = HtmlFormatter()
        results = make_mock_results(model="gpt-4o")
        output = formatter.format(results)

        # Should NOT have multi-model title
        assert "Multi-Model Evaluation Results" not in output
        # Should have regular title
        assert "Evaluation Results" in output


class TestMultiModelJsonFormatter:
    """Tests for multi-model JSON formatting."""

    def test_multi_model_json_output(self) -> None:
        """Should produce structured multi-model JSON."""
        formatter = JsonFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        data = json.loads(output)

        # Should have multi-model type
        assert data["type"] == "multi_model_evaluation"

        # Should have models list
        assert "models" in data
        assert "gpt-4o" in data["models"]
        assert "gpt-4-turbo" in data["models"]

        # Should have per-model stats
        assert "per_model_stats" in data
        assert "gpt-4o" in data["per_model_stats"]
        assert "gpt-4-turbo" in data["per_model_stats"]

        # Should have comparison structure
        assert "comparison" in data
        assert "TestSuite" in data["comparison"]

    def test_multi_model_json_has_best_model_per_case(self) -> None:
        """Should include best model per case."""
        formatter = JsonFormatter()
        results = make_multi_model_results()
        output = formatter.format(results)

        data = json.loads(output)

        # Each case in comparison should have best_model
        for suite_name, cases in data["comparison"].items():
            for case_name, case_data in cases.items():
                assert "best_model" in case_data
                assert "best_score" in case_data

    def test_single_model_uses_regular_json_format(self) -> None:
        """Should use regular format for single model."""
        formatter = JsonFormatter()
        results = make_mock_results(model="gpt-4o")
        output = formatter.format(results)

        data = json.loads(output)

        # Should NOT have multi-model type
        assert data["type"] == "evaluation"
        # Should not have comparison structure
        assert "comparison" not in data


# =============================================================================
# MULTI-MODEL COMPARATIVE TESTS (CASE-FIRST GROUPING)
# =============================================================================


def make_multi_model_comparative_results() -> list[list[dict]]:
    """Create mock results for multi-model comparative evaluation."""
    results: list[list[dict]] = []

    for model in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]:
        for track in ["track_a", "track_b"]:
            results.append([
                {
                    "model": model,
                    "suite_name": f"TestSuite [{track}]",
                    "track_name": track,
                    "is_comparative": True,
                    "cases": [
                        {
                            "name": "case_1",
                            "input": "Test input for case 1",
                            "evaluation": MockEvaluation(passed=True, score=0.9),
                        },
                        {
                            "name": "case_2",
                            "input": "Test input for case 2",
                            "evaluation": MockEvaluation(passed=False, score=0.3),
                        },
                    ],
                }
            ])

    return results


class TestMultiModelComparativeCaseFirstGrouping:
    """Tests for multi-model comparative evaluation with case-first grouping."""

    def test_is_multi_model_comparative_detection(self) -> None:
        """Should correctly detect multi-model comparative evaluation."""
        from arcade_cli.formatters.base import is_multi_model_comparative

        # Multi-model comparative
        results = make_multi_model_comparative_results()
        assert is_multi_model_comparative(results) is True

        # Single-model comparative
        single_model_results = [r for r in results if r[0].get("model") == "gpt-4o"]
        assert is_multi_model_comparative(single_model_results) is False

    def test_group_comparative_by_case_first(self) -> None:
        """Should group results by case first, then model."""
        from arcade_cli.formatters.base import group_comparative_by_case_first

        results = make_multi_model_comparative_results()
        case_groups, model_order, _, passed, failed, _, total = group_comparative_by_case_first(
            results
        )

        # Check model order
        assert len(model_order) == 3
        assert "gpt-4o" in model_order
        assert "gpt-4o-mini" in model_order
        assert "gpt-4-turbo" in model_order

        # Check case grouping structure: suite -> case -> model
        assert "TestSuite" in case_groups
        assert "case_1" in case_groups["TestSuite"]
        assert "case_2" in case_groups["TestSuite"]

        # Each case should have results for all models
        for case_name in ["case_1", "case_2"]:
            for model in model_order:
                assert model in case_groups["TestSuite"][case_name]

    def test_markdown_case_first_grouping(self) -> None:
        """Markdown formatter should use case-first grouping for multi-model comparative."""
        formatter = MarkdownFormatter()
        results = make_multi_model_comparative_results()
        output = formatter.format(results)

        # Should use case-first format
        assert "Multi-Model" in output
        assert "Results by Case" in output

        # Cases should appear before models in the hierarchy
        case_1_pos = output.find("Case: case_1")
        case_2_pos = output.find("Case: case_2")

        # After each case header, models should be listed
        assert case_1_pos > 0
        assert case_2_pos > 0

        # Check that each case section contains all models
        assert output.count("gpt-4o") > 0
        assert output.count("gpt-4o-mini") > 0
        assert output.count("gpt-4-turbo") > 0

    def test_text_case_first_grouping(self) -> None:
        """Text formatter should use case-first grouping for multi-model comparative."""
        formatter = TextFormatter()
        results = make_multi_model_comparative_results()
        output = formatter.format(results)

        # Should use case-first format
        assert "MULTI-MODEL" in output
        assert "CASE:" in output

        # Check that models appear grouped under cases
        assert "[gpt-4o]" in output
        assert "[gpt-4o-mini]" in output
        assert "[gpt-4-turbo]" in output

    def test_html_case_first_grouping(self) -> None:
        """HTML formatter should use case-first grouping for multi-model comparative."""
        formatter = HtmlFormatter()
        results = make_multi_model_comparative_results()
        output = formatter.format(results)

        # Should use case-first format
        assert "Multi-Model" in output
        assert "Results by Case" in output
        assert "case-group" in output  # CSS class for case grouping
        assert "model-panel" in output  # CSS class for model panels

        # Check structure
        assert "case_1" in output
        assert "case_2" in output

    def test_json_case_first_grouping(self) -> None:
        """JSON formatter should use case-first structure for multi-model comparative."""
        formatter = JsonFormatter()
        results = make_multi_model_comparative_results()
        output = formatter.format(results)
        data = json.loads(output)

        # Should have multi-model comparative type
        assert data["type"] == "multi_model_comparative_evaluation"

        # Should have model order
        assert "models" in data
        assert len(data["models"]) == 3

        # Should have case-first structure
        assert "grouped_by_case" in data
        assert "TestSuite" in data["grouped_by_case"]

        # Check structure: suite -> cases -> case -> models
        suite_data = data["grouped_by_case"]["TestSuite"]
        assert "case_1" in suite_data["cases"]
        assert "case_2" in suite_data["cases"]

        # Each case should have all models
        case_1 = suite_data["cases"]["case_1"]
        assert "models" in case_1
        for model in data["models"]:
            assert model in case_1["models"]

    def test_single_model_comparative_uses_model_first(self) -> None:
        """Single-model comparative should still use model-first grouping."""
        from arcade_cli.formatters.base import is_multi_model_comparative

        # Create single-model comparative
        results = [
            [r[0]] for r in make_multi_model_comparative_results() if r[0].get("model") == "gpt-4o"
        ]

        # Should not be detected as multi-model
        assert is_multi_model_comparative(results) is False

        # Markdown should not have case-first format
        md_formatter = MarkdownFormatter()
        md_output = md_formatter.format(results)
        assert "Results by Model" in md_output
        assert "Results by Case" not in md_output


# =============================================================================
# CONTEXT FUNCTIONALITY TESTS
# =============================================================================


def make_results_with_context(
    model: str = "gpt-4o",
    suite_name: str = "test_suite",
) -> list[list[dict]]:
    """Create mock results with system_message and additional_messages."""
    return [
        [
            {
                "model": model,
                "suite_name": suite_name,
                "rubric": "Test Rubric",
                "cases": [
                    {
                        "name": "case_with_context",
                        "input": "What is the weather?",
                        "system_message": "You are a helpful weather assistant.",
                        "additional_messages": [
                            {"role": "user", "content": "Hello!"},
                            {"role": "assistant", "content": "Hi! How can I help?"},
                            {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": '{"city": "NYC"}',
                                        }
                                    }
                                ],
                            },
                            {
                                "role": "tool",
                                "name": "get_weather",
                                "content": '{"temp": 72, "conditions": "sunny"}',
                            },
                        ],
                        "evaluation": MockEvaluation(passed=True, score=1.0),
                    },
                    {
                        "name": "case_without_context",
                        "input": "Simple test",
                        "evaluation": MockEvaluation(passed=True, score=0.9),
                    },
                ],
            }
        ]
    ]


def make_comparative_results_with_context() -> list[list[dict]]:
    """Create mock comparative results with context."""
    return [
        [
            {
                "model": "gpt-4o",
                "suite_name": "weather_suite [track_a]",
                "track_name": "track_a",
                "rubric": "Test",
                "cases": [
                    {
                        "name": "weather_test",
                        "input": "Get weather for NYC",
                        "system_message": "You are a weather bot.",
                        "additional_messages": [
                            {"role": "user", "content": "I need weather info"},
                            {
                                "role": "tool",
                                "name": "weather_api",
                                "content": '{"temp": 72, "city": "NYC"}',
                            },
                        ],
                        "evaluation": MockEvaluation(passed=True, score=1.0),
                    }
                ],
            },
            {
                "model": "gpt-4o",
                "suite_name": "weather_suite [track_b]",
                "track_name": "track_b",
                "rubric": "Test",
                "cases": [
                    {
                        "name": "weather_test",
                        "input": "Get weather for NYC",
                        "system_message": "You are a weather bot.",
                        "additional_messages": [
                            {"role": "user", "content": "I need weather info"},
                        ],
                        "evaluation": MockEvaluation(passed=False, score=0.7),
                    }
                ],
            },
        ]
    ]


class TestIncludeContextJson:
    """Tests for JSON formatter include_context functionality."""

    def test_json_include_context_true_shows_context(self) -> None:
        """JSON output should include context fields when include_context=True."""
        formatter = JsonFormatter()
        results = make_results_with_context()

        output = formatter.format(results, include_context=True)
        data = json.loads(output)

        cases = data["models"]["gpt-4o"]["suites"]["test_suite"]["cases"]
        case_with_ctx = next(c for c in cases if c["name"] == "case_with_context")

        assert "system_message" in case_with_ctx
        assert case_with_ctx["system_message"] == "You are a helpful weather assistant."
        assert "additional_messages" in case_with_ctx
        assert len(case_with_ctx["additional_messages"]) == 4

    def test_json_include_context_false_excludes_context(self) -> None:
        """JSON output should NOT include context fields when include_context=False."""
        formatter = JsonFormatter()
        results = make_results_with_context()

        output = formatter.format(results, include_context=False)
        data = json.loads(output)

        cases = data["models"]["gpt-4o"]["suites"]["test_suite"]["cases"]
        case_with_ctx = next(c for c in cases if c["name"] == "case_with_context")

        assert "system_message" not in case_with_ctx
        assert "additional_messages" not in case_with_ctx

    def test_json_comparative_with_context(self) -> None:
        """JSON comparative output should include context when requested."""
        formatter = JsonFormatter()
        results = make_comparative_results_with_context()

        output = formatter.format(results, include_context=True)
        data = json.loads(output)

        # Comparative results have different structure
        assert "models" in data
        cases = data["models"]["gpt-4o"]["suites"]["weather_suite"]["cases"]

        assert "weather_test" in cases
        case_data = cases["weather_test"]
        assert "system_message" in case_data
        assert case_data["system_message"] == "You are a weather bot."


class TestIncludeContextHtml:
    """Tests for HTML formatter include_context functionality."""

    def test_html_include_context_shows_context_section(self) -> None:
        """HTML output should include context section when include_context=True."""
        formatter = HtmlFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "context-section" in output or "📋 Context" in output
        assert "You are a helpful weather assistant" in output

    def test_html_include_context_false_no_context(self) -> None:
        """HTML output should NOT include context when include_context=False."""
        formatter = HtmlFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=False)

        # System message should not appear
        assert "You are a helpful weather assistant" not in output

    def test_html_formats_tool_response_json(self) -> None:
        """HTML should pretty-print JSON in tool responses."""
        formatter = HtmlFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        # Tool response JSON should be formatted (indented)
        # The raw JSON would be on one line, formatted has newlines
        assert "tool-response" in output or '"temp"' in output


class TestIncludeContextMarkdown:
    """Tests for Markdown formatter include_context functionality."""

    def test_markdown_include_context_shows_context(self) -> None:
        """Markdown output should include context when include_context=True."""
        formatter = MarkdownFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "Context" in output or "System Message" in output
        assert "You are a helpful weather assistant" in output

    def test_markdown_include_context_false_no_context(self) -> None:
        """Markdown should NOT include context when include_context=False."""
        formatter = MarkdownFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=False)

        assert "You are a helpful weather assistant" not in output


class TestIncludeContextText:
    """Tests for Text formatter include_context functionality."""

    def test_text_include_context_shows_context(self) -> None:
        """Text output should include context when include_context=True."""
        formatter = TextFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "Context:" in output or "CONTEXT" in output
        assert "You are a helpful weather assistant" in output

    def test_text_include_context_false_no_context(self) -> None:
        """Text should NOT include context when include_context=False."""
        formatter = TextFormatter()
        results = make_results_with_context()

        output = formatter.format(results, show_details=True, include_context=False)

        assert "You are a helpful weather assistant" not in output


class TestGroupingPreservesContext:
    """Tests that grouping functions preserve context data."""

    def test_group_comparative_by_case_preserves_context(self) -> None:
        """group_comparative_by_case should preserve system_message and additional_messages."""
        from arcade_cli.formatters.base import group_comparative_by_case

        results = make_comparative_results_with_context()
        groups, *_ = group_comparative_by_case(results)

        # Navigate to the case data
        case_data = groups["gpt-4o"]["weather_suite"]["weather_test"]

        assert "system_message" in case_data
        assert case_data["system_message"] == "You are a weather bot."
        assert "additional_messages" in case_data
        assert len(case_data["additional_messages"]) == 2

    def test_group_comparative_by_case_first_preserves_context(self) -> None:
        """group_comparative_by_case_first should preserve context."""
        from arcade_cli.formatters.base import group_comparative_by_case_first

        # Create multi-model comparative results
        results = make_comparative_results_with_context()
        # Add another model
        results[0].append({
            "model": "gpt-4o-mini",
            "suite_name": "weather_suite [track_a]",
            "track_name": "track_a",
            "rubric": "Test",
            "cases": [
                {
                    "name": "weather_test",
                    "input": "Get weather for NYC",
                    "system_message": "You are a weather bot.",
                    "additional_messages": [{"role": "user", "content": "Test"}],
                    "evaluation": MockEvaluation(passed=True, score=0.95),
                }
            ],
        })

        groups, model_order, *_ = group_comparative_by_case_first(results)

        # Navigate to the case data for first model
        model_data = groups["weather_suite"]["weather_test"]["gpt-4o"]

        assert "system_message" in model_data
        assert model_data["system_message"] == "You are a weather bot."
        assert "additional_messages" in model_data


class TestConversationFormatting:
    """Tests for conversation/tool response formatting."""

    def test_html_conversation_formats_tool_calls(self) -> None:
        """HTML _format_conversation should format tool calls with arguments."""
        formatter = HtmlFormatter()

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test", "limit": 10}',
                        }
                    }
                ],
            }
        ]

        html = formatter._format_conversation(messages)

        assert "search" in html
        assert "query" in html
        assert "tool-call" in html.lower() or "tool_call" in html.lower()

    def test_html_conversation_formats_tool_response_json(self) -> None:
        """HTML should format tool response JSON nicely."""
        formatter = HtmlFormatter()

        messages = [
            {
                "role": "tool",
                "name": "get_data",
                "content": '{"results": [1, 2, 3], "count": 3}',
            }
        ]

        html = formatter._format_conversation(messages)

        # Should have tool-response class for styling
        assert "tool-response" in html
        # Should show the tool name
        assert "get_data" in html

    def test_html_conversation_handles_invalid_json(self) -> None:
        """HTML should gracefully handle non-JSON tool responses."""
        formatter = HtmlFormatter()

        messages = [
            {
                "role": "tool",
                "name": "raw_tool",
                "content": "This is not JSON, just plain text response",
            }
        ]

        html = formatter._format_conversation(messages)

        # Should still render the content
        assert "plain text response" in html
        # Should show as regular content, not JSON
        assert "msg-content" in html


class TestComparativeWithContext:
    """Tests for comparative formatters with context enabled."""

    def test_html_comparative_with_context(self) -> None:
        """HTML comparative format should include context."""
        formatter = HtmlFormatter()
        results = make_comparative_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "You are a weather bot" in output

    def test_markdown_comparative_with_context(self) -> None:
        """Markdown comparative format should include context."""
        formatter = MarkdownFormatter()
        results = make_comparative_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "You are a weather bot" in output

    def test_text_comparative_with_context(self) -> None:
        """Text comparative format should include context."""
        formatter = TextFormatter()
        results = make_comparative_results_with_context()

        output = formatter.format(results, show_details=True, include_context=True)

        assert "You are a weather bot" in output


class TestHtmlSafeId:
    """Tests for HTML formatter's _make_safe_id method."""

    def test_make_safe_id_basic(self) -> None:
        """Test basic ID generation."""
        formatter = HtmlFormatter()
        case_id = formatter._make_safe_id("My Suite", "Test Case", "gpt-4o")

        # Should be a valid HTML ID (alphanumeric + hyphens/underscores)
        assert isinstance(case_id, str)
        assert len(case_id) > 0
        # Should not contain problematic characters
        assert '"' not in case_id
        assert "'" not in case_id
        assert " " not in case_id

    def test_make_safe_id_with_special_chars(self) -> None:
        """Test ID generation with special characters that could break HTML."""
        formatter = HtmlFormatter()

        # Test with double quotes
        case_id = formatter._make_safe_id('Suite "quoted"', 'Case "test"', 'model "name"')
        assert '"' not in case_id

        # Test with single quotes
        case_id2 = formatter._make_safe_id("Suite's name", "Case's test", "model's")
        assert "'" not in case_id2

        # Test with brackets
        case_id3 = formatter._make_safe_id("Suite [track]", "Case [test]", "model")
        assert "[" not in case_id3
        assert "]" not in case_id3

    def test_make_safe_id_stable(self) -> None:
        """Test that same inputs produce same ID (for caching/consistency)."""
        formatter = HtmlFormatter()

        id1 = formatter._make_safe_id("Suite", "Case", "Model")
        id2 = formatter._make_safe_id("Suite", "Case", "Model")

        assert id1 == id2

    def test_make_safe_id_unique(self) -> None:
        """Test that different inputs produce different IDs."""
        formatter = HtmlFormatter()

        id1 = formatter._make_safe_id("Suite1", "Case", "Model")
        id2 = formatter._make_safe_id("Suite2", "Case", "Model")
        id3 = formatter._make_safe_id("Suite1", "Case2", "Model")
        id4 = formatter._make_safe_id("Suite1", "Case", "Model2")

        # All should be different
        ids = {id1, id2, id3, id4}
        assert len(ids) == 4

    def test_json_comparative_preserves_tool_response(self) -> None:
        """JSON comparative should preserve tool response content."""
        formatter = JsonFormatter()
        results = make_comparative_results_with_context()

        output = formatter.format(results, include_context=True)
        data = json.loads(output)

        cases = data["models"]["gpt-4o"]["suites"]["weather_suite"]["cases"]
        case_data = cases["weather_test"]

        assert "additional_messages" in case_data
        tool_msg = next(m for m in case_data["additional_messages"] if m.get("role") == "tool")
        assert "temp" in tool_msg["content"]
