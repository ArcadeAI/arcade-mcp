"""Markdown formatter for evaluation and capture results."""

import json
from datetime import datetime, timezone
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
            if failed_only and original_counts and original_counts[0] > 0:
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

                        # Context section (if include_context is True)
                        if include_context:
                            system_msg = case.get("system_message")
                            addl_msgs = case.get("additional_messages")
                            if system_msg or addl_msgs:
                                lines.append("**📋 Context:**")
                                lines.append("")
                                if system_msg:
                                    lines.append(f"> **System:** {system_msg}")
                                    lines.append("")
                                if addl_msgs:
                                    lines.append(
                                        f"<details open><summary>💬 Conversation ({len(addl_msgs)} messages)</summary>"
                                    )
                                    lines.append("")
                                    lines.extend(self._format_conversation_md(addl_msgs))
                                    lines.append("</details>")
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
        """Format evaluation results with multi-model comparison tables."""
        lines: list[str] = []

        # Header
        lines.append("# Multi-Model Evaluation Results")
        lines.append("")
        lines.append(
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        # Get comparison data
        comparison_data, model_order, per_model_stats = group_eval_for_comparison(results)

        # Calculate totals
        total_cases = sum(s["total"] for s in per_model_stats.values())
        total_passed = sum(s["passed"] for s in per_model_stats.values())
        total_failed = sum(s["failed"] for s in per_model_stats.values())
        total_warned = sum(s["warned"] for s in per_model_stats.values())

        # Models being compared
        lines.append(f"**Models Compared:** {', '.join(f'`{m}`' for m in model_order)}")
        lines.append("")

        # Per-Model Summary Table
        lines.append("## Per-Model Summary")
        lines.append("")
        lines.append("| Model | Passed | Failed | Warned | Total | Pass Rate |")
        lines.append("|-------|--------|--------|--------|-------|-----------|")

        best_model = None
        best_rate = -1.0
        for model in model_order:
            stats = per_model_stats[model]
            rate = stats["pass_rate"]
            rate_str = f"{rate:.1f}%"

            # Track best model
            if rate > best_rate:
                best_rate = rate
                best_model = model

            lines.append(
                f"| `{model}` | {stats['passed']} | {stats['failed']} | "
                f"{stats['warned']} | {stats['total']} | {rate_str} |"
            )

        lines.append("")
        if best_model:
            lines.append(f"**🏆 Best Overall:** `{best_model}` ({best_rate:.1f}% pass rate)")
        lines.append("")

        # Cross-Model Comparison by Suite
        lines.append("## Cross-Model Comparison")
        lines.append("")

        for suite_name, cases in comparison_data.items():
            lines.append(f"### 📁 {suite_name}")
            lines.append("")

            # Build comparison table header
            header = "| Case |"
            separator = "|------|"
            for model in model_order:
                header += f" {model} |"
                separator += "--------|"
            header += " Best |"
            separator += "------|"

            lines.append(header)
            lines.append(separator)

            # Build rows for each case
            for case_name, case_models in cases.items():
                row = f"| {case_name} |"

                for model in model_order:
                    if model in case_models:
                        evaluation = case_models[model]["evaluation"]
                        score = evaluation.score * 100
                        if evaluation.passed:
                            cell = f"✅ {score:.0f}%"
                        elif evaluation.warning:
                            cell = f"⚠️ {score:.0f}%"
                        else:
                            cell = f"❌ {score:.0f}%"
                    else:
                        cell = "—"
                    row += f" {cell} |"

                # Find best model for this case
                best, best_score = find_best_model(case_models)
                if best == "Tie":
                    row += " Tie |"
                elif best:
                    row += f" `{best}` |"
                else:
                    row += " — |"

                lines.append(row)

            lines.append("")

            # Detailed results per case (if requested)
            if show_details:
                lines.append("<details>")
                lines.append("<summary><strong>📋 Detailed Results</strong></summary>")
                lines.append("")

                for case_name, case_models in cases.items():
                    lines.append(f"#### {case_name}")
                    lines.append("")

                    for model in model_order:
                        if model not in case_models:
                            continue

                        case_result = case_models[model]
                        evaluation = case_result["evaluation"]

                        lines.append(f"**{model}:** Score {evaluation.score * 100:.1f}%")
                        lines.append("")
                        lines.append(self._format_evaluation_details(evaluation))
                        lines.append("")

                    lines.append("---")
                    lines.append("")

                lines.append("</details>")
                lines.append("")

        # Overall summary
        lines.append("## Overall Summary")
        lines.append("")
        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            lines.append("> ⚠️ Showing only failed evaluations")
            lines.append("")
            lines.append(f"- **Total Cases:** {orig_total}")
            lines.append(f"- **Passed:** {orig_passed}")
            lines.append(f"- **Failed:** {orig_failed}")
            if orig_warned > 0:
                lines.append(f"- **Warned:** {orig_warned}")
        else:
            # Note: total_cases counts each model's run of each case separately
            unique_cases = sum(len(cases) for cases in comparison_data.values())
            lines.append(f"- **Unique Cases:** {unique_cases}")
            lines.append(f"- **Total Evaluations:** {total_cases} ({len(model_order)} models)")
            lines.append(f"- **Passed:** {total_passed}")
            lines.append(f"- **Failed:** {total_failed}")
            if total_warned > 0:
                lines.append(f"- **Warned:** {total_warned}")

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

        # Single model comparative - use original model-first grouping
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

        # Header
        lines.append("# Comparative Evaluation Results")
        lines.append("")
        lines.append(
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        # Use comparative grouping
        (
            comparative_groups,
            total_passed,
            total_failed,
            total_warned,
            total_cases,
            suite_track_order,
        ) = group_comparative_by_case(results)

        # Collect all unique tracks for summary
        all_tracks: list[str] = []
        for tracks in suite_track_order.values():
            for t in tracks:
                if t not in all_tracks:
                    all_tracks.append(t)

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Tracks compared:** {', '.join(f'`{t}`' for t in all_tracks)}")
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
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
            lines.append("")
            lines.append(f"**Pass Rate:** {pass_rate:.1f}%")

        lines.append("")

        # Results by model
        lines.append("## Results by Model")
        lines.append("")

        for model, suites in comparative_groups.items():
            lines.append(f"### 🤖 {model}")
            lines.append("")

            for suite_name, cases in suites.items():
                # Get track order for this specific suite
                track_order = suite_track_order.get(suite_name, [])

                lines.append(f"#### 📊 {suite_name} (Comparative)")
                lines.append("")
                lines.append(f"**Tracks:** {', '.join(f'`{t}`' for t in track_order)}")
                lines.append("")

                # List all cases with summary comparison
                for case_name, case_data in cases.items():
                    # Context section (if include_context is True)
                    if include_context:
                        system_msg = case_data.get("system_message")
                        addl_msgs = case_data.get("additional_messages")
                        if system_msg or addl_msgs:
                            lines.append("<details>")
                            lines.append("<summary>📋 <strong>Context</strong></summary>")
                            lines.append("")
                            if system_msg:
                                lines.append(f"**System Message:** {system_msg}")
                                lines.append("")
                            if addl_msgs:
                                lines.append(f"**💬 Conversation ({len(addl_msgs)} messages):**")
                                lines.append("")
                                for msg in addl_msgs:
                                    role = msg.get("role", "unknown")
                                    content = msg.get("content", "")
                                    name = msg.get("name", "")
                                    role_icons = {
                                        "user": "👤",
                                        "assistant": "🤖",
                                        "tool": "🔧",
                                        "system": "⚙️",
                                    }
                                    icon = role_icons.get(role, "💬")
                                    label = (
                                        f"{icon} **{role.title()}**"
                                        if not name
                                        else f"{icon} **{role.title()}** (`{name}`)"
                                    )
                                    lines.append(f"> {label}")
                                    if content:
                                        if role == "tool":
                                            try:
                                                import json

                                                parsed = json.loads(content)
                                                formatted = json.dumps(parsed, indent=2)
                                                lines.append("> ```json")
                                                for json_line in formatted.split("\n"):
                                                    lines.append(f"> {json_line}")
                                                lines.append("> ```")
                                            except (json.JSONDecodeError, TypeError):
                                                lines.append(f"> {content}")
                                        else:
                                            lines.append(f"> {content}")
                                    tool_calls = msg.get("tool_calls", [])
                                    if tool_calls:
                                        for tc in tool_calls:
                                            func = tc.get("function", {})
                                            tc_name = func.get("name", "unknown")
                                            tc_args = func.get("arguments", "{}")
                                            lines.append(f"> 🔧 **{tc_name}**")
                                            try:
                                                import json

                                                args_dict = (
                                                    json.loads(tc_args)
                                                    if isinstance(tc_args, str)
                                                    else tc_args
                                                )
                                                formatted = json.dumps(args_dict, indent=2)
                                                lines.append("> ```json")
                                                for arg_line in formatted.split("\n"):
                                                    lines.append(f"> {arg_line}")
                                                lines.append("> ```")
                                            except (json.JSONDecodeError, TypeError):
                                                lines.append(f"> `{tc_args}`")
                                    lines.append(">")
                            lines.append("</details>")
                            lines.append("")

                    lines.extend(
                        self._format_comparative_case(
                            case_name, case_data, track_order, show_details
                        )
                    )

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

        # Header
        lines.append("# Comparative Evaluation Results (Multi-Model)")
        lines.append("")
        lines.append(
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")
        lines.append(f"**Models:** {', '.join(f'`{m}`' for m in model_order)}")
        lines.append("")
        lines.append(f"**Tracks:** {', '.join(f'`{t}`' for t in all_tracks)}")
        lines.append("")

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
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
            lines.append("")
            lines.append(f"**Pass Rate:** {pass_rate:.1f}%")

        lines.append("")

        # Results grouped by case
        lines.append("## Results by Case")
        lines.append("")

        for suite_name, cases in case_groups.items():
            track_order = suite_track_order.get(suite_name, [])

            lines.append(f"### 📊 {suite_name}")
            lines.append("")
            lines.append(f"**Tracks:** {', '.join(f'`{t}`' for t in track_order)}")
            lines.append("")

            for case_name, model_data in cases.items():
                # Case header
                lines.append(f"#### 📋 Case: {case_name}")
                lines.append("")

                # Get input and context from first model
                first_model_data = next(iter(model_data.values()), {})
                case_input = first_model_data.get("input", "")
                if case_input:
                    lines.append(f"**Input:** `{case_input}`")
                    lines.append("")

                # Context section (if include_context is True)
                if include_context:
                    system_msg = first_model_data.get("system_message")
                    addl_msgs = first_model_data.get("additional_messages")
                    if system_msg or addl_msgs:
                        lines.append("<details>")
                        lines.append("<summary>📋 <strong>Context</strong></summary>")
                        lines.append("")
                        if system_msg:
                            lines.append(f"**System Message:** {system_msg}")
                            lines.append("")
                        if addl_msgs:
                            lines.append(f"**💬 Conversation ({len(addl_msgs)} messages):**")
                            lines.append("")
                            for msg in addl_msgs:
                                role = msg.get("role", "unknown")
                                content = msg.get("content", "")
                                name = msg.get("name", "")
                                role_icons = {
                                    "user": "👤",
                                    "assistant": "🤖",
                                    "tool": "🔧",
                                    "system": "⚙️",
                                }
                                icon = role_icons.get(role, "💬")
                                label = (
                                    f"{icon} **{role.title()}**"
                                    if not name
                                    else f"{icon} **{role.title()}** (`{name}`)"
                                )
                                lines.append(f"> {label}")
                                if content:
                                    # For tool responses, format as JSON code block
                                    if role == "tool":
                                        try:
                                            import json

                                            parsed = json.loads(content)
                                            formatted = json.dumps(parsed, indent=2)
                                            lines.append("> ```json")
                                            for json_line in formatted.split("\n"):
                                                lines.append(f"> {json_line}")
                                            lines.append("> ```")
                                        except (json.JSONDecodeError, TypeError):
                                            lines.append(f"> {content}")
                                    else:
                                        lines.append(f"> {content}")
                                # Handle tool calls
                                tool_calls = msg.get("tool_calls", [])
                                if tool_calls:
                                    for tc in tool_calls:
                                        func = tc.get("function", {})
                                        tc_name = func.get("name", "unknown")
                                        tc_args = func.get("arguments", "{}")
                                        lines.append(f"> 🔧 **{tc_name}**")
                                        try:
                                            import json

                                            args_dict = (
                                                json.loads(tc_args)
                                                if isinstance(tc_args, str)
                                                else tc_args
                                            )
                                            formatted = json.dumps(args_dict, indent=2)
                                            lines.append("> ```json")
                                            for arg_line in formatted.split("\n"):
                                                lines.append(f"> {arg_line}")
                                            lines.append("> ```")
                                        except (json.JSONDecodeError, TypeError):
                                            lines.append(f"> `{tc_args}`")
                                lines.append(">")
                        lines.append("</details>")
                        lines.append("")

                # Show each model's results for this case
                for model in model_order:
                    if model not in model_data:
                        lines.append(f"##### 🤖 {model}")
                        lines.append("")
                        lines.append("*(No data)*")
                        lines.append("")
                        continue

                    model_case_data = model_data[model]
                    lines.append(f"##### 🤖 {model}")
                    lines.append("")

                    # Show track comparison for this model
                    lines.extend(
                        self._format_comparative_case(
                            case_name, model_case_data, track_order, show_details
                        )
                    )

                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def _format_comparative_case(
        self,
        case_name: str,
        case_data: ComparativeCaseData,
        track_order: list[str],
        show_details: bool,
    ) -> list[str]:
        """Format a single comparative case showing all tracks."""
        lines: list[str] = []
        tracks = case_data.get("tracks", {})

        lines.append(f"##### Case: {case_name}")
        lines.append("")
        lines.append(f"**Input:** `{case_data.get('input', 'N/A')}`")
        lines.append("")

        # Compute differences from baseline
        differences = compute_track_differences(case_data, track_order)

        # Summary comparison table
        lines.append("| Track | Status | Score | Differences |")
        lines.append("|-------|--------|-------|-------------|")

        for track_name in track_order:
            if track_name not in tracks:
                lines.append(f"| `{track_name}` | ⚠️ | N/A | *No data* |")
                continue

            track_result = tracks[track_name]
            evaluation = track_result.get("evaluation")

            if not evaluation:
                lines.append(f"| `{track_name}` | ⚠️ | N/A | *No evaluation* |")
                continue

            # Status
            if evaluation.passed:
                status = "✅"
            elif evaluation.warning:
                status = "⚠️"
            else:
                status = "❌"

            # Score
            score_pct = evaluation.score * 100

            # Differences from baseline
            diff_fields = differences.get(track_name, [])
            if track_name == track_order[0]:
                diff_text = "*(baseline)*"
            elif diff_fields:
                diff_text = ", ".join(f"`{f}`" for f in diff_fields)
            else:
                diff_text = "—"

            lines.append(f"| `{track_name}` | {status} | {score_pct:.1f}% | {diff_text} |")

        lines.append("")

        # Detailed results per track (collapsible)
        if show_details:
            for track_name in track_order:
                if track_name not in tracks:
                    continue

                track_result = tracks[track_name]
                evaluation = track_result.get("evaluation")

                if not evaluation:
                    continue

                lines.append("<details>")
                lines.append(f"<summary>📋 <b>{track_name}</b> — Detailed Results</summary>")
                lines.append("")
                lines.append(self._format_evaluation_details(evaluation))
                lines.append("")
                lines.append("</details>")
                lines.append("")

        lines.append("---")
        lines.append("")

        return lines

    def _format_conversation_md(self, messages: list[dict]) -> list[str]:
        """Format conversation messages as Markdown for context display."""
        lines: list[str] = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            name = msg.get("name", "")

            role_icons = {"user": "👤", "assistant": "🤖", "tool": "🔧", "system": "⚙️"}
            icon = role_icons.get(role, "💬")
            label = (
                f"{icon} **{role.title()}**"
                if not name
                else f"{icon} **{role.title()}** (`{name}`)"
            )

            lines.append(f"> {label}")

            if content:
                # For tool responses, try to format JSON nicely
                if role == "tool":
                    try:
                        parsed = json.loads(content)
                        formatted = json.dumps(parsed, indent=2)
                        lines.append("> ```json")
                        for json_line in formatted.split("\n"):
                            lines.append(f"> {json_line}")
                        lines.append("> ```")
                    except (json.JSONDecodeError, TypeError):
                        lines.append(f"> {content}")
                else:
                    lines.append(f"> {content}")

            # Handle tool calls in assistant messages
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tc_name = func.get("name", "unknown")
                    tc_args = func.get("arguments", "{}")
                    lines.append(f"> 🔧 **{tc_name}**")
                    try:
                        args_dict = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
                        formatted = json.dumps(args_dict, indent=2)
                        lines.append("> ```json")
                        for arg_line in formatted.split("\n"):
                            lines.append(f"> {arg_line}")
                        lines.append("> ```")
                    except (json.JSONDecodeError, TypeError):
                        lines.append(f"> `{tc_args}`")

            lines.append(">")

        return lines


class CaptureMarkdownFormatter(CaptureFormatter):
    """Markdown formatter for capture results."""

    @property
    def file_extension(self) -> str:
        return "md"

    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format capture results as Markdown."""
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
        lines.append("# Capture Results")
        lines.append("")

        total_cases = 0
        total_calls = 0

        for capture in captures:
            lines.append(f"## {capture.suite_name}")
            lines.append("")
            lines.append(f"- **Model:** {capture.model}")
            lines.append(f"- **Provider:** {capture.provider}")
            lines.append("")

            for case in capture.captured_cases:
                total_cases += 1
                lines.append(f"### Case: {case.case_name}")
                lines.append("")

                # track_name is set for comparative cases
                track_name = getattr(case, "track_name", None)
                if track_name:
                    lines.append(f"**Track:** `{track_name}`")
                    lines.append("")

                lines.append(f"**User Message:** {case.user_message}")
                lines.append("")

                if include_context and case.system_message:
                    lines.append(f"**System Message:** {case.system_message}")
                    lines.append("")

                lines.append("#### Tool Calls")
                lines.append("")

                if case.tool_calls:
                    for tc in case.tool_calls:
                        total_calls += 1
                        lines.append(f"**`{tc.name}`**")
                        if tc.args:
                            lines.append("")
                            lines.append("```json")
                            lines.append(json.dumps(tc.args, indent=2))
                            lines.append("```")
                        lines.append("")
                else:
                    lines.append("*No tool calls captured*")
                    lines.append("")

                if include_context and case.additional_messages:
                    lines.append("<details open>")
                    lines.append(
                        f"<summary>💬 <b>Conversation Context</b> ({len(case.additional_messages)} messages)</summary>"
                    )
                    lines.append("")
                    lines.extend(self._format_conversation_md(case.additional_messages))
                    lines.append("</details>")
                    lines.append("")

                lines.append("---")
                lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Cases:** {total_cases}")
        lines.append(f"- **Total Tool Calls:** {total_calls}")
        lines.append("")

        return "\n".join(lines)

    def _format_multi_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format multi-model capture results with track sections."""
        from arcade_cli.formatters.base import group_captures_by_case_then_track

        grouped, model_order, track_order = group_captures_by_case_then_track(captures)
        has_tracks = len(track_order) > 1 or (track_order and track_order[0] is not None)

        lines: list[str] = []
        lines.append("# Multi-Model Capture Results")
        lines.append("")

        # Show models being compared
        lines.append(f"**Models Compared:** {', '.join(f'`{m}`' for m in model_order)}")
        if has_tracks:
            track_names = [t for t in track_order if t is not None]
            lines.append(f"**Tracks:** {' | '.join(f'`{t}`' for t in track_names)}")
        lines.append("")

        total_cases = 0
        total_calls = 0

        for suite_name, cases in grouped.items():
            lines.append(f"## {suite_name}")
            lines.append("")

            for case_name, case_data in cases.items():
                total_cases += 1
                lines.append(f"### Case: {case_name}")
                lines.append("")
                lines.append(f"**User Message:** {case_data.get('user_message', 'N/A')}")
                lines.append("")

                if include_context and case_data.get("system_message"):
                    lines.append(f"**System Message:** {case_data['system_message']}")
                    lines.append("")

                tracks_data = case_data.get("tracks", {})
                track_keys = list(tracks_data.keys())
                has_multiple_tracks = len(track_keys) > 1 or (
                    len(track_keys) == 1 and track_keys[0] != "_default"
                )

                if has_multiple_tracks:
                    # Show tool calls by track with clear sections
                    for track_key in track_keys:
                        track_display = track_key if track_key != "_default" else "Default"
                        lines.append(f"#### Track: `{track_display}`")
                        lines.append("")

                        track_data = tracks_data[track_key]
                        models_dict = track_data.get("models", {})

                        # Model comparison table within track
                        lines.append("| Model | Tools Called |")
                        lines.append("|-------|-------------|")

                        for model in model_order:
                            if model not in models_dict:
                                lines.append(f"| `{model}` | *(no data)* |")
                                continue

                            captured_case = models_dict[model]
                            if captured_case.tool_calls:
                                tool_names = ", ".join(
                                    f"`{tc.name}`" for tc in captured_case.tool_calls
                                )
                                total_calls += len(captured_case.tool_calls)
                            else:
                                tool_names = "*(none)*"
                            lines.append(f"| `{model}` | {tool_names} |")

                        lines.append("")

                        # Detailed tool calls per model
                        for model in model_order:
                            if model not in models_dict:
                                continue

                            captured_case = models_dict[model]
                            if not captured_case.tool_calls:
                                continue

                            lines.append("<details>")
                            lines.append(f"<summary>🤖 {model} - Details</summary>")
                            lines.append("")

                            for tc in captured_case.tool_calls:
                                lines.append(f"**`{tc.name}`**")
                                if tc.args:
                                    lines.append("")
                                    lines.append("```json")
                                    lines.append(json.dumps(tc.args, indent=2))
                                    lines.append("```")
                                lines.append("")

                            lines.append("</details>")
                            lines.append("")

                        lines.append("---")
                        lines.append("")
                else:
                    # No tracks - show models directly
                    lines.append("#### Tool Calls by Model")
                    lines.append("")

                    track_key = track_keys[0] if track_keys else "_default"
                    track_data = tracks_data.get(track_key, {})
                    models_dict = track_data.get("models", {})

                    lines.append("| Model | Tools Called |")
                    lines.append("|-------|-------------|")

                    for model in model_order:
                        if model not in models_dict:
                            lines.append(f"| `{model}` | *(no data)* |")
                            continue

                        captured_case = models_dict[model]
                        if captured_case.tool_calls:
                            tool_names = ", ".join(
                                f"`{tc.name}`" for tc in captured_case.tool_calls
                            )
                            total_calls += len(captured_case.tool_calls)
                        else:
                            tool_names = "*(none)*"
                        lines.append(f"| `{model}` | {tool_names} |")

                    lines.append("")

                    # Detailed tool calls per model (collapsible)
                    for model in model_order:
                        if model not in models_dict:
                            continue

                        captured_case = models_dict[model]
                        if not captured_case.tool_calls:
                            continue

                        lines.append("<details>")
                        lines.append(f"<summary>🤖 <b>{model}</b> - Tool Call Details</summary>")
                        lines.append("")

                        for tc in captured_case.tool_calls:
                            lines.append(f"**`{tc.name}`**")
                            if tc.args:
                                lines.append("")
                                lines.append("```json")
                                lines.append(json.dumps(tc.args, indent=2))
                                lines.append("```")
                            lines.append("")

                        lines.append("</details>")
                        lines.append("")

                # Context (shared, show once)
                if include_context and case_data.get("additional_messages"):
                    lines.append("<details>")
                    lines.append(
                        f"<summary>💬 <b>Conversation Context</b> "
                        f"({len(case_data['additional_messages'])} messages)</summary>"
                    )
                    lines.append("")
                    lines.extend(self._format_conversation_md(case_data["additional_messages"]))
                    lines.append("</details>")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Models:** {len(model_order)}")
        lines.append(f"- **Unique Cases:** {total_cases}")
        lines.append(f"- **Total Tool Calls:** {total_calls}")
        lines.append("")

        return "\n".join(lines)

    def _format_conversation_md(self, messages: list[dict]) -> list[str]:
        """Format conversation messages as rich Markdown."""
        lines: list[str] = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            name = msg.get("name", "")

            # Role-specific icons and formatting
            role_info = {
                "user": ("👤", "**User**"),
                "assistant": ("🤖", "**Assistant**"),
                "tool": ("🔧", "**Tool**"),
                "system": ("⚙️", "**System**"),
            }.get(role, ("💬", f"**{role.capitalize()}**"))

            icon, label = role_info

            # Header line
            if role == "tool" and name:
                lines.append(f"> {icon} {label} (`{name}`)")
            else:
                lines.append(f"> {icon} {label}")

            lines.append(">")

            # Content
            if content:
                # Indent content and handle multi-line
                for line in content.split("\n"):
                    lines.append(f"> {line}")
            elif role == "assistant" and not content and tool_calls:
                lines.append("> *(calling tools...)*")

            # Tool calls for assistant messages
            if tool_calls:
                lines.append(">")
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tc_name = func.get("name", "unknown")
                    tc_args = func.get("arguments", "{}")

                    # Parse and pretty-print arguments
                    try:
                        args_dict = json.loads(tc_args) if isinstance(tc_args, str) else tc_args
                        args_formatted = json.dumps(args_dict, indent=2)
                    except (json.JSONDecodeError, TypeError):
                        args_formatted = str(tc_args)

                    lines.append(f"> 📞 **`{tc_name}`**")
                    lines.append(">")
                    lines.append("> ```json")
                    for arg_line in args_formatted.split("\n"):
                        lines.append(f"> {arg_line}")
                    lines.append("> ```")

            lines.append("")  # Blank line between messages

        return lines
