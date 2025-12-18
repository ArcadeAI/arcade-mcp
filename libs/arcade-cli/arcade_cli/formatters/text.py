"""Plain text formatter for evaluation results."""

from typing import Any

from arcade_cli.formatters.base import EvalResultFormatter, group_results_by_model


class TextFormatter(EvalResultFormatter):
    """
    Plain text formatter for evaluation results.

    Produces output similar to pytest's format with simple ASCII formatting.
    """

    @property
    def file_extension(self) -> str:
        return "txt"

    def format(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
    ) -> str:
        lines: list[str] = []

        # Use shared grouping logic
        model_groups, total_passed, total_failed, total_warned, total_cases = (
            group_results_by_model(results)
        )

        # Output grouped results
        for model, suites in model_groups.items():
            lines.append(f"Model: {model}")
            lines.append("=" * 60)

            for suite_name, cases in suites.items():
                lines.append(f"  Suite: {suite_name}")
                lines.append("  " + "-" * 56)

                for case in cases:
                    evaluation = case["evaluation"]
                    if evaluation.passed:
                        status = "PASSED"
                    elif evaluation.warning:
                        status = "WARNED"
                    else:
                        status = "FAILED"

                    score_percentage = evaluation.score * 100
                    lines.append(f"    {status} {case['name']} -- Score: {score_percentage:.2f}%")

                    if show_details:
                        lines.append(f"    User Input: {case['input']}")
                        lines.append("")
                        lines.append("    Details:")
                        for detail_line in self._format_evaluation(evaluation).split("\n"):
                            lines.append(f"    {detail_line}")
                        lines.append("    " + "-" * 52)

                lines.append("")

            lines.append("")

        # Summary
        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append(f"Note: Showing only {total_cases} failed evaluation(s) (--failed-only)")
            summary = f"Summary -- Total: {orig_total} -- Passed: {orig_passed}"
            if orig_warned > 0:
                summary += f" -- Warnings: {orig_warned}"
            if orig_failed > 0:
                summary += f" -- Failed: {orig_failed}"
        else:
            summary = f"Summary -- Total: {total_cases} -- Passed: {total_passed}"
            if total_warned > 0:
                summary += f" -- Warnings: {total_warned}"
            if total_failed > 0:
                summary += f" -- Failed: {total_failed}"

        lines.append(summary)
        lines.append("")

        return "\n".join(lines)

    def _format_evaluation(self, evaluation: Any) -> str:
        """Format evaluation details."""
        result_lines = []
        if evaluation.failure_reason:
            result_lines.append(f"Failure Reason: {evaluation.failure_reason}")
        else:
            for critic_result in evaluation.results:
                is_criticized = critic_result.get("is_criticized", True)
                field = critic_result["field"]
                score = critic_result["score"]
                weight = critic_result["weight"]
                expected = critic_result["expected"]
                actual = critic_result["actual"]

                if is_criticized:
                    match_str = "Match" if critic_result["match"] else "No Match"
                    result_lines.append(
                        f"{field}: {match_str}\n"
                        f"     Score: {score:.2f}/{weight:.2f}\n"
                        f"     Expected: {expected}\n"
                        f"     Actual: {actual}"
                    )
                else:
                    result_lines.append(
                        f"{field}: Un-criticized\n     Expected: {expected}\n     Actual: {actual}"
                    )
        return "\n".join(result_lines)
