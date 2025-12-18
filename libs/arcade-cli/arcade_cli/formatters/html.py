"""HTML formatter for evaluation results with full color support."""

from datetime import datetime, timezone
from typing import Any

from arcade_cli.formatters.base import (
    EvalResultFormatter,
    group_results_by_model,
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

    @property
    def file_extension(self) -> str:
        return "html"

    def format(
        self,
        results: list[list[dict[str, Any]]],
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: tuple[int, int, int, int] | None = None,
    ) -> str:
        # Use shared grouping logic
        model_groups, total_passed, total_failed, total_warned, total_cases = (
            group_results_by_model(results)
        )

        # Calculate pass rate
        if total_cases > 0:
            if failed_only and original_counts:
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
    </style>
</head>
<body>
"""
