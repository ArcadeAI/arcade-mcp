"""HTML formatter for evaluation and capture results with full color support."""

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


class HtmlFormatter(EvalResultFormatter):
    """
    HTML formatter for evaluation results.

    Produces a styled HTML document with colors matching the terminal output.

    Security Note: All user-controllable data MUST be escaped via _escape_html()
    before being inserted into HTML. This includes case names, inputs, model names,
    suite names, and any evaluation results or error messages.
    """

    def __init__(self) -> None:
        """Initialize formatter with ID tracking for uniqueness."""
        super().__init__()
        self._id_cache: dict[tuple[str, str, str], str] = {}
        self._used_ids: set[str] = set()

    @property
    def file_extension(self) -> str:
        return "html"

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
        # Use shared grouping logic
        model_groups, total_passed, total_failed, total_warned, total_cases = (
            group_results_by_model(results)
        )

        # Calculate pass rate
        if total_cases > 0:
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
        else:
            pass_rate = 0

        # Build HTML
        html_parts = [self._get_html_header()]

        # Title and timestamp
        html_parts.append('<div class="container">')
        html_parts.append("<h1>🎯 Evaluation Results</h1>")
        html_parts.append(
            f'<p class="timestamp">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>'
        )

        # Summary section
        html_parts.append('<div class="summary-section">')
        html_parts.append("<h2>📊 Summary</h2>")

        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            html_parts.append(
                f'<div class="warning-banner">⚠️ Showing only {total_cases} failed evaluation(s)</div>'
            )
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{orig_total}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{orig_passed}</span></div>'
            )
            if orig_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{orig_warned}</span></div>'
                )
            html_parts.append(
                f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{orig_failed}</span></div>'
            )
        else:
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{total_cases}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{total_passed}</span></div>'
            )
            if total_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{total_warned}</span></div>'
                )
            if total_failed > 0:
                html_parts.append(
                    f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{total_failed}</span></div>'
                )

        html_parts.append("</div>")  # stats-grid
        html_parts.append(
            f'<div class="pass-rate">Pass Rate: <strong>{pass_rate:.1f}%</strong></div>'
        )
        html_parts.append("</div>")  # summary-section

        # Results by model
        html_parts.append("<h2>📋 Results by Model</h2>")

        for model, suites in model_groups.items():
            html_parts.append('<div class="model-section">')
            html_parts.append(f"<h3>🤖 {self._escape_html(model)}</h3>")

            for suite_name, cases in suites.items():
                # Show suite/file name
                html_parts.append('<div class="suite-section">')
                html_parts.append(
                    f'<h4 class="suite-header">📁 {self._escape_html(suite_name)}</h4>'
                )

                # Show summary table only when NOT showing details (avoid duplication)
                if not show_details:
                    html_parts.append('<table class="results-table">')
                    html_parts.append(
                        "<thead><tr><th>Status</th><th>Case</th><th>Score</th></tr></thead>"
                    )
                    html_parts.append("<tbody>")

                    for case in cases:
                        evaluation = case["evaluation"]
                        if evaluation.passed:
                            status_class = "passed"
                            status_text = "✅ PASSED"
                        elif evaluation.warning:
                            status_class = "warned"
                            status_text = "⚠️ WARNED"
                        else:
                            status_class = "failed"
                            status_text = "❌ FAILED"

                        score_pct = evaluation.score * 100
                        case_name = self._escape_html(case["name"])

                        html_parts.append(f'<tr class="{status_class}">')
                        html_parts.append(f'<td class="status-cell">{status_text}</td>')
                        html_parts.append(f"<td>{case_name}</td>")
                        html_parts.append(f'<td class="score-cell">{score_pct:.1f}%</td>')
                        html_parts.append("</tr>")

                    html_parts.append("</tbody></table>")

                # Detailed results - each case is individually expandable
                if show_details:
                    html_parts.append(
                        '<p class="expand-hint">💡 Click on any case below to expand details</p>'
                    )
                    for case in cases:
                        evaluation = case["evaluation"]
                        if evaluation.passed:
                            status_class = "passed"
                            status_badge = '<span class="badge passed">PASSED</span>'
                            status_icon = "✅"
                        elif evaluation.warning:
                            status_class = "warned"
                            status_badge = '<span class="badge warned">WARNED</span>'
                            status_icon = "⚠️"
                        else:
                            status_class = "failed"
                            status_badge = '<span class="badge failed">FAILED</span>'
                            status_icon = "❌"

                        case_name = self._escape_html(case["name"])
                        score_pct = evaluation.score * 100

                        # Each case is a collapsible details element (collapsed by default)
                        html_parts.append(f'<details class="case-expandable {status_class}">')
                        html_parts.append(
                            f'<summary class="case-summary">'
                            f"{status_icon} <strong>{case_name}</strong> "
                            f'<span class="score-inline">{score_pct:.1f}%</span> '
                            f"{status_badge}"
                            f"</summary>"
                        )
                        html_parts.append('<div class="case-content">')
                        html_parts.append(
                            f"<p><strong>Input:</strong> <code>{self._escape_html(case['input'])}</code></p>"
                        )

                        # Context section (if include_context is True)
                        if include_context:
                            system_msg = case.get("system_message")
                            addl_msgs = case.get("additional_messages")
                            if system_msg or addl_msgs:
                                html_parts.append('<div class="context-section">')
                                html_parts.append("<h4>📋 Context</h4>")
                                if system_msg:
                                    html_parts.append(
                                        f'<div class="context-item">'
                                        f"<strong>System Message:</strong> "
                                        f"<code>{self._escape_html(system_msg)}</code>"
                                        f"</div>"
                                    )
                                if addl_msgs:
                                    conversation_html = self._format_conversation(addl_msgs)
                                    html_parts.append(
                                        f'<details class="context-item conversation-context" open>'
                                        f"<summary>💬 Conversation Context ({len(addl_msgs)} messages)</summary>"
                                        f"{conversation_html}"
                                        f"</details>"
                                    )
                                html_parts.append("</div>")

                        # Evaluation details
                        html_parts.append(self._format_evaluation_details(evaluation))
                        html_parts.append("</div>")
                        html_parts.append("</details>")

                html_parts.append("</div>")  # suite-section

            html_parts.append("</div>")  # model-section

        html_parts.append("</div>")  # container
        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    def _format_evaluation_details(self, evaluation: Any) -> str:
        """Format evaluation details as HTML table."""
        if evaluation.failure_reason:
            return f'<div class="failure-reason">❌ <strong>Failure Reason:</strong> {self._escape_html(evaluation.failure_reason)}</div>'

        lines = ['<table class="detail-table">']
        lines.append(
            "<thead><tr><th>Field</th><th>Match</th><th>Score</th><th>Expected</th><th>Actual</th></tr></thead>"
        )
        lines.append("<tbody>")

        for critic_result in evaluation.results:
            is_criticized = critic_result.get("is_criticized", True)
            field = self._escape_html(critic_result["field"])
            score = critic_result["score"]
            weight = critic_result["weight"]
            expected = self._escape_html(str(critic_result["expected"]))
            actual = self._escape_html(str(critic_result["actual"]))

            # Truncate long values for table readability
            expected = truncate_field_value(expected)
            actual = truncate_field_value(actual)

            if is_criticized:
                if critic_result["match"]:
                    match_cell = '<span class="match-yes">✅ Match</span>'
                    row_class = "match-row"
                else:
                    match_cell = '<span class="match-no">❌ No Match</span>'
                    row_class = "nomatch-row"
                score_cell = f"{score:.2f}/{weight:.2f}"
            else:
                match_cell = '<span class="uncriticized">— Un-criticized</span>'
                row_class = "uncriticized-row"
                score_cell = "-"

            lines.append(f'<tr class="{row_class}">')
            lines.append(f'<td class="field-name">{field}</td>')
            lines.append(f"<td>{match_cell}</td>")
            lines.append(f'<td class="score">{score_cell}</td>')
            lines.append(f"<td><code>{expected}</code></td>")
            lines.append(f"<td><code>{actual}</code></td>")
            lines.append("</tr>")

        lines.append("</tbody></table>")
        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def _make_safe_id(self, suite_name: str, case_name: str, model_name: str = "") -> str:
        """Generate a safe ID for HTML attributes and CSS selectors.

        Removes or replaces characters that could break HTML attributes or
        CSS selectors, including quotes, brackets, and special characters.
        Ensures uniqueness by appending a counter when duplicates are detected.

        Args:
            suite_name: The suite name.
            case_name: The case name.
            model_name: Optional model name.

        Returns:
            A sanitized string safe for use in HTML id/data attributes, guaranteed unique.
        """
        import re

        def sanitize(s: str) -> str:
            # Replace common separators with underscores
            s = s.replace(" ", "_").replace("-", "_")
            # Remove brackets and parentheses
            s = s.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
            # Remove quotes that would break HTML attributes
            s = s.replace('"', "").replace("'", "")
            # Remove any remaining non-alphanumeric characters except underscores
            s = re.sub(r"[^\w]", "", s)
            return s

        # Check cache for idempotence - same inputs should return same ID
        cache_key = (suite_name, case_name, model_name)
        if cache_key in self._id_cache:
            return self._id_cache[cache_key]

        suite_id = sanitize(suite_name)
        case_id_part = sanitize(case_name)
        base_id = f"{suite_id}__{case_id_part}"

        if model_name:
            model_id = sanitize(model_name)
            base_id = f"{model_id}__{base_id}"

        # Ensure uniqueness by appending a counter if this ID already exists
        unique_id = base_id
        counter = 1
        while unique_id in self._used_ids:
            unique_id = f"{base_id}_{counter}"
            counter += 1

        # Cache the result and mark ID as used
        self._id_cache[cache_key] = unique_id
        self._used_ids.add(unique_id)
        return unique_id

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format conversation messages as rich HTML for context display."""
        html_parts = ['<div class="conversation">']

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content")
            tool_calls = msg.get("tool_calls", [])
            tool_name = msg.get("name", "")  # For tool responses

            role_class = f"msg msg-{role}"
            role_label = {
                "user": "👤 User",
                "assistant": "🤖 Assistant",
                "tool": "🔧 Tool",
                "system": "⚙️ System",
            }.get(role, f"💬 {role.title()}")

            # Add tool name to label for tool responses
            if role == "tool" and tool_name:
                role_label = f"🔧 Tool ({tool_name})"

            html_parts.append(f'<div class="{role_class}">')
            html_parts.append(f'<div class="msg-role">{role_label}</div>')

            if content:
                # For tool responses, try to format JSON nicely
                if role == "tool":
                    try:
                        parsed_content = json.loads(content)
                        formatted_content = json.dumps(parsed_content, indent=2)
                        html_parts.append(
                            f'<pre class="tool-response">{self._escape_html(formatted_content)}</pre>'
                        )
                    except (json.JSONDecodeError, TypeError):
                        # Not valid JSON, show as regular content
                        html_parts.append(
                            f'<div class="msg-content">{self._escape_html(str(content))}</div>'
                        )
                else:
                    html_parts.append(
                        f'<div class="msg-content">{self._escape_html(str(content))}</div>'
                    )

            # Handle tool calls in assistant messages
            if tool_calls:
                html_parts.append('<div class="tool-calls">')
                for tc in tool_calls:
                    tc_func = tc.get("function", {})
                    tc_name = tc_func.get("name", "unknown")
                    tc_args = tc_func.get("arguments", "{}")
                    try:
                        args_formatted = json.dumps(json.loads(tc_args), indent=2)
                    except (json.JSONDecodeError, TypeError):
                        args_formatted = str(tc_args)
                    html_parts.append(
                        f'<div class="tool-call-item">'
                        f'<span class="tool-call-name">🛠️ {self._escape_html(tc_name)}</span>'
                        f'<pre class="tool-call-args">{self._escape_html(args_formatted)}</pre>'
                        f"</div>"
                    )
                html_parts.append("</div>")

            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

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
        comparison_data, model_order, per_model_stats = group_eval_for_comparison(results)

        # Build HTML
        html_parts = [self._get_html_header()]
        html_parts.append(self._get_multi_model_styles())

        # Container
        html_parts.append('<div class="container">')
        html_parts.append("<h1>🔄 Multi-Model Evaluation Results</h1>")
        html_parts.append(
            f'<p class="timestamp">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>'
        )
        html_parts.append(f'<p class="models-info">Models: {", ".join(model_order)}</p>')

        # Per-Model Summary Section
        html_parts.append('<div class="section">')
        html_parts.append("<h2>📊 Per-Model Summary</h2>")
        html_parts.append('<table class="summary-table multi-model-summary">')
        html_parts.append("<thead><tr>")
        html_parts.append(
            "<th>Model</th><th>Passed</th><th>Failed</th><th>Warned</th><th>Total</th><th>Pass Rate</th>"
        )
        html_parts.append("</tr></thead><tbody>")

        best_model = None
        best_rate = -1.0
        for model in model_order:
            stats = per_model_stats[model]
            rate = stats["pass_rate"]

            if rate > best_rate:
                best_rate = rate
                best_model = model

            row_class = "best-model" if rate == best_rate and best_model == model else ""
            html_parts.append(f'<tr class="{row_class}">')
            html_parts.append(f'<td class="model-name">{self._escape_html(model)}</td>')
            html_parts.append(f'<td class="passed">{stats["passed"]}</td>')
            html_parts.append(f'<td class="failed">{stats["failed"]}</td>')
            html_parts.append(f'<td class="warned">{stats["warned"]}</td>')
            html_parts.append(f"<td>{stats['total']}</td>")
            html_parts.append(f'<td class="pass-rate">{rate:.1f}%</td>')
            html_parts.append("</tr>")

        html_parts.append("</tbody></table>")

        if best_model:
            html_parts.append(
                f'<p class="best-overall">🏆 Best Overall: <strong>{self._escape_html(best_model)}</strong> ({best_rate:.1f}% pass rate)</p>'
            )
        html_parts.append("</div>")

        # Cross-Model Comparison Section
        html_parts.append('<div class="section">')
        html_parts.append("<h2>⚔️ Cross-Model Comparison</h2>")

        for suite_name, cases in comparison_data.items():
            html_parts.append('<div class="suite-section">')
            html_parts.append(f"<h3>Suite: {self._escape_html(suite_name)}</h3>")

            # Comparison table
            html_parts.append('<table class="comparison-table">')
            html_parts.append("<thead><tr>")
            html_parts.append("<th>Case</th>")
            for model in model_order:
                html_parts.append(f"<th>{self._escape_html(model)}</th>")
            html_parts.append("<th>Best</th>")
            html_parts.append("</tr></thead><tbody>")

            for case_name, case_models in cases.items():
                html_parts.append("<tr>")
                html_parts.append(f'<td class="case-name">{self._escape_html(case_name)}</td>')

                for model in model_order:
                    if model in case_models:
                        evaluation = case_models[model]["evaluation"]
                        score = evaluation.score * 100
                        if evaluation.passed:
                            cell_class = "passed"
                            icon = "✓"
                        elif evaluation.warning:
                            cell_class = "warned"
                            icon = "⚠"
                        else:
                            cell_class = "failed"
                            icon = "✗"
                        html_parts.append(f'<td class="{cell_class}">{icon} {score:.0f}%</td>')
                    else:
                        html_parts.append('<td class="no-data">-</td>')

                # Best model
                best, _ = find_best_model(case_models)
                if best == "Tie":
                    html_parts.append('<td class="tie">🤝 Tie</td>')
                elif best and best != "N/A":
                    html_parts.append(f'<td class="best">🏆 {self._escape_html(best)}</td>')
                else:
                    html_parts.append('<td class="no-data">-</td>')

                html_parts.append("</tr>")

            html_parts.append("</tbody></table>")
            html_parts.append("</div>")

            # Detailed results
            if show_details:
                html_parts.append('<div class="details-section">')
                html_parts.append("<h4>Detailed Results</h4>")

                for case_name, case_models in cases.items():
                    html_parts.append('<div class="case-details">')
                    html_parts.append(f"<h5>{self._escape_html(case_name)}</h5>")

                    for model in model_order:
                        if model not in case_models:
                            continue

                        case_result = case_models[model]
                        evaluation = case_result["evaluation"]

                        html_parts.append('<div class="model-result">')
                        html_parts.append(
                            f"<strong>{self._escape_html(model)}</strong>: Score {evaluation.score * 100:.1f}%"
                        )
                        html_parts.append(self._format_evaluation_details(evaluation))
                        html_parts.append("</div>")

                    html_parts.append("</div>")

                html_parts.append("</div>")

        html_parts.append("</div>")

        # Footer
        html_parts.append("</div>")  # container
        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    def _get_multi_model_styles(self) -> str:
        """Return additional CSS for multi-model views."""
        return """
        <style>
            .models-info { color: #888; margin-bottom: 20px; }
            .multi-model-summary .model-name { font-weight: bold; }
            .multi-model-summary .passed { color: #4caf50; }
            .multi-model-summary .failed { color: #f44336; }
            .multi-model-summary .warned { color: #ff9800; }
            .multi-model-summary .pass-rate { font-weight: bold; }
            .multi-model-summary .best-model { background-color: rgba(76, 175, 80, 0.1); }
            .best-overall { margin-top: 15px; padding: 10px; background: #1e1e1e; border-radius: 4px; }
            .comparison-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            .comparison-table th, .comparison-table td { padding: 10px; border: 1px solid #333; text-align: center; }
            .comparison-table th { background-color: #252525; }
            .comparison-table .case-name { text-align: left; font-weight: bold; }
            .comparison-table .passed { background-color: rgba(76, 175, 80, 0.2); color: #4caf50; }
            .comparison-table .failed { background-color: rgba(244, 67, 54, 0.2); color: #f44336; }
            .comparison-table .warned { background-color: rgba(255, 152, 0, 0.2); color: #ff9800; }
            .comparison-table .no-data { color: #666; }
            .comparison-table .best { color: #ffc107; font-weight: bold; }
            .comparison-table .tie { color: #9e9e9e; }
            .suite-section { margin-bottom: 30px; }
            .details-section { margin-top: 20px; padding: 15px; background: #1a1a1a; border-radius: 4px; }
            .case-details { margin-bottom: 20px; padding: 15px; background: #202020; border-radius: 4px; }
            .model-result { margin: 10px 0; padding: 10px; background: #252525; border-radius: 4px; }
        </style>
        """

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
        """Format comparative evaluation results with tabbed track view."""
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

        # Calculate pass rate
        if total_cases > 0:
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
        else:
            pass_rate = 0

        # Build HTML
        html_parts = [self._get_html_header()]

        # Title and timestamp
        html_parts.append('<div class="container">')
        html_parts.append("<h1>📊 Comparative Evaluation Results</h1>")
        html_parts.append(
            f'<p class="timestamp">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>'
        )

        # Tracks list (only show if there are multiple tracks)
        if len(all_tracks) > 1:
            html_parts.append('<div class="tracks-list">')
            html_parts.append("<strong>All Tracks:</strong>")
            for track in all_tracks:
                html_parts.append(f'<span class="track-badge">{self._escape_html(track)}</span>')
            html_parts.append("</div>")

        # Summary section
        html_parts.append('<div class="summary-section">')
        html_parts.append("<h2>📊 Summary</h2>")

        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            html_parts.append(
                f'<div class="warning-banner">⚠️ Showing only {total_cases} failed evaluation(s)</div>'
            )
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{orig_total}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{orig_passed}</span></div>'
            )
            if orig_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{orig_warned}</span></div>'
                )
            html_parts.append(
                f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{orig_failed}</span></div>'
            )
        else:
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{total_cases}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{total_passed}</span></div>'
            )
            if total_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{total_warned}</span></div>'
                )
            if total_failed > 0:
                html_parts.append(
                    f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{total_failed}</span></div>'
                )

        html_parts.append("</div>")  # stats-grid
        html_parts.append(
            f'<div class="pass-rate">Pass Rate: <strong>{pass_rate:.1f}%</strong></div>'
        )
        html_parts.append("</div>")  # summary-section

        # Results by model
        html_parts.append("<h2>📋 Comparative Results by Model</h2>")

        for model, suites in comparative_groups.items():
            html_parts.append('<div class="model-section">')
            html_parts.append(f"<h3>🤖 {self._escape_html(model)}</h3>")

            for suite_name, cases in suites.items():
                # Get track order for this specific suite
                track_order = suite_track_order.get(suite_name, [])

                html_parts.append('<div class="suite-section">')
                # Only show COMPARATIVE badge if there are multiple tracks
                badge = (
                    '<span class="comparative-badge">COMPARATIVE</span>'
                    if len(track_order) > 1
                    else ""
                )
                html_parts.append(
                    f'<h4 class="suite-header">📁 {self._escape_html(suite_name)} {badge}</h4>'
                )

                # Show tracks for this suite (only if multiple)
                if len(track_order) > 1:
                    html_parts.append('<div class="tracks-list">')
                    html_parts.append("<strong>Tracks:</strong>")
                    for track in track_order:
                        html_parts.append(
                            f'<span class="track-badge">{self._escape_html(track)}</span>'
                        )
                    html_parts.append("</div>")

                for case_name, case_data in cases.items():
                    # Context section (if include_context is True)
                    if include_context:
                        system_msg = case_data.get("system_message")
                        addl_msgs = case_data.get("additional_messages")
                        if system_msg or addl_msgs:
                            html_parts.append('<div class="context-section">')
                            html_parts.append("<h4>📋 Context</h4>")
                            if system_msg:
                                html_parts.append(
                                    f'<div class="context-item">'
                                    f"<strong>System Message:</strong> "
                                    f"<code>{self._escape_html(system_msg)}</code>"
                                    f"</div>"
                                )
                            if addl_msgs:
                                conversation_html = self._format_conversation(addl_msgs)
                                html_parts.append(
                                    f'<details class="context-item conversation-context" open>'
                                    f"<summary>💬 Conversation Context ({len(addl_msgs)} messages)</summary>"
                                    f"{conversation_html}"
                                    f"</details>"
                                )
                            html_parts.append("</div>")

                    html_parts.append(
                        self._format_comparative_case_html(
                            case_name, case_data, track_order, show_details, suite_name
                        )
                    )

                html_parts.append("</div>")  # suite-section

            html_parts.append("</div>")  # model-section

        # JavaScript for tab switching
        html_parts.append(self._get_tab_script())

        html_parts.append("</div>")  # container
        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    def _format_comparative_case_first(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
        include_context: bool = False,
    ) -> str:
        """Format multi-model comparative evaluation grouped by case first."""
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

        # Calculate pass rate
        if total_cases > 0:
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
        else:
            pass_rate = 0

        # Build HTML
        html_parts = [self._get_html_header()]
        html_parts.append(self._get_multi_model_styles())

        html_parts.append('<div class="container">')
        html_parts.append("<h1>📊 Comparative Evaluation Results (Multi-Model)</h1>")
        html_parts.append(
            f'<p class="timestamp">Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</p>'
        )

        # Models and tracks info
        html_parts.append('<div class="info-section">')
        html_parts.append(f"<p><strong>Models:</strong> {', '.join(model_order)}</p>")
        # Only show tracks list if there are multiple tracks
        if len(all_tracks) > 1:
            html_parts.append('<div class="tracks-list">')
            html_parts.append("<strong>Tracks:</strong>")
            for track in all_tracks:
                html_parts.append(f'<span class="track-badge">{self._escape_html(track)}</span>')
            html_parts.append("</div>")
        html_parts.append("</div>")

        # Summary section
        html_parts.append('<div class="summary-section">')
        html_parts.append("<h2>📊 Summary</h2>")

        if failed_only and original_counts:
            orig_total, orig_passed, orig_failed, orig_warned = original_counts
            html_parts.append(
                f'<div class="warning-banner">⚠️ Showing only {total_cases} failed evaluation(s)</div>'
            )
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{orig_total}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{orig_passed}</span></div>'
            )
            if orig_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{orig_warned}</span></div>'
                )
            html_parts.append(
                f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{orig_failed}</span></div>'
            )
        else:
            html_parts.append('<div class="stats-grid">')
            html_parts.append(
                f'<div class="stat-card total"><span class="label">Total</span><span class="value">{total_cases}</span></div>'
            )
            html_parts.append(
                f'<div class="stat-card passed"><span class="label">Passed</span><span class="value">{total_passed}</span></div>'
            )
            if total_warned > 0:
                html_parts.append(
                    f'<div class="stat-card warned"><span class="label">Warnings</span><span class="value">{total_warned}</span></div>'
                )
            if total_failed > 0:
                html_parts.append(
                    f'<div class="stat-card failed"><span class="label">Failed</span><span class="value">{total_failed}</span></div>'
                )

        html_parts.append("</div>")  # stats-grid
        html_parts.append(
            f'<div class="pass-rate">Pass Rate: <strong>{pass_rate:.1f}%</strong></div>'
        )
        html_parts.append("</div>")  # summary-section

        # Results grouped by case
        html_parts.append("<h2>📋 Results by Case</h2>")

        for suite_name, cases in case_groups.items():
            track_order = suite_track_order.get(suite_name, [])

            html_parts.append('<div class="suite-section">')
            # Only show COMPARATIVE badge if there are multiple tracks
            badge = (
                '<span class="comparative-badge">COMPARATIVE</span>' if len(track_order) > 1 else ""
            )
            html_parts.append(
                f'<h3 class="suite-header">📁 {self._escape_html(suite_name)} {badge}</h3>'
            )

            # Show tracks for this suite (only if multiple)
            if len(track_order) > 1:
                html_parts.append('<div class="tracks-list">')
                html_parts.append("<strong>Tracks:</strong>")
                for track in track_order:
                    html_parts.append(
                        f'<span class="track-badge">{self._escape_html(track)}</span>'
                    )
                html_parts.append("</div>")

            for case_name, model_data in cases.items():
                # Case container
                html_parts.append('<div class="case-group">')
                html_parts.append(f"<h4>📋 Case: {self._escape_html(case_name)}</h4>")

                # Get input and context from first model
                first_model_data = next(iter(model_data.values()), {})
                case_input = first_model_data.get("input", "")
                if case_input:
                    html_parts.append(
                        f'<p class="case-input"><strong>Input:</strong> {self._escape_html(case_input)}</p>'
                    )

                # Context section (if include_context is True)
                if include_context:
                    system_msg = first_model_data.get("system_message")
                    addl_msgs = first_model_data.get("additional_messages")
                    if system_msg or addl_msgs:
                        html_parts.append('<div class="context-section">')
                        html_parts.append("<h4>📋 Context</h4>")
                        if system_msg:
                            html_parts.append(
                                f'<div class="context-item">'
                                f"<strong>System Message:</strong> "
                                f"<code>{self._escape_html(system_msg)}</code>"
                                f"</div>"
                            )
                        if addl_msgs:
                            conversation_html = self._format_conversation(addl_msgs)
                            html_parts.append(
                                f'<details class="context-item conversation-context" open>'
                                f"<summary>💬 Conversation Context ({len(addl_msgs)} messages)</summary>"
                                f"{conversation_html}"
                                f"</details>"
                            )
                        html_parts.append("</div>")

                # Show each model's results for this case
                for model in model_order:
                    if model not in model_data:
                        html_parts.append('<div class="model-panel">')
                        html_parts.append(
                            f'<div class="model-label">🤖 {self._escape_html(model)}</div>'
                        )
                        html_parts.append('<div class="no-data">No data</div>')
                        html_parts.append("</div>")
                        continue

                    model_case_data = model_data[model]
                    html_parts.append('<div class="model-panel">')
                    html_parts.append(
                        f'<div class="model-label">🤖 {self._escape_html(model)}</div>'
                    )

                    # Show track comparison for this model
                    html_parts.append(
                        self._format_comparative_case_html(
                            case_name, model_case_data, track_order, show_details, suite_name, model
                        )
                    )

                    html_parts.append("</div>")  # model-panel

                html_parts.append("</div>")  # case-group

            html_parts.append("</div>")  # suite-section

        # JavaScript for tab switching
        html_parts.append(self._get_tab_script())

        html_parts.append("</div>")  # container
        html_parts.append("</body></html>")

        return "\n".join(html_parts)

    def _format_comparative_case_html(
        self,
        case_name: str,
        case_data: ComparativeCaseData,
        track_order: list[str],
        show_details: bool,
        suite_name: str = "",
        model_name: str = "",
    ) -> str:
        """Format a single comparative case as HTML with tabbed details."""
        lines: list[str] = []
        tracks = case_data.get("tracks", {})

        # Compute differences from baseline
        differences = compute_track_differences(case_data, track_order)

        # Generate unique ID for this case's tabs - include suite name and model for uniqueness
        # Sanitize all parts for use in HTML attributes and CSS selectors
        case_id = self._make_safe_id(suite_name, case_name, model_name)

        lines.append('<div class="comparative-case">')

        # Case header
        lines.append('<div class="comparative-case-header">')
        lines.append(f"<h5>{self._escape_html(case_name)}</h5>")
        lines.append(
            f'<p class="case-input"><strong>Input:</strong> '
            f"<code>{self._escape_html(case_data.get('input', 'N/A'))}</code></p>"
        )
        lines.append("</div>")

        # Comparison summary table
        lines.append('<table class="comparison-table">')
        lines.append(
            "<thead><tr><th>Track</th><th>Status</th><th>Score</th><th>Differences</th></tr></thead>"
        )
        lines.append("<tbody>")

        for i, track_name in enumerate(track_order):
            is_baseline = i == 0
            row_class = "baseline" if is_baseline else ""

            if track_name not in tracks:
                lines.append(f'<tr class="{row_class}">')
                lines.append(f"<td><code>{self._escape_html(track_name)}</code></td>")
                lines.append('<td class="status-cell">⚠️ N/A</td>')
                lines.append('<td class="score-cell">—</td>')
                lines.append('<td class="no-diff">No data</td>')
                lines.append("</tr>")
                continue

            track_result = tracks[track_name]
            evaluation = track_result.get("evaluation")

            if not evaluation:
                lines.append(f'<tr class="{row_class}">')
                lines.append(f"<td><code>{self._escape_html(track_name)}</code></td>")
                lines.append('<td class="status-cell">⚠️ N/A</td>')
                lines.append('<td class="score-cell">—</td>')
                lines.append('<td class="no-diff">No evaluation</td>')
                lines.append("</tr>")
                continue

            # Status
            if evaluation.passed:
                status_class = "passed"
                status_text = "✅ PASSED"
            elif evaluation.warning:
                status_class = "warned"
                status_text = "⚠️ WARNED"
            else:
                status_class = "failed"
                status_text = "❌ FAILED"

            # Score
            score_pct = evaluation.score * 100

            # Differences
            diff_fields = differences.get(track_name, [])
            if is_baseline:
                diff_html = '<span class="no-diff">(baseline)</span>'
            elif diff_fields:
                diff_html = " ".join(
                    f'<span class="diff-field">{self._escape_html(f)}</span>' for f in diff_fields
                )
            else:
                diff_html = '<span class="no-diff">—</span>'

            lines.append(f'<tr class="{row_class} {status_class}">')
            lines.append(f"<td><code>{self._escape_html(track_name)}</code></td>")
            lines.append(f'<td class="status-cell">{status_text}</td>')
            lines.append(f'<td class="score-cell">{score_pct:.1f}%</td>')
            lines.append(f"<td>{diff_html}</td>")
            lines.append("</tr>")

        lines.append("</tbody></table>")

        # Detailed results with tabs (if show_details)
        if show_details:
            # Find tracks with data for proper active tab handling
            tracks_with_data = [
                (i, tn)
                for i, tn in enumerate(track_order)
                if tn in tracks and tracks[tn].get("evaluation")
            ]

            # Tab buttons - show all tracks, style N/A differently but keep clickable
            lines.append('<div class="track-tabs">')
            first_with_data = tracks_with_data[0][0] if tracks_with_data else 0
            for i, track_name in enumerate(track_order):
                has_data = track_name in tracks and tracks[track_name].get("evaluation")
                active = "active" if i == first_with_data else ""
                na_class = "" if has_data else "na-track"
                diff_class = "has-diff" if differences.get(track_name) else ""
                lines.append(
                    f'<button class="track-tab {active} {diff_class} {na_class}" '
                    f'data-case="{case_id}" data-track="{i}">'
                    f"{self._escape_html(track_name)}"
                    f"{'' if has_data else ' (N/A)'}"
                    f"</button>"
                )
            lines.append("</div>")  # track-tabs

            # Tab panels container - include panels for ALL tracks
            lines.append('<div class="track-panels-container">')
            for i, track_name in enumerate(track_order):
                has_data = track_name in tracks and tracks[track_name].get("evaluation")
                active = "active" if i == first_with_data else ""

                lines.append(
                    f'<div class="track-panel {active}" data-case="{case_id}" data-track="{i}">'
                )

                if not has_data:
                    # Show informative N/A panel
                    lines.append('<div class="track-panel-header">')
                    lines.append('<span class="track-label">Viewing track:</span>')
                    lines.append(
                        f'<span class="track-badge na-badge">{self._escape_html(track_name)}</span>'
                    )
                    lines.append("</div>")
                    lines.append('<div class="na-panel-content">')
                    lines.append('<div class="na-icon">ℹ</div>')  # noqa: RUF001
                    lines.append("<h4>Track Not Configured</h4>")
                    lines.append(
                        f"<p>The <strong>{self._escape_html(track_name)}</strong> track "
                        f"was not configured for this test case.</p>"
                    )
                    lines.append("<p class='na-explanation'>")
                    lines.append(
                        "This happens when a comparative case uses <code>.for_track()</code> "
                        "to define expectations only for specific tracks. "
                        "Tracks without expectations are skipped during evaluation."
                    )
                    lines.append("</p>")
                    lines.append('<div class="na-hint">')
                    lines.append("<strong>To include this track:</strong>")
                    lines.append("<pre><code>case.for_track(")
                    lines.append(f'    "{self._escape_html(track_name)}",')
                    lines.append("    expected_tool_calls=[...],")
                    lines.append("    critics=[...]")
                    lines.append(")</code></pre>")
                    lines.append("</div>")
                    lines.append("</div>")  # na-panel-content
                else:
                    # Show normal evaluation panel
                    track_result = tracks[track_name]
                    evaluation = track_result.get("evaluation")
                    lines.append('<div class="track-panel-header">')
                    lines.append('<span class="track-label">Viewing track:</span>')
                    lines.append(
                        f'<span class="track-badge">{self._escape_html(track_name)}</span>'
                    )
                    lines.append("</div>")
                    lines.append(self._format_evaluation_details(evaluation))

                lines.append("</div>")  # track-panel
            lines.append("</div>")  # track-panels-container

        lines.append("</div>")  # comparative-case

        return "\n".join(lines)

    def _get_tab_script(self) -> str:
        """Return JavaScript for tab switching."""
        return """
<script>
document.querySelectorAll('.track-tab').forEach(tab => {
    tab.addEventListener('click', function() {
        const caseId = this.dataset.case;
        const trackId = this.dataset.track;

        // Deactivate all tabs and panels for this case
        document.querySelectorAll(`.track-tab[data-case="${caseId}"]`).forEach(t => {
            t.classList.remove('active');
        });
        document.querySelectorAll(`.track-panel[data-case="${caseId}"]`).forEach(p => {
            p.classList.remove('active');
        });

        // Activate clicked tab and corresponding panel
        this.classList.add('active');
        document.querySelector(`.track-panel[data-case="${caseId}"][data-track="${trackId}"]`)
            .classList.add('active');
    });
});
</script>
"""

    def _get_html_header(self) -> str:
        """Return HTML header with embedded CSS for styling."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Results</title>
    <style>
        :root {
            --bg-color: #1e1e2e;
            --text-color: #cdd6f4;
            --card-bg: #313244;
            --border-color: #45475a;
            --green: #a6e3a1;
            --yellow: #f9e2af;
            --red: #f38ba8;
            --blue: #89b4fa;
            --purple: #cba6f7;
            --cyan: #94e2d5;
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            color: var(--purple);
            border-bottom: 2px solid var(--purple);
            padding-bottom: 10px;
        }

        h2 {
            color: var(--blue);
            margin-top: 30px;
        }

        h3 {
            color: var(--cyan);
        }

        h4 {
            color: var(--text-color);
            margin-bottom: 10px;
        }

        .timestamp {
            color: #6c7086;
            font-size: 0.9em;
        }

        .summary-section {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .stats-grid {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin: 15px 0;
        }

        .stat-card {
            background: var(--bg-color);
            padding: 15px 25px;
            border-radius: 8px;
            text-align: center;
            min-width: 100px;
            border: 2px solid;
        }

        .stat-card .label {
            display: block;
            font-size: 0.85em;
            color: #a6adc8;
            margin-bottom: 5px;
        }

        .stat-card .value {
            display: block;
            font-size: 1.8em;
            font-weight: bold;
        }

        .stat-card.total { border-color: var(--blue); }
        .stat-card.total .value { color: var(--blue); }

        .stat-card.passed { border-color: var(--green); }
        .stat-card.passed .value { color: var(--green); }

        .stat-card.warned { border-color: var(--yellow); }
        .stat-card.warned .value { color: var(--yellow); }

        .stat-card.failed { border-color: var(--red); }
        .stat-card.failed .value { color: var(--red); }

        .pass-rate {
            font-size: 1.2em;
            margin-top: 15px;
        }

        .pass-rate strong {
            color: var(--green);
        }

        .warning-banner {
            background: #45475a;
            color: var(--yellow);
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            border-left: 4px solid var(--yellow);
        }

        .model-section {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .suite-section {
            background: rgba(0, 0, 0, 0.15);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 3px solid var(--cyan);
        }

        .suite-header {
            color: var(--cyan);
            margin: 0 0 15px 0;
            font-size: 1.1em;
        }

        .expand-hint {
            color: #6c7086;
            font-size: 0.85em;
            font-style: italic;
            margin: 10px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background: var(--bg-color);
            color: var(--purple);
            font-weight: 600;
        }

        .results-table tr.passed { background: rgba(166, 227, 161, 0.1); }
        .results-table tr.warned { background: rgba(249, 226, 175, 0.1); }
        .results-table tr.failed { background: rgba(243, 139, 168, 0.1); }

        .results-table tr.passed .status-cell { color: var(--green); }
        .results-table tr.warned .status-cell { color: var(--yellow); }
        .results-table tr.failed .status-cell { color: var(--red); }

        .score-cell {
            font-weight: bold;
            color: var(--blue);
        }

        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }

        .badge.passed { background: var(--green); color: #1e1e2e; }
        .badge.warned { background: var(--yellow); color: #1e1e2e; }
        .badge.failed { background: var(--red); color: #1e1e2e; }

        .case-detail {
            background: var(--bg-color);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid;
        }

        .case-detail.passed { border-left-color: var(--green); }
        .case-detail.warned { border-left-color: var(--yellow); }
        .case-detail.failed { border-left-color: var(--red); }

        code {
            background: var(--bg-color);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: var(--cyan);
        }

        details {
            margin-top: 15px;
        }

        summary {
            cursor: pointer;
            padding: 10px;
            background: var(--bg-color);
            border-radius: 5px;
            font-weight: bold;
            color: var(--blue);
        }

        summary:hover {
            background: #45475a;
        }

        .detail-table {
            font-size: 0.9em;
        }

        .field-name {
            color: var(--purple);
            font-weight: 600;
        }

        .match-yes { color: var(--green); font-weight: bold; }
        .match-no { color: var(--red); font-weight: bold; }
        .uncriticized { color: var(--yellow); }

        .match-row { background: rgba(166, 227, 161, 0.05); }
        .nomatch-row { background: rgba(243, 139, 168, 0.1); }
        .uncriticized-row { background: rgba(249, 226, 175, 0.05); }

        .failure-reason {
            background: rgba(243, 139, 168, 0.2);
            border: 1px solid var(--red);
            padding: 15px;
            border-radius: 8px;
            color: var(--red);
        }

        /* Expandable case results */
        .details-header {
            color: var(--blue);
            margin-bottom: 15px;
        }

        .case-expandable {
            margin: 8px 0;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }

        .case-expandable.passed { border-left: 4px solid var(--green); }
        .case-expandable.warned { border-left: 4px solid var(--yellow); }
        .case-expandable.failed { border-left: 4px solid var(--red); }

        .case-summary {
            padding: 12px 15px;
            background: var(--bg-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: normal;
        }

        .case-summary:hover {
            background: #45475a;
        }

        .case-expandable.passed .case-summary { border-left-color: var(--green); }
        .case-expandable.warned .case-summary { border-left-color: var(--yellow); }
        .case-expandable.failed .case-summary { border-left-color: var(--red); }

        .score-inline {
            color: var(--blue);
            font-weight: bold;
            margin-left: auto;
            margin-right: 10px;
        }

        .case-content {
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-top: 1px solid var(--border-color);
        }

        .case-expandable[open] .case-summary {
            border-bottom: 1px solid var(--border-color);
        }

        @media (max-width: 768px) {
            .stats-grid {
                flex-direction: column;
            }
            .stat-card {
                width: 100%;
            }
            table {
                font-size: 0.85em;
            }
        }

        /* Comparative evaluation styles */
        .comparative-badge {
            background: var(--purple);
            color: #1e1e2e;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-left: 10px;
        }

        .tracks-list {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 15px 0;
        }

        .track-badge {
            background: var(--card-bg);
            border: 1px solid var(--cyan);
            color: var(--cyan);
            padding: 5px 12px;
            border-radius: 4px;
            font-family: monospace;
        }

        .comparative-case {
            background: var(--bg-color);
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }

        .comparative-case-header {
            background: var(--card-bg);
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
        }

        .comparative-case-header h5 {
            margin: 0 0 10px 0;
            color: var(--purple);
        }

        .case-input {
            font-size: 0.9em;
            color: #a6adc8;
        }

        .comparison-table {
            width: 100%;
            margin: 0;
        }

        .comparison-table th {
            background: rgba(0, 0, 0, 0.3);
        }

        .comparison-table tr.baseline td:first-child::after {
            content: " (baseline)";
            font-size: 0.8em;
            color: #6c7086;
        }

        .diff-field {
            background: rgba(249, 226, 175, 0.2);
            color: var(--yellow);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.85em;
            margin: 0 2px;
        }

        .track-tabs {
            display: flex;
            gap: 4px;
            padding: 0 15px;
            padding-top: 12px;
            background: transparent;
            margin-bottom: -1px;
            position: relative;
            z-index: 1;
        }

        .track-tab {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 10px 20px;
            border-radius: 6px 6px 0 0;
            cursor: pointer;
            font-family: monospace;
            font-weight: 500;
            transition: all 0.15s ease;
            opacity: 0.6;
            position: relative;
        }

        .track-tab:hover {
            background: #45475a;
            opacity: 0.9;
        }

        .track-tab.active {
            background: var(--bg-color);
            border-color: var(--purple);
            border-bottom-color: var(--bg-color);
            color: var(--purple);
            font-weight: 700;
            opacity: 1;
            z-index: 2;
        }

        .track-tab.has-diff {
            border-color: var(--yellow);
        }

        .track-tab.has-diff.active {
            border-color: var(--purple);
            border-bottom-color: var(--bg-color);
        }

        .track-tab.na-track {
            opacity: 0.6;
            background: #2a2a3a;
            color: #888;
            border-style: dashed;
        }

        .track-tab.na-track:hover {
            background: #3a3a4a;
            opacity: 0.8;
            color: #aaa;
        }

        .track-tab.na-track.active {
            background: var(--bg-color);
            border-bottom-color: var(--bg-color);
            opacity: 1;
            color: #999;
        }

        .track-panels-container {
            border: 1px solid var(--purple);
            border-radius: 0 6px 6px 6px;
            background: var(--bg-color);
        }

        .track-panel {
            display: none;
            padding: 15px;
        }

        .track-panel.active {
            display: block;
            animation: fadeIn 0.15s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .track-panel-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px dashed var(--border-color);
        }

        .track-panel-header .track-badge {
            background: var(--purple);
            color: #1e1e2e;
            padding: 4px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-weight: 600;
            font-size: 0.9em;
        }

        .track-panel-header .track-label {
            color: var(--text-muted);
            font-size: 0.85em;
        }

        .track-panel-header .na-badge {
            background: #4a4a5a;
            color: #999;
            border: 1px dashed #666;
        }

        /* N/A Panel Content Styles */
        .na-panel-content {
            text-align: center;
            padding: 30px 20px;
            color: var(--text-muted);
        }

        .na-panel-content .na-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
            opacity: 0.8;
        }

        .na-panel-content h4 {
            color: var(--text-color);
            margin: 0 0 10px 0;
            font-size: 1.2em;
        }

        .na-panel-content p {
            margin: 10px auto;
            max-width: 500px;
            line-height: 1.5;
        }

        .na-panel-content .na-explanation {
            font-size: 0.9em;
            color: #666;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin: 15px auto;
            max-width: 550px;
        }

        .na-panel-content .na-hint {
            background: rgba(168, 85, 247, 0.1);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 8px;
            padding: 15px;
            margin: 20px auto;
            max-width: 400px;
            text-align: left;
        }

        .na-panel-content .na-hint strong {
            color: var(--purple);
            display: block;
            margin-bottom: 10px;
        }

        .na-panel-content .na-hint pre {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 4px;
            margin: 0;
            overflow-x: auto;
            font-size: 0.85em;
        }

        .na-panel-content .na-hint code {
            color: var(--cyan);
        }

        .no-diff {
            color: #6c7086;
        }

        /* Context section styles for --include-context */
        .context-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            border-left: 3px solid var(--purple);
        }

        .context-section h4 {
            margin: 0 0 10px 0;
            color: var(--purple);
        }

        .context-item {
            margin: 10px 0;
            padding: 10px;
            background: var(--card-bg);
            border-radius: 5px;
        }

        .context-item code {
            display: block;
            white-space: pre-wrap;
            word-break: break-word;
            margin-top: 5px;
        }

        .conversation-context summary {
            background: var(--card-bg);
            padding: 8px 12px;
            border-radius: 5px;
            cursor: pointer;
            color: var(--cyan);
        }

        /* Conversation message styles */
        .conversation {
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 10px;
        }

        .msg {
            padding: 12px 15px;
            border-radius: 8px;
            background: var(--card-bg);
            border-left: 3px solid var(--border-color);
        }

        .msg-user {
            border-left-color: var(--blue);
            background: rgba(137, 180, 250, 0.1);
        }

        .msg-assistant {
            border-left-color: var(--green);
            background: rgba(166, 227, 161, 0.1);
        }

        .msg-tool {
            border-left-color: var(--yellow);
            background: rgba(249, 226, 175, 0.1);
        }

        .msg-system {
            border-left-color: var(--purple);
            background: rgba(203, 166, 247, 0.1);
        }

        .msg-role {
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 0.9em;
        }

        .msg-content {
            color: var(--text-color);
            line-height: 1.5;
        }

        .tool-calls {
            margin-top: 10px;
        }

        .tool-call-item {
            background: var(--bg-color);
            padding: 10px;
            border-radius: 5px;
            margin-top: 8px;
        }

        .tool-call-name {
            font-family: monospace;
            color: var(--cyan);
            font-weight: bold;
        }

        .tool-call-args {
            background: var(--bg-color);
            padding: 8px;
            border-radius: 4px;
            font-size: 0.85em;
            margin-top: 5px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
        }

        .tool-response {
            background: linear-gradient(135deg, rgba(46, 204, 113, 0.1), rgba(39, 174, 96, 0.05));
            border: 1px solid rgba(46, 204, 113, 0.3);
            border-left: 3px solid var(--green);
            padding: 12px;
            border-radius: 6px;
            font-size: 0.85em;
            overflow-x: auto;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 8px 0;
        }
    </style>
</head>
<body>
"""


class CaptureHtmlFormatter(CaptureFormatter):
    """HTML formatter for capture results."""

    @property
    def file_extension(self) -> str:
        return "html"

    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format capture results as HTML."""
        # Check for multi-model captures
        if is_multi_model_capture(captures):
            return self._format_multi_model(captures, include_context)

        return self._format_single_model(captures, include_context)

    def _format_single_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format single-model capture results as HTML."""
        total_cases = 0
        total_calls = 0

        # Build captures HTML
        captures_html = []
        for capture in captures:
            cases_html = []
            for case in capture.captured_cases:
                total_cases += 1
                tool_calls_html = []

                for tc in case.tool_calls:
                    total_calls += 1
                    args_html = ""
                    if tc.args:
                        args_json = json.dumps(tc.args, indent=2)
                        args_html = f'<pre class="args">{self._escape_html(args_json)}</pre>'
                    tool_calls_html.append(
                        f'<div class="tool-call">'
                        f'<span class="tool-name">{self._escape_html(tc.name)}</span>'
                        f"{args_html}"
                        f"</div>"
                    )

                if not tool_calls_html:
                    tool_calls_html.append('<div class="no-calls">No tool calls captured</div>')

                context_html = ""
                if include_context:
                    context_parts = []
                    if case.system_message:
                        context_parts.append(
                            f'<div class="context-item">'
                            f"<strong>System Message:</strong> "
                            f"{self._escape_html(case.system_message)}"
                            f"</div>"
                        )
                    if case.additional_messages:
                        conversation_html = self._format_conversation(case.additional_messages)
                        context_parts.append(
                            f'<details class="context-item conversation-context" open>'
                            f"<summary>💬 Conversation Context ({len(case.additional_messages)} messages)</summary>"
                            f"{conversation_html}"
                            f"</details>"
                        )
                    if context_parts:
                        context_html = f'<div class="context">{"".join(context_parts)}</div>'

                # track_name is set for comparative cases
                track_name = getattr(case, "track_name", None)
                track_html = ""
                if track_name:
                    track_html = f'<span class="track-badge">{self._escape_html(track_name)}</span>'

                cases_html.append(
                    f'<div class="case">'
                    f'<h3 class="case-name">{self._escape_html(case.case_name)} {track_html}</h3>'
                    f'<div class="user-message">'
                    f"<strong>User:</strong> {self._escape_html(case.user_message)}"
                    f"</div>"
                    f"{context_html}"
                    f'<div class="tool-calls"><h4>Tool Calls</h4>{"".join(tool_calls_html)}</div>'
                    f"</div>"
                )

            captures_html.append(
                f'<div class="capture">'
                f'<h2 class="suite-name">{self._escape_html(capture.suite_name)}</h2>'
                f'<div class="meta">'
                f"<span>Model: <strong>{self._escape_html(capture.model)}</strong></span>"
                f"<span>Provider: <strong>{self._escape_html(capture.provider)}</strong></span>"
                f"</div>"
                f'<div class="cases">{"".join(cases_html)}</div>'
                f"</div>"
            )

        return self._get_capture_html(captures_html, total_cases, total_calls)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format conversation messages as a rich HTML conversation view."""
        html_parts = ['<div class="conversation">']

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            name = msg.get("name", "")

            # Role-specific styling
            role_class = f"msg-{role}"
            role_icon = {
                "user": "👤",
                "assistant": "🤖",
                "tool": "🔧",
                "system": "⚙️",
            }.get(role, "💬")
            role_label = role.capitalize()

            html_parts.append(f'<div class="msg {role_class}">')
            html_parts.append(
                f'<div class="msg-header">'
                f'<span class="msg-icon">{role_icon}</span>'
                f'<span class="msg-role">{role_label}</span>'
            )

            # Show tool name for tool responses
            if role == "tool" and name:
                html_parts.append(f'<span class="msg-tool-name">({self._escape_html(name)})</span>')

            html_parts.append("</div>")  # Close msg-header

            # Message content
            if content:
                # For tool responses, try to format JSON nicely
                if role == "tool":
                    try:
                        parsed_content = json.loads(content)
                        formatted_content = json.dumps(parsed_content, indent=2)
                        html_parts.append(
                            f'<pre class="tool-response">{self._escape_html(formatted_content)}</pre>'
                        )
                    except (json.JSONDecodeError, TypeError):
                        # Not valid JSON, show as regular content
                        html_parts.append(
                            f'<div class="msg-content">{self._escape_html(str(content))}</div>'
                        )
                else:
                    html_parts.append(
                        f'<div class="msg-content">{self._escape_html(str(content))}</div>'
                    )

            # Tool calls (for assistant messages)
            if tool_calls:
                html_parts.append('<div class="msg-tool-calls">')
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

                    html_parts.append(
                        f'<div class="tool-call-inline">'
                        f'<span class="tool-call-name">📞 {self._escape_html(tc_name)}</span>'
                        f'<pre class="tool-call-args">{self._escape_html(args_formatted)}</pre>'
                        f"</div>"
                    )
                html_parts.append("</div>")

            html_parts.append("</div>")  # Close msg

        html_parts.append("</div>")  # Close conversation
        return "\n".join(html_parts)

    def _format_multi_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format multi-model capture results with track tabs."""
        from arcade_cli.formatters.base import group_captures_by_case_then_track

        grouped_data, model_order, track_order = group_captures_by_case_then_track(captures)

        html_parts: list[str] = []

        # HTML head with track tab styles
        html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Model Capture Results</title>
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --border: #30363d;
            --accent: #58a6ff;
            --success: #3fb950;
            --purple: #a855f7;
            --code-bg: #1f2428;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }
        h1 { color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 1rem; margin-bottom: 2rem; }
        h2 { color: var(--text-primary); margin: 1.5rem 0 1rem; }
        h3 { color: var(--accent); margin-bottom: 1rem; }
        h4 { color: var(--text-secondary); margin: 0.5rem 0; }
        .models-info { color: var(--text-secondary); margin-bottom: 1.5rem; }
        .suite-section {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        .case-group {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 1.5rem;
            padding: 1rem;
        }
        .case-header {
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.75rem;
            margin-bottom: 1rem;
        }
        /* Track tabs */
        .track-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: -1px;
            position: relative;
            z-index: 1;
        }
        .track-tab {
            padding: 8px 16px;
            border: 1px solid var(--border);
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.85rem;
            font-family: 'SFMono-Regular', Consolas, monospace;
            transition: all 0.2s ease;
        }
        .track-tab:hover {
            background: var(--bg-secondary);
            color: var(--text-primary);
        }
        .track-tab.active {
            background: var(--purple);
            color: white;
            font-weight: bold;
            border-color: var(--purple);
            box-shadow: 0 -2px 10px rgba(168, 85, 247, 0.3);
        }
        .track-panels {
            border: 1px solid var(--border);
            border-radius: 0 8px 8px 8px;
            background: var(--bg-secondary);
            padding: 1rem;
        }
        .track-panel {
            display: none;
        }
        .track-panel.active {
            display: block;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .track-indicator {
            display: inline-block;
            padding: 4px 10px;
            background: var(--purple);
            color: white;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: 'SFMono-Regular', Consolas, monospace;
            margin-bottom: 0.75rem;
        }
        .model-panel {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 4px;
            margin-bottom: 1rem;
            padding: 1rem;
        }
        .model-label {
            font-weight: bold;
            color: var(--accent);
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }
        .tool-call {
            background: var(--code-bg);
            border-radius: 4px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
        }
        .tool-name {
            color: var(--success);
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-weight: 600;
        }
        .args {
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.85rem;
            margin-top: 0.5rem;
            color: var(--text-secondary);
            white-space: pre-wrap;
        }
        .no-calls { color: var(--text-secondary); font-style: italic; }
        .no-track-data {
            color: var(--text-secondary);
            font-style: italic;
            padding: 1rem;
            text-align: center;
        }
        .summary {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        .context-section {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }
        /* Conversation styles */
        .conversation {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 1rem;
        }
        .msg {
            border-radius: 8px;
            padding: 0.75rem 1rem;
            border-left: 3px solid var(--border);
        }
        .msg-user {
            background: linear-gradient(135deg, #1a365d 0%, #153e75 100%);
            border-left-color: #4299e1;
        }
        .msg-assistant {
            background: linear-gradient(135deg, #22543d 0%, #276749 100%);
            border-left-color: #48bb78;
        }
        .msg-tool {
            background: linear-gradient(135deg, #553c9a 0%, #6b46c1 100%);
            border-left-color: #9f7aea;
        }
        .msg-system {
            background: linear-gradient(135deg, #744210 0%, #975a16 100%);
            border-left-color: #ed8936;
        }
        .msg-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
        }
        .msg-icon { font-size: 1rem; }
        .msg-role {
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .msg-tool-name {
            color: var(--text-secondary);
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.8rem;
        }
        .msg-content {
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }
        .msg-tool-calls { margin-top: 0.5rem; }
        .tool-call-inline {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            padding: 0.5rem;
            margin-top: 0.5rem;
        }
        .tool-call-name {
            color: var(--accent);
            font-weight: 600;
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.9rem;
        }
        .tool-call-args {
            margin-top: 0.5rem;
            font-size: 0.8rem;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.5rem;
            border-radius: 4px;
        }
        .tool-response {
            background: linear-gradient(135deg, rgba(46, 204, 113, 0.1), rgba(39, 174, 96, 0.05));
            border: 1px solid rgba(46, 204, 113, 0.3);
            border-left: 3px solid #2ecc71;
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.85em;
            overflow-x: auto;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0.5rem 0;
        }
    </style>
</head>
<body>
""")

        html_parts.append("<h1>🔄 Multi-Model Capture Results</h1>")
        html_parts.append(
            f'<p class="models-info">Models: {", ".join(self._escape_html(m) for m in model_order)}</p>'
        )

        total_cases = 0
        total_calls = 0
        case_idx = 0

        for suite_name, cases in grouped_data.items():
            html_parts.append('<div class="suite-section">')
            html_parts.append(f"<h2>{self._escape_html(suite_name)}</h2>")

            for case_name, case_data in cases.items():
                total_cases += 1
                case_idx += 1
                case_id = f"case_{case_idx}"
                html_parts.append('<div class="case-group">')

                user_msg = case_data.get("user_message", "")
                tracks_data = case_data.get("tracks", {})

                html_parts.append('<div class="case-header">')
                html_parts.append(f"<h3>{self._escape_html(case_name)}</h3>")
                if user_msg:
                    html_parts.append(
                        f"<p><strong>User:</strong> {self._escape_html(user_msg)}</p>"
                    )
                html_parts.append("</div>")

                # Check if we have multiple tracks
                track_keys = list(tracks_data.keys())
                has_multiple_tracks = len(track_keys) > 1 or (
                    len(track_keys) == 1 and track_keys[0] != "_default"
                )

                if has_multiple_tracks:
                    # Render track tabs
                    html_parts.append('<div class="track-tabs">')
                    for i, track_key in enumerate(track_keys):
                        active = "active" if i == 0 else ""
                        display_name = track_key if track_key != "_default" else "Default"
                        html_parts.append(
                            f'<button class="track-tab {active}" '
                            f'data-case="{case_id}" data-track="{i}">'
                            f"{self._escape_html(display_name)}</button>"
                        )
                    html_parts.append("</div>")

                    # Render track panels
                    html_parts.append('<div class="track-panels">')
                    for i, track_key in enumerate(track_keys):
                        active = "active" if i == 0 else ""
                        track_data = tracks_data[track_key]
                        html_parts.append(
                            f'<div class="track-panel {active}" '
                            f'data-case="{case_id}" data-track="{i}">'
                        )

                        display_name = track_key if track_key != "_default" else "Default"
                        html_parts.append(
                            f'<div class="track-indicator">🏷️ {self._escape_html(display_name)}</div>'
                        )

                        # Render model panels within track
                        models_dict = track_data.get("models", {})
                        for model in model_order:
                            if model not in models_dict:
                                html_parts.append('<div class="model-panel">')
                                html_parts.append(
                                    f'<div class="model-label">{self._escape_html(model)}</div>'
                                )
                                html_parts.append('<div class="no-calls">No data</div>')
                                html_parts.append("</div>")
                                continue

                            captured_case = models_dict[model]
                            html_parts.append('<div class="model-panel">')
                            html_parts.append(
                                f'<div class="model-label">{self._escape_html(model)}</div>'
                            )

                            if captured_case.tool_calls:
                                for tc in captured_case.tool_calls:
                                    total_calls += 1
                                    args_html = ""
                                    if tc.args:
                                        args_json = json.dumps(tc.args, indent=2)
                                        args_html = f'<pre class="args">{self._escape_html(args_json)}</pre>'
                                    html_parts.append(
                                        f'<div class="tool-call">'
                                        f'<span class="tool-name">{self._escape_html(tc.name)}</span>'
                                        f"{args_html}</div>"
                                    )
                            else:
                                html_parts.append('<div class="no-calls">No tool calls</div>')

                            html_parts.append("</div>")  # model-panel

                        html_parts.append("</div>")  # track-panel
                    html_parts.append("</div>")  # track-panels
                else:
                    # No tracks - render models directly
                    track_key = track_keys[0] if track_keys else "_default"
                    track_data = tracks_data.get(track_key, {})
                    models_dict = track_data.get("models", {})

                    for model in model_order:
                        if model not in models_dict:
                            html_parts.append('<div class="model-panel">')
                            html_parts.append(
                                f'<div class="model-label">{self._escape_html(model)}</div>'
                            )
                            html_parts.append('<div class="no-calls">No data</div>')
                            html_parts.append("</div>")
                            continue

                        captured_case = models_dict[model]
                        html_parts.append('<div class="model-panel">')
                        html_parts.append(
                            f'<div class="model-label">{self._escape_html(model)}</div>'
                        )

                        if captured_case.tool_calls:
                            for tc in captured_case.tool_calls:
                                total_calls += 1
                                args_html = ""
                                if tc.args:
                                    args_json = json.dumps(tc.args, indent=2)
                                    args_html = (
                                        f'<pre class="args">{self._escape_html(args_json)}</pre>'
                                    )
                                html_parts.append(
                                    f'<div class="tool-call">'
                                    f'<span class="tool-name">{self._escape_html(tc.name)}</span>'
                                    f"{args_html}</div>"
                                )
                        else:
                            html_parts.append('<div class="no-calls">No tool calls</div>')

                        html_parts.append("</div>")

                # Context section
                system_msg = case_data.get("system_message")
                addl_msgs = case_data.get("additional_messages")
                if include_context and (system_msg or addl_msgs):
                    html_parts.append('<div class="context-section">')
                    html_parts.append("<h4>Context</h4>")
                    if system_msg:
                        html_parts.append(
                            f"<p><strong>System:</strong> {self._escape_html(system_msg)}</p>"
                        )
                    if addl_msgs:
                        html_parts.append(self._format_conversation(addl_msgs))
                    html_parts.append("</div>")

                html_parts.append("</div>")  # case-group

            html_parts.append("</div>")  # suite-section

        # Summary
        total_suites = len(grouped_data)
        html_parts.append(f"""
<div class="summary">
    <h2>Summary</h2>
    <p>Suites: {total_suites} | Cases: {total_cases} | Models: {len(model_order)} | Tool Calls: {total_calls}</p>
</div>

<script>
document.querySelectorAll('.track-tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
        const caseId = tab.dataset.case;
        const trackId = tab.dataset.track;

        // Update tab states
        document.querySelectorAll(`.track-tab[data-case="${{caseId}}"]`).forEach(t => {{
            t.classList.remove('active');
        }});
        tab.classList.add('active');

        // Update panel states
        document.querySelectorAll(`.track-panel[data-case="${{caseId}}"]`).forEach(p => {{
            p.classList.remove('active');
        }});
        document.querySelector(`.track-panel[data-case="${{caseId}}"][data-track="${{trackId}}"]`)
            ?.classList.add('active');
    }});
}});
</script>
</body>
</html>
""")

        return "\n".join(html_parts)

    def _get_capture_html(
        self, captures_html: list[str], total_cases: int, total_calls: int
    ) -> str:
        """Return complete HTML document for capture results."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Capture Results</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --border: #30363d;
            --accent: #58a6ff;
            --success: #3fb950;
            --code-bg: #1f2428;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        h1 {{
            color: var(--accent);
            border-bottom: 2px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }}
        .capture {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 2rem;
            padding: 1.5rem;
        }}
        .suite-name {{
            color: var(--accent);
            margin-bottom: 0.5rem;
        }}
        .meta {{
            color: var(--text-secondary);
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }}
        .case {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 1rem;
            padding: 1rem;
        }}
        .case-name {{
            color: var(--success);
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}
        .track-badge {{
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            border: none;
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: bold;
            font-family: 'SFMono-Regular', Consolas, monospace;
            margin-left: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            box-shadow: 0 2px 8px rgba(168, 85, 247, 0.3);
            vertical-align: middle;
        }}
        .user-message {{
            background: var(--bg-primary);
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }}
        .tool-calls h4 {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        .tool-call {{
            background: var(--bg-primary);
            border-left: 3px solid var(--accent);
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 0 4px 4px 0;
        }}
        .tool-name {{
            color: var(--accent);
            font-weight: 600;
            font-family: 'SFMono-Regular', Consolas, monospace;
        }}
        .args, pre {{
            background: var(--code-bg);
            padding: 0.75rem;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }}
        .no-calls {{
            color: var(--text-secondary);
            font-style: italic;
        }}
        .context {{
            margin: 1rem 0;
            padding: 0.75rem;
            background: var(--bg-primary);
            border-radius: 4px;
        }}
        .context-item {{
            margin-bottom: 0.5rem;
        }}
        details summary {{
            cursor: pointer;
            color: var(--accent);
        }}
        .summary {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        .summary h2 {{
            color: var(--accent);
            margin-bottom: 1rem;
        }}
        .stats {{
            display: flex;
            gap: 2rem;
        }}
        .stat {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--success);
        }}
        .stat-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        /* Conversation styles */
        .conversation {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            margin-top: 1rem;
        }}
        .msg {{
            border-radius: 8px;
            padding: 0.75rem 1rem;
            border-left: 3px solid var(--border);
        }}
        .msg-user {{
            background: linear-gradient(135deg, #1a365d 0%, #153e75 100%);
            border-left-color: #4299e1;
        }}
        .msg-assistant {{
            background: linear-gradient(135deg, #22543d 0%, #276749 100%);
            border-left-color: #48bb78;
        }}
        .msg-tool {{
            background: linear-gradient(135deg, #553c9a 0%, #6b46c1 100%);
            border-left-color: #9f7aea;
        }}
        .msg-system {{
            background: linear-gradient(135deg, #744210 0%, #975a16 100%);
            border-left-color: #ed8936;
        }}
        .msg-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
        }}
        .msg-icon {{
            font-size: 1rem;
        }}
        .msg-role {{
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .msg-tool-name {{
            color: var(--text-secondary);
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.8rem;
        }}
        .msg-content {{
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .msg-tool-calls {{
            margin-top: 0.5rem;
        }}
        .tool-call-inline {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            padding: 0.5rem;
            margin-top: 0.5rem;
        }}
        .tool-call-name {{
            color: var(--accent);
            font-weight: 600;
            font-family: 'SFMono-Regular', Consolas, monospace;
            font-size: 0.9rem;
        }}
        .tool-call-args {{
            margin-top: 0.5rem;
            font-size: 0.8rem;
            background: rgba(0, 0, 0, 0.3);
        }}
        .tool-response {{
            background: linear-gradient(135deg, rgba(46, 204, 113, 0.1), rgba(39, 174, 96, 0.05));
            border: 1px solid rgba(46, 204, 113, 0.3);
            border-left: 3px solid #2ecc71;
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.85em;
            overflow-x: auto;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0.5rem 0;
        }}
        .conversation-context summary {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <h1>🎯 Capture Results</h1>
    {"".join(captures_html)}
    <div class="summary">
        <h2>Summary</h2>
        <div class="stats">
            <div>
                <div class="stat">{total_cases}</div>
                <div class="stat-label">Total Cases</div>
            </div>
            <div>
                <div class="stat">{total_calls}</div>
                <div class="stat-label">Tool Calls</div>
            </div>
        </div>
    </div>
</body>
</html>"""
