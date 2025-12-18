"""Markdown formatter for evaluation results."""

from datetime import datetime, timezone
from typing import Any

from arcade_cli.formatters.base import (
    EvalResultFormatter,
    group_results_by_model,
    truncate_field_value,
)

# Markdown-specific truncation length (slightly shorter for table readability)
MD_MAX_FIELD_LENGTH = 50


class MarkdownFormatter(EvalResultFormatter):
    """
    Markdown formatter for evaluation results.

    Produces a well-structured Markdown document with tables and collapsible sections.
    """

    @property
    def file_extension(self) -> str:
        return "md"

    def format(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
    ) -> str:
        lines: list[str] = []

        # Header
        lines.append("# Evaluation Results")
        lines.append("")
        lines.append(
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        # Use shared grouping logic
        model_groups, total_passed, total_failed, total_warned, total_cases = (
            group_results_by_model(results)
        )

        # Summary section
        lines.append("## Summary")
        lines.append("")

        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append(f"> ⚠️ **Note:** Showing only {total_cases} failed evaluation(s)")
            lines.append("")
            lines.append("| Metric | Count |")
            lines.append("|--------|-------|")
            lines.append(f"| **Total** | {orig_total} |")
            lines.append(f"| ✅ Passed | {orig_passed} |")
            if orig_warned > 0:
                lines.append(f"| ⚠️ Warnings | {orig_warned} |")
            lines.append(f"| ❌ Failed | {orig_failed} |")
        else:
            lines.append("| Metric | Count |")
            lines.append("|--------|-------|")
            lines.append(f"| **Total** | {total_cases} |")
            lines.append(f"| ✅ Passed | {total_passed} |")
            if total_warned > 0:
                lines.append(f"| ⚠️ Warnings | {total_warned} |")
            if total_failed > 0:
                lines.append(f"| ❌ Failed | {total_failed} |")

        # Pass rate
        if total_cases > 0:
            if failed_only and original_counts:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
            lines.append("")
            lines.append(f"**Pass Rate:** {pass_rate:.1f}%")

        lines.append("")

        # Results by model
        lines.append("## Results by Model")
        lines.append("")

        for model, suites in model_groups.items():
            lines.append(f"### 🤖 {model}")
            lines.append("")

            for suite_name, cases in suites.items():
                lines.append(f"#### 📁 {suite_name}")
                lines.append("")

                # Results table
                lines.append("| Status | Case | Score |")
                lines.append("|--------|------|-------|")

                for case in cases:
                    evaluation = case["evaluation"]
                    if evaluation.passed:
                        status = "✅"
                    elif evaluation.warning:
                        status = "⚠️"
                    else:
                        status = "❌"

                    score_pct = evaluation.score * 100
                    case_name = case["name"].replace("|", "\\|")
                    lines.append(f"| {status} | {case_name} | {score_pct:.1f}% |")

                lines.append("")

                # Detailed results if requested
                if show_details:
                    lines.append("<details>")
                    lines.append("<summary><strong>Detailed Results</strong></summary>")
                    lines.append("")

                    for case in cases:
                        evaluation = case["evaluation"]
                        if evaluation.passed:
                            status_text = "✅ PASSED"
                        elif evaluation.warning:
                            status_text = "⚠️ WARNED"
                        else:
                            status_text = "❌ FAILED"

                        lines.append(f"##### {case['name']}")
                        lines.append("")
                        lines.append(f"**Status:** {status_text}  ")
                        lines.append(f"**Score:** {evaluation.score * 100:.2f}%")
                        lines.append("")
                        lines.append(f"**Input:** `{case['input']}`")
                        lines.append("")

                        # Evaluation details
                        lines.append(self._format_evaluation_details(evaluation))
                        lines.append("")
                        lines.append("---")
                        lines.append("")

                    lines.append("</details>")
                    lines.append("")

        return "\n".join(lines)

    def _format_evaluation_details(self, evaluation: Any) -> str:
        """Format evaluation details as markdown."""
        lines: list[str] = []

        if evaluation.failure_reason:
            lines.append(f"**Failure Reason:** {evaluation.failure_reason}")
        else:
            lines.append("| Field | Match | Score | Expected | Actual |")
            lines.append("|-------|-------|-------|----------|--------|")

            for critic_result in evaluation.results:
                is_criticized = critic_result.get("is_criticized", True)
                field = critic_result["field"]
                score = critic_result["score"]
                weight = critic_result["weight"]
                expected = str(critic_result["expected"]).replace("|", "\\|")
                actual = str(critic_result["actual"]).replace("|", "\\|")

                # Truncate long values for table readability
                expected = truncate_field_value(expected, MD_MAX_FIELD_LENGTH)
                actual = truncate_field_value(actual, MD_MAX_FIELD_LENGTH)

                if is_criticized:
                    match_icon = "✅" if critic_result["match"] else "❌"
                    lines.append(
                        f"| {field} | {match_icon} | {score:.2f}/{weight:.2f} | `{expected}` | `{actual}` |"
                    )
                else:
                    lines.append(f"| {field} | — | - | `{expected}` | `{actual}` |")

        return "\n".join(lines)
