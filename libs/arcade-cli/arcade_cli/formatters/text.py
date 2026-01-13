"""Plain text formatter for evaluation and capture results."""

import json
from typing import Any

from arcade_cli.formatters.base import (
    CaptureFormatter,
    CaptureResults,
    ComparativeCaseData,
    EvalResultFormatter,
    compute_track_differences,
    find_best_model,
    group_comparative_by_case,
    group_comparative_by_case_first,
    group_eval_for_comparison,
    group_results_by_model,
    is_comparative_result,
    is_multi_model_capture,
    is_multi_model_comparative,
    is_multi_model_eval,
)


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
        include_context: bool = False,
    ) -> str:
        # Check if this is a comparative evaluation
        if is_comparative_result(results):
            return self._format_comparative(
                results, show_details, failed_only, original_counts, include_context
            )

        # Check if this is a multi-model evaluation
        if is_multi_model_eval(results):
            return self._format_multi_model(
                results, show_details, failed_only, original_counts, include_context
            )

        return self._format_regular(
            results, show_details, failed_only, original_counts, include_context
        )

    def _format_regular(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format regular (non-comparative) evaluation results."""
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

                        # Context section (if include_context is True)
                        if include_context:
                            system_msg = case.get("system_message")
                            addl_msgs = case.get("additional_messages")
                            if system_msg or addl_msgs:
                                lines.append("    Context:")
                                if system_msg:
                                    lines.append(f"      System: {system_msg}")
                                if addl_msgs:
                                    lines.append(f"      Conversation ({len(addl_msgs)} messages):")
                                    for conv_line in self._format_conversation_text(addl_msgs):
                                        lines.append(f"        {conv_line}")
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
            lines.append(f"Note: Showing only {total_cases} failed evaluation(s) (--only-failed)")
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

    # =========================================================================
    # MULTI-MODEL EVALUATION FORMATTING
    # =========================================================================

    def _format_multi_model(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format multi-model evaluation results with comparison tables."""
        lines: list[str] = []

        # Get comparison data
        comparison_data, model_order, per_model_stats = group_eval_for_comparison(results)

        # Header
        lines.append("=" * 78)
        lines.append("MULTI-MODEL EVALUATION RESULTS")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"Models: {', '.join(model_order)}")
        lines.append("")

        # Per-Model Summary Table
        lines.append("-" * 78)
        lines.append("PER-MODEL SUMMARY")
        lines.append("-" * 78)
        lines.append("")

        # Build header row
        header = f"{'Model':<20} {'Passed':>8} {'Failed':>8} {'Warned':>8} {'Total':>8} {'Pass Rate':>10}"
        lines.append(header)
        lines.append("-" * len(header))

        best_model = None
        best_rate = -1.0
        for model in model_order:
            stats = per_model_stats[model]
            rate = stats["pass_rate"]

            if rate > best_rate:
                best_rate = rate
                best_model = model

            lines.append(
                f"{model:<20} {stats['passed']:>8} {stats['failed']:>8} "
                f"{stats['warned']:>8} {stats['total']:>8} {rate:>9.1f}%"
            )

        lines.append("")
        if best_model:
            lines.append(f"Best Overall: {best_model} ({best_rate:.1f}% pass rate)")
        lines.append("")

        # Cross-Model Comparison by Suite
        lines.append("-" * 78)
        lines.append("CROSS-MODEL COMPARISON")
        lines.append("-" * 78)
        lines.append("")

        for suite_name, cases in comparison_data.items():
            lines.append(f"Suite: {suite_name}")
            lines.append("")

            # Build comparison table header - dynamic based on model count
            # Calculate column widths
            case_col_width = 30
            model_col_width = 12
            best_col_width = 15

            header_parts = [f"{'Case':<{case_col_width}}"]
            for model in model_order:
                # Truncate model name if too long
                display_name = (
                    model[: model_col_width - 1] if len(model) > model_col_width - 1 else model
                )
                header_parts.append(f"{display_name:>{model_col_width}}")
            header_parts.append(f"{'Best':>{best_col_width}}")

            header_line = " ".join(header_parts)
            lines.append(header_line)
            lines.append("-" * len(header_line))

            # Build rows for each case
            for case_name, case_models in cases.items():
                # Truncate case name if needed
                display_case = (
                    case_name[: case_col_width - 1]
                    if len(case_name) > case_col_width - 1
                    else case_name
                )
                row_parts = [f"{display_case:<{case_col_width}}"]

                for model in model_order:
                    if model in case_models:
                        evaluation = case_models[model]["evaluation"]
                        score = evaluation.score * 100
                        if evaluation.passed:
                            cell = f"OK {score:.0f}%"
                        elif evaluation.warning:
                            cell = f"WN {score:.0f}%"
                        else:
                            cell = f"FL {score:.0f}%"
                    else:
                        cell = "-"
                    row_parts.append(f"{cell:>{model_col_width}}")

                # Find best model for this case
                best, _ = find_best_model(case_models)
                if best == "Tie":
                    best_cell = "Tie"
                elif best:
                    best_cell = (
                        best[: best_col_width - 1] if len(best) > best_col_width - 1 else best
                    )
                else:
                    best_cell = "-"
                row_parts.append(f"{best_cell:>{best_col_width}}")

                lines.append(" ".join(row_parts))

            lines.append("")

            # Detailed results per case (if requested)
            if show_details:
                lines.append("  Detailed Results:")
                lines.append("  " + "-" * 70)

                for case_name, case_models in cases.items():
                    lines.append(f"  Case: {case_name}")

                    for model in model_order:
                        if model not in case_models:
                            continue

                        case_result = case_models[model]
                        evaluation = case_result["evaluation"]

                        lines.append(f"    [{model}] Score: {evaluation.score * 100:.1f}%")

                        # Show evaluation details indented
                        eval_details = self._format_evaluation(evaluation)
                        for line in eval_details.split("\n"):
                            lines.append(f"      {line}")

                    lines.append("")

                lines.append("")

        # Overall summary
        total_cases = sum(s["total"] for s in per_model_stats.values())
        total_passed = sum(s["passed"] for s in per_model_stats.values())
        total_failed = sum(s["failed"] for s in per_model_stats.values())
        total_warned = sum(s["warned"] for s in per_model_stats.values())

        lines.append("=" * 78)
        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append("Note: Showing only failed evaluations (--only-failed)")
            lines.append(
                f"Summary -- Total: {orig_total} -- Passed: {orig_passed} -- "
                f"Failed: {orig_failed} -- Warned: {orig_warned}"
            )
        else:
            unique_cases = sum(len(cases) for cases in comparison_data.values())
            lines.append(
                f"Summary -- Unique Cases: {unique_cases} -- "
                f"Total Evaluations: {total_cases} ({len(model_order)} models)"
            )
            lines.append(
                f"         Passed: {total_passed} -- Failed: {total_failed} -- Warned: {total_warned}"
            )
        lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # COMPARATIVE EVALUATION FORMATTING
    # =========================================================================

    def _format_comparative(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format comparative evaluation results showing tracks side-by-side."""
        # Check if this is multi-model comparative - use case-first grouping
        if is_multi_model_comparative(results):
            return self._format_comparative_case_first(
                results, show_details, failed_only, original_counts, include_context
            )

        return self._format_comparative_single_model(
            results, show_details, failed_only, original_counts, include_context
        )

    def _format_comparative_single_model(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format single-model comparative evaluation results."""
        lines: list[str] = []

        # Use comparative grouping
        (
            comparative_groups,
            total_passed,
            total_failed,
            total_warned,
            total_cases,
            suite_track_order,
        ) = group_comparative_by_case(results)

        # Collect all unique tracks for header
        all_tracks: list[str] = []
        for tracks in suite_track_order.values():
            for t in tracks:
                if t not in all_tracks:
                    all_tracks.append(t)

        lines.append("=" * 76)
        lines.append("COMPARATIVE EVALUATION RESULTS")
        lines.append("=" * 76)
        lines.append("")
        lines.append(f"All Tracks: {' vs '.join(all_tracks)}")
        lines.append("")

        # Output grouped results
        for model, suites in comparative_groups.items():
            lines.append(f"Model: {model}")
            lines.append("=" * 76)

            for suite_name, cases in suites.items():
                # Get track order for this specific suite
                track_order = suite_track_order.get(suite_name, [])

                lines.append(f"  Suite: {suite_name} (Comparative)")
                lines.append(f"  Tracks: {' vs '.join(track_order)}")
                lines.append("  " + "-" * 72)

                for case_name, case_data in cases.items():
                    # Context section (if include_context is True)
                    if include_context:
                        system_msg = case_data.get("system_message")
                        addl_msgs = case_data.get("additional_messages")
                        if system_msg or addl_msgs:
                            lines.append("  " + "-" * 40)
                            lines.append("  📋 CONTEXT")
                            lines.append("  " + "-" * 40)
                            if system_msg:
                                lines.append(f"  System Message: {system_msg}")
                            if addl_msgs:
                                lines.append(f"  💬 Conversation ({len(addl_msgs)} messages):")
                                for msg in addl_msgs:
                                    role = msg.get("role", "unknown").upper()
                                    content = msg.get("content", "")
                                    name = msg.get("name", "")
                                    role_label = f"[{role}]" if not name else f"[{role}: {name}]"
                                    lines.append(f"    {role_label}")
                                    if content:
                                        # For tool responses, try to format JSON
                                        if role.lower() == "tool":
                                            try:
                                                import json

                                                parsed = json.loads(content)
                                                formatted = json.dumps(parsed, indent=2)
                                                for json_line in formatted.split("\n"):
                                                    lines.append(f"      {json_line}")
                                            except (json.JSONDecodeError, TypeError):
                                                lines.append(f"      {content}")
                                        else:
                                            lines.append(f"      {content}")
                                    # Handle tool calls
                                    tool_calls = msg.get("tool_calls", [])
                                    if tool_calls:
                                        for tc in tool_calls:
                                            func = tc.get("function", {})
                                            tc_name = func.get("name", "unknown")
                                            tc_args = func.get("arguments", "{}")
                                            lines.append(f"      🔧 {tc_name}")
                                            try:
                                                import json

                                                args_dict = (
                                                    json.loads(tc_args)
                                                    if isinstance(tc_args, str)
                                                    else tc_args
                                                )
                                                formatted = json.dumps(args_dict, indent=2)
                                                for arg_line in formatted.split("\n"):
                                                    lines.append(f"        {arg_line}")
                                            except (json.JSONDecodeError, TypeError):
                                                lines.append(f"        {tc_args}")
                            lines.append("  " + "-" * 40)

                    lines.extend(
                        self._format_comparative_case_text(
                            case_name, case_data, track_order, show_details
                        )
                    )

            lines.append("")

        # Summary
        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append(f"Note: Showing only {total_cases} failed evaluation(s) (--only-failed)")
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

    def _format_comparative_case_first(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format multi-model comparative evaluation grouped by case first."""
        lines: list[str] = []

        # Get case-first grouping
        (
            case_groups,
            model_order,
            suite_track_order,
            total_passed,
            total_failed,
            total_warned,
            total_cases,
        ) = group_comparative_by_case_first(results)

        # Collect all unique tracks
        all_tracks: list[str] = []
        for tracks in suite_track_order.values():
            for t in tracks:
                if t not in all_tracks:
                    all_tracks.append(t)

        lines.append("=" * 78)
        lines.append("COMPARATIVE EVALUATION RESULTS (MULTI-MODEL)")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"Models: {', '.join(model_order)}")
        lines.append(f"Tracks: {', '.join(all_tracks)}")
        lines.append("")

        # Results grouped by case
        for suite_name, cases in case_groups.items():
            track_order = suite_track_order.get(suite_name, [])

            lines.append("-" * 78)
            lines.append(f"SUITE: {suite_name}")
            lines.append(f"Tracks: {' vs '.join(track_order)}")
            lines.append("-" * 78)
            lines.append("")

            for case_name, model_data in cases.items():
                # Case header
                lines.append("  " + "=" * 72)
                lines.append(f"  CASE: {case_name}")
                lines.append("  " + "=" * 72)

                # Get input and context from first model
                first_model_data = next(iter(model_data.values()), {})
                case_input = first_model_data.get("input", "")
                if case_input:
                    lines.append(f"  Input: {case_input}")

                # Context section (if include_context is True)
                if include_context:
                    system_msg = first_model_data.get("system_message")
                    addl_msgs = first_model_data.get("additional_messages")
                    if system_msg or addl_msgs:
                        lines.append("")
                        lines.append("  " + "-" * 40)
                        lines.append("  📋 CONTEXT")
                        lines.append("  " + "-" * 40)
                        if system_msg:
                            lines.append(f"  System Message: {system_msg}")
                        if addl_msgs:
                            lines.append(f"  💬 Conversation ({len(addl_msgs)} messages):")
                            for msg in addl_msgs:
                                role = msg.get("role", "unknown").upper()
                                content = msg.get("content", "")
                                name = msg.get("name", "")
                                role_label = f"[{role}]" if not name else f"[{role}: {name}]"
                                lines.append(f"    {role_label}")
                                if content:
                                    # For tool responses, try to format JSON
                                    if role.lower() == "tool":
                                        try:
                                            import json

                                            parsed = json.loads(content)
                                            formatted = json.dumps(parsed, indent=2)
                                            for json_line in formatted.split("\n"):
                                                lines.append(f"      {json_line}")
                                        except (json.JSONDecodeError, TypeError):
                                            lines.append(f"      {content}")
                                    else:
                                        lines.append(f"      {content}")
                                # Handle tool calls in assistant messages
                                tool_calls = msg.get("tool_calls", [])
                                if tool_calls:
                                    for tc in tool_calls:
                                        func = tc.get("function", {})
                                        tc_name = func.get("name", "unknown")
                                        tc_args = func.get("arguments", "{}")
                                        lines.append(f"      🔧 {tc_name}")
                                        try:
                                            import json

                                            args_dict = (
                                                json.loads(tc_args)
                                                if isinstance(tc_args, str)
                                                else tc_args
                                            )
                                            formatted = json.dumps(args_dict, indent=2)
                                            for arg_line in formatted.split("\n"):
                                                lines.append(f"        {arg_line}")
                                        except (json.JSONDecodeError, TypeError):
                                            lines.append(f"        {tc_args}")
                        lines.append("  " + "-" * 40)

                lines.append("")

                # Show each model's results for this case
                for model in model_order:
                    if model not in model_data:
                        lines.append(f"    [{model}] (no data)")
                        lines.append("")
                        continue

                    model_case_data = model_data[model]
                    lines.append(f"    [{model}]")

                    # Show track comparison for this model
                    case_lines = self._format_comparative_case_text(
                        case_name, model_case_data, track_order, show_details
                    )
                    # Indent the case lines
                    for line in case_lines:
                        lines.append("    " + line)

                lines.append("")

        # Summary
        lines.append("=" * 78)
        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append(f"Note: Showing only {total_cases} failed evaluation(s) (--only-failed)")
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

    def _format_comparative_case_text(
        self,
        case_name: str,
        case_data: ComparativeCaseData,
        track_order: list[str],
        show_details: bool,
    ) -> list[str]:
        """Format a single comparative case in text format."""
        lines: list[str] = []
        tracks = case_data.get("tracks", {})

        lines.append("")
        lines.append("    " + "─" * 68)
        lines.append(f"    CASE: {case_name}")
        lines.append("    " + "─" * 68)
        lines.append(f"    Input: {case_data.get('input', 'N/A')}")
        lines.append("")

        # Compute differences from baseline
        differences = compute_track_differences(case_data, track_order)

        # Build comparison table header
        lines.append("    ┌─ COMPARISON ─────────────────────────────────────────────────────┐")
        lines.append(
            "    │ {:20s} │ {:8s} │ {:8s} │ {:24s} │".format(
                "Track", "Status", "Score", "Differences"
            )
        )
        lines.append("    ├" + "─" * 22 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 26 + "┤")

        for track_name in track_order:
            if track_name not in tracks:
                lines.append(
                    "    │ {:20s} │ {:8s} │ {:8s} │ {:24s} │".format(
                        track_name[:20], "N/A", "N/A", "No data"
                    )
                )
                continue

            track_result = tracks[track_name]
            evaluation = track_result.get("evaluation")

            if not evaluation:
                lines.append(
                    "    │ {:20s} │ {:8s} │ {:8s} │ {:24s} │".format(
                        track_name[:20], "N/A", "N/A", "No evaluation"
                    )
                )
                continue

            # Status
            if evaluation.passed:
                status = "PASSED"
            elif evaluation.warning:
                status = "WARNED"
            else:
                status = "FAILED"

            # Score
            score_str = f"{evaluation.score * 100:.1f}%"

            # Differences from baseline
            diff_fields = differences.get(track_name, [])
            if track_name == track_order[0]:
                diff_text = "(baseline)"
            elif diff_fields:
                diff_text = ", ".join(diff_fields)[:24]
            else:
                diff_text = "—"

            lines.append(
                f"    │ {track_name[:20]:20s} │ {status:8s} │ {score_str:8s} │ {diff_text[:24]:24s} │"
            )

        lines.append("    └" + "─" * 22 + "┴" + "─" * 10 + "┴" + "─" * 10 + "┴" + "─" * 26 + "┘")
        lines.append("")

        # Detailed results per track
        if show_details:
            for track_name in track_order:
                if track_name not in tracks:
                    continue

                track_result = tracks[track_name]
                evaluation = track_result.get("evaluation")

                if not evaluation:
                    continue

                lines.append(f"    [{track_name}] Details:")
                for detail_line in self._format_evaluation(evaluation).split("\n"):
                    lines.append(f"      {detail_line}")
                lines.append("")

        return lines

    def _format_conversation_text(self, messages: list[dict]) -> list[str]:
        """Format conversation messages as plain text for context display."""
        lines: list[str] = []

        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            name = msg.get("name", "")

            role_label = f"[{role}]" if not name else f"[{role}: {name}]"
            lines.append(f"  {role_label}")

            if content:
                # For tool responses, try to format JSON nicely
                if role.lower() == "tool":
                    try:
                        parsed = json.loads(content)
                        formatted = json.dumps(parsed, indent=2)
                        for json_line in formatted.split("\n"):
                            lines.append(f"    {json_line}")
                    except (json.JSONDecodeError, TypeError):
                        lines.append(f"    {content}")
                else:
                    lines.append(f"    {content}")

            # Handle tool calls in assistant messages
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tc_name = func.get("name", "unknown")
                    tc_args = func.get("arguments", "{}")
                    lines.append(f"    🔧 {tc_name}")
                    try:
                        args_dict = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
                        formatted = json.dumps(args_dict, indent=2)
                        for arg_line in formatted.split("\n"):
                            lines.append(f"      {arg_line}")
                    except (json.JSONDecodeError, TypeError):
                        lines.append(f"      {tc_args}")

        return lines


class CaptureTextFormatter(CaptureFormatter):
    """Plain text formatter for capture results."""

    @property
    def file_extension(self) -> str:
        return "txt"

    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format capture results as plain text."""
        # Check for multi-model captures
        if is_multi_model_capture(captures):
            return self._format_multi_model(captures, include_context)

        return self._format_single_model(captures, include_context)

    def _format_single_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format single-model capture results."""
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append("CAPTURE RESULTS")
        lines.append("=" * 70)
        lines.append("")

        total_cases = 0
        total_calls = 0

        for capture in captures:
            lines.append(f"Suite: {capture.suite_name}")
            lines.append(f"Model: {capture.model}")
            lines.append(f"Provider: {capture.provider}")
            lines.append("-" * 70)

            for case in capture.captured_cases:
                total_cases += 1
                lines.append("")
                lines.append(f"  Case: {case.case_name}")
                # track_name is set for comparative cases
                track_name = getattr(case, "track_name", None)
                if track_name:
                    lines.append(f"  Track: {track_name}")
                lines.append(f"  User Message: {case.user_message}")

                if include_context and case.system_message:
                    lines.append(f"  System Message: {case.system_message}")

                lines.append("")
                lines.append("  Tool Calls:")
                if case.tool_calls:
                    for tc in case.tool_calls:
                        total_calls += 1
                        lines.append(f"    - {tc.name}")
                        if tc.args:
                            for key, value in tc.args.items():
                                lines.append(f"        {key}: {self._format_value(value)}")
                else:
                    lines.append("    (no tool calls)")

                if include_context and case.additional_messages:
                    lines.append("")
                    lines.append(
                        f"  Conversation Context ({len(case.additional_messages)} messages):"
                    )
                    lines.extend(self._format_conversation_text(case.additional_messages))

                lines.append("")

            lines.append("")

        lines.append("=" * 70)
        lines.append(f"Summary: {total_calls} tool calls across {total_cases} cases")
        lines.append("")

        return "\n".join(lines)

    def _format_multi_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format multi-model capture results with track sections."""
        from arcade_cli.formatters.base import group_captures_by_case_then_track

        grouped_data, model_order, track_order = group_captures_by_case_then_track(captures)
        has_tracks = len(track_order) > 1 or (track_order and track_order[0] is not None)

        lines: list[str] = []

        lines.append("=" * 78)
        lines.append("MULTI-MODEL CAPTURE RESULTS")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"Models: {', '.join(model_order)}")
        if has_tracks:
            track_names = [t for t in track_order if t is not None]
            lines.append(f"Tracks: {' | '.join(track_names)}")
        lines.append("")

        for suite_name, cases in grouped_data.items():
            lines.append("-" * 78)
            lines.append(f"SUITE: {suite_name}")
            lines.append("-" * 78)
            lines.append("")

            for case_name, case_data in cases.items():
                lines.append("  " + "=" * 72)
                lines.append(f"  CASE: {case_name}")
                lines.append("  " + "=" * 72)

                user_msg = case_data.get("user_message", "")
                if user_msg:
                    lines.append(f"  User Message: {user_msg}")
                lines.append("")

                tracks_data = case_data.get("tracks", {})
                track_keys = list(tracks_data.keys())
                has_multiple_tracks = len(track_keys) > 1 or (
                    len(track_keys) == 1 and track_keys[0] != "_default"
                )

                if has_multiple_tracks:
                    # Show track sections
                    for track_key in track_keys:
                        track_display = track_key if track_key != "_default" else "Default"
                        lines.append("  " + "┌" + "─" * 70 + "┐")
                        lines.append(f"  │ 🏷️  TRACK: {track_display:<57s} │")
                        lines.append("  " + "├" + "─" * 70 + "┤")

                        track_data = tracks_data[track_key]
                        models_dict = track_data.get("models", {})

                        for model in model_order:
                            if model not in models_dict:
                                lines.append(f"  │   [{model}] (no data)")
                                continue

                            captured_case = models_dict[model]
                            lines.append(f"  │   [{model}]")

                            if captured_case.tool_calls:
                                for tc in captured_case.tool_calls:
                                    lines.append(f"  │     - {tc.name}")
                                    if tc.args:
                                        for key, value in tc.args.items():
                                            lines.append(
                                                f"  │         {key}: {self._format_value(value)}"
                                            )
                            else:
                                lines.append("  │     (no tool calls)")
                            lines.append("  │")

                        lines.append("  " + "└" + "─" * 70 + "┘")
                        lines.append("")
                else:
                    # No tracks - render models directly
                    track_key = track_keys[0] if track_keys else "_default"
                    track_data = tracks_data.get(track_key, {})
                    models_dict = track_data.get("models", {})

                    lines.append("  Tool Calls by Model:")
                    lines.append("  " + "-" * 70)

                    for model in model_order:
                        if model not in models_dict:
                            lines.append(f"    [{model}] (no data)")
                            continue

                        captured_case = models_dict[model]
                        lines.append(f"    [{model}]")

                        if captured_case.tool_calls:
                            for tc in captured_case.tool_calls:
                                lines.append(f"      - {tc.name}")
                                if tc.args:
                                    for key, value in tc.args.items():
                                        lines.append(
                                            f"          {key}: {self._format_value(value)}"
                                        )
                        else:
                            lines.append("      (no tool calls)")
                        lines.append("")

                # Context section
                system_msg = case_data.get("system_message")
                addl_msgs = case_data.get("additional_messages")
                if include_context and (system_msg or addl_msgs):
                    lines.append("  📋 Context:")
                    if system_msg:
                        lines.append(f"    System: {system_msg}")
                    if addl_msgs:
                        lines.append(f"    Conversation ({len(addl_msgs)} messages):")
                        lines.extend(self._format_conversation_text(addl_msgs))
                    lines.append("")

                lines.append("")

        # Summary
        total_models = len(model_order)
        total_suites = len(grouped_data)
        total_cases = sum(len(cases) for cases in grouped_data.values())
        track_info = f", {len([t for t in track_order if t])} track(s)" if has_tracks else ""

        lines.append("=" * 78)
        lines.append(
            f"Summary: {total_cases} cases across {total_suites} suite(s), "
            f"{total_models} model(s){track_info}"
        )
        lines.append("")

        return "\n".join(lines)

    def _format_conversation_text(self, messages: list[dict]) -> list[str]:
        """Format conversation messages as plain text."""
        lines: list[str] = []

        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            name = msg.get("name", "")

            # Role indicators
            role_prefix = {
                "user": "    [USER]",
                "assistant": "    [ASSISTANT]",
                "tool": "    [TOOL]",
                "system": "    [SYSTEM]",
            }.get(role, f"    [{role.upper()}]")

            # Add separator between messages
            if i > 0:
                lines.append("    " + "-" * 50)

            # Header
            if role == "tool" and name:
                lines.append(f"{role_prefix} ({name})")
            else:
                lines.append(role_prefix)

            # Content
            if content:
                # Indent content lines
                for line in content.split("\n"):
                    if line.strip():
                        lines.append(f"      {line}")
            elif role == "assistant" and not content and tool_calls:
                lines.append("      (calling tools...)")

            # Tool calls for assistant messages
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tc_name = func.get("name", "unknown")
                    tc_args = func.get("arguments", "{}")

                    lines.append(f"      -> {tc_name}")

                    # Parse and format arguments
                    try:
                        args_dict = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
                        args_formatted = json.dumps(args_dict, indent=2)
                        for arg_line in args_formatted.split("\n"):
                            lines.append(f"         {arg_line}")
                    except (json.JSONDecodeError, TypeError):
                        lines.append(f"         {tc_args}")

        return lines

    def _format_value(self, value: Any) -> str:
        """Format a value for display, truncating if too long."""
        str_value = str(value)
        if len(str_value) > 60:
            return str_value[:57] + "..."
        return str_value
