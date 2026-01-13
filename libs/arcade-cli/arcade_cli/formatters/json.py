"""JSON formatter for evaluation and capture results."""

import json
from datetime import datetime, timezone
from typing import Any

from arcade_cli.formatters.base import (
    CaptureFormatter,
    CaptureResults,
    EvalResultFormatter,
    EvalResults,
    EvalStats,
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


class JsonFormatter(EvalResultFormatter):
    """
    JSON formatter for evaluation results.

    Produces a structured JSON document containing all evaluation data,
    suitable for programmatic processing, dashboards, or further analysis.
    """

    @property
    def file_extension(self) -> str:
        return "json"

    def format(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> str:
        """Format evaluation results as JSON."""
        # Check if this is a comparative evaluation
        if is_comparative_result(results):
            output = self._format_comparative(
                results, show_details, failed_only, original_counts, include_context
            )
        elif is_multi_model_eval(results):
            output = self._format_multi_model(
                results, show_details, failed_only, original_counts, include_context
            )
        else:
            output = self._format_regular(
                results, show_details, failed_only, original_counts, include_context
            )

        return json.dumps(output, indent=2, default=str)

    def _format_regular(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """Format regular (non-comparative) evaluation results."""
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

        output: dict[str, Any] = {
            "type": "evaluation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_cases": total_cases,
                "passed": total_passed,
                "failed": total_failed,
                "warned": total_warned,
                "pass_rate": round(pass_rate, 2),
            },
            "models": {},
        }

        if failed_only and original_counts:
            output["summary"]["original_counts"] = {
                "total": original_counts[0],
                "passed": original_counts[1],
                "failed": original_counts[2],
                "warned": original_counts[3],
            }
            output["summary"]["filtered"] = True

        # Build model results
        for model, suites in model_groups.items():
            output["models"][model] = {"suites": {}}

            for suite_name, cases in suites.items():
                suite_data: dict[str, Any] = {
                    "case_count": len(cases),
                    "cases": [],
                }

                for case in cases:
                    case_data = self._serialize_case(case, show_details, include_context)
                    suite_data["cases"].append(case_data)

                output["models"][model]["suites"][suite_name] = suite_data

        return output

    def _format_comparative(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """Format comparative evaluation results."""
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
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """Format single-model comparative evaluation results."""
        (
            comparative_groups,
            total_passed,
            total_failed,
            total_warned,
            total_cases,
            suite_track_order,
        ) = group_comparative_by_case(results)

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

        output: dict[str, Any] = {
            "type": "comparative_evaluation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tracks": all_tracks,
            "summary": {
                "total_cases": total_cases,
                "passed": total_passed,
                "failed": total_failed,
                "warned": total_warned,
                "pass_rate": round(pass_rate, 2),
            },
            "models": {},
        }

        if failed_only and original_counts:
            output["summary"]["original_counts"] = {
                "total": original_counts[0],
                "passed": original_counts[1],
                "failed": original_counts[2],
                "warned": original_counts[3],
            }
            output["summary"]["filtered"] = True

        # Build model results
        for model, suites in comparative_groups.items():
            output["models"][model] = {"suites": {}}

            for suite_name, cases in suites.items():
                track_order = suite_track_order.get(suite_name, [])

                suite_data: dict[str, Any] = {
                    "tracks": track_order,
                    "case_count": len(cases),
                    "cases": {},
                }

                for case_name, case_data in cases.items():
                    tracks_data = case_data.get("tracks", {})

                    case_output: dict[str, Any] = {
                        "input": case_data.get("input", ""),
                        "tracks": {},
                    }

                    # Add context if requested
                    if include_context:
                        system_msg = case_data.get("system_message")
                        addl_msgs = case_data.get("additional_messages")
                        if system_msg:
                            case_output["system_message"] = system_msg
                        if addl_msgs:
                            case_output["additional_messages"] = addl_msgs

                    for track_name in track_order:
                        if track_name not in tracks_data:
                            case_output["tracks"][track_name] = {"status": "missing"}
                            continue

                        track_result = tracks_data[track_name]
                        evaluation = track_result.get("evaluation")

                        if not evaluation:
                            case_output["tracks"][track_name] = {"status": "no_evaluation"}
                            continue

                        track_data: dict[str, Any] = {
                            "status": self._get_status(evaluation),
                            "score": round(evaluation.score * 100, 2),
                            "passed": evaluation.passed,
                            "warning": evaluation.warning,
                        }

                        if evaluation.failure_reason:
                            track_data["failure_reason"] = evaluation.failure_reason

                        if show_details and evaluation.results:
                            track_data["details"] = self._serialize_critic_results(
                                evaluation.results
                            )

                        case_output["tracks"][track_name] = track_data

                    suite_data["cases"][case_name] = case_output

                output["models"][model]["suites"][suite_name] = suite_data

        return output

    def _format_comparative_case_first(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
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

        output: dict[str, Any] = {
            "type": "multi_model_comparative_evaluation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "models": model_order,
            "tracks": all_tracks,
            "summary": {
                "total_cases": total_cases,
                "passed": total_passed,
                "failed": total_failed,
                "warned": total_warned,
                "pass_rate": round(pass_rate, 2),
            },
            "grouped_by_case": {},
        }

        if failed_only and original_counts:
            output["summary"]["original_counts"] = {
                "total": original_counts[0],
                "passed": original_counts[1],
                "failed": original_counts[2],
                "warned": original_counts[3],
            }
            output["summary"]["filtered"] = True

        # Build case-first structure
        for suite_name, cases in case_groups.items():
            track_order = suite_track_order.get(suite_name, [])
            output["grouped_by_case"][suite_name] = {"tracks": track_order, "cases": {}}

            for case_name, model_data in cases.items():
                first_model_data = next(iter(model_data.values()), {})
                case_output: dict[str, Any] = {
                    "input": first_model_data.get("input", ""),
                    "models": {},
                }

                # Add context if requested
                if include_context:
                    system_msg = first_model_data.get("system_message")
                    addl_msgs = first_model_data.get("additional_messages")
                    if system_msg:
                        case_output["system_message"] = system_msg
                    if addl_msgs:
                        case_output["additional_messages"] = addl_msgs

                for model in model_order:
                    if model not in model_data:
                        case_output["models"][model] = {"status": "missing"}
                        continue

                    model_case_data = model_data[model]
                    tracks_data = model_case_data.get("tracks", {})

                    model_output: dict[str, Any] = {"tracks": {}}

                    for track_name in track_order:
                        if track_name not in tracks_data:
                            model_output["tracks"][track_name] = {"status": "missing"}
                            continue

                        track_result = tracks_data[track_name]
                        evaluation = track_result.get("evaluation")

                        if not evaluation:
                            model_output["tracks"][track_name] = {"status": "no_evaluation"}
                            continue

                        track_data: dict[str, Any] = {
                            "status": self._get_status(evaluation),
                            "score": round(evaluation.score * 100, 2),
                            "passed": evaluation.passed,
                            "warning": evaluation.warning,
                        }

                        if evaluation.failure_reason:
                            track_data["failure_reason"] = evaluation.failure_reason

                        if show_details and evaluation.results:
                            track_data["details"] = self._serialize_critic_results(
                                evaluation.results
                            )

                        model_output["tracks"][track_name] = track_data

                    case_output["models"][model] = model_output

                output["grouped_by_case"][suite_name]["cases"][case_name] = case_output

        return output

    def _format_multi_model(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """Format multi-model evaluation results with comparison structure."""
        comparison_data, model_order, per_model_stats = group_eval_for_comparison(results)

        # Calculate totals
        total_passed = sum(s["passed"] for s in per_model_stats.values())
        total_failed = sum(s["failed"] for s in per_model_stats.values())
        total_warned = sum(s["warned"] for s in per_model_stats.values())
        total_cases = sum(s["total"] for s in per_model_stats.values())

        # Calculate pass rate
        if total_cases > 0:
            if failed_only and original_counts and original_counts[0] > 0:
                pass_rate = (original_counts[1] / original_counts[0]) * 100
            else:
                pass_rate = (total_passed / total_cases) * 100
        else:
            pass_rate = 0

        output: dict[str, Any] = {
            "type": "multi_model_evaluation",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "models": model_order,
            "summary": {
                "total_evaluations": total_cases,
                "unique_cases": sum(len(cases) for cases in comparison_data.values()),
                "passed": total_passed,
                "failed": total_failed,
                "warned": total_warned,
                "pass_rate": round(pass_rate, 2),
            },
            "per_model_stats": {},
            "comparison": {},
        }

        if failed_only and original_counts:
            output["summary"]["original_counts"] = {
                "total": original_counts[0],
                "passed": original_counts[1],
                "failed": original_counts[2],
                "warned": original_counts[3],
            }
            output["summary"]["filtered"] = True

        # Per-model statistics
        best_model = None
        best_rate = -1.0
        for model in model_order:
            stats = per_model_stats[model]
            output["per_model_stats"][model] = {
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "warned": stats["warned"],
                "pass_rate": round(stats["pass_rate"], 2),
            }
            if stats["pass_rate"] > best_rate:
                best_rate = stats["pass_rate"]
                best_model = model

        if best_model:
            output["summary"]["best_model"] = best_model
            output["summary"]["best_pass_rate"] = round(best_rate, 2)

        # Build comparison structure
        for suite_name, cases in comparison_data.items():
            output["comparison"][suite_name] = {}

            for case_name, case_models in cases.items():
                case_output: dict[str, Any] = {
                    "results_by_model": {},
                }

                # Add context from first model if requested
                if include_context:
                    first_model_result = next(iter(case_models.values()), {})
                    system_msg = first_model_result.get("system_message")
                    addl_msgs = first_model_result.get("additional_messages")
                    if system_msg:
                        case_output["system_message"] = system_msg
                    if addl_msgs:
                        case_output["additional_messages"] = addl_msgs

                for model in model_order:
                    if model not in case_models:
                        case_output["results_by_model"][model] = {"status": "missing"}
                        continue

                    case_result = case_models[model]
                    evaluation = case_result["evaluation"]

                    model_data: dict[str, Any] = {
                        "status": self._get_status(evaluation),
                        "score": round(evaluation.score * 100, 2),
                        "passed": evaluation.passed,
                        "warning": evaluation.warning,
                    }

                    if evaluation.failure_reason:
                        model_data["failure_reason"] = evaluation.failure_reason

                    if show_details and evaluation.results:
                        model_data["details"] = self._serialize_critic_results(evaluation.results)

                    case_output["results_by_model"][model] = model_data

                # Find best model for this case
                best, best_score = find_best_model(case_models)
                case_output["best_model"] = best
                case_output["best_score"] = round(best_score * 100, 2)

                output["comparison"][suite_name][case_name] = case_output

        return output

    def _serialize_case(
        self, case: dict[str, Any], show_details: bool, include_context: bool = False
    ) -> dict[str, Any]:
        """Serialize a single evaluation case."""
        evaluation = case["evaluation"]

        case_data: dict[str, Any] = {
            "name": case["name"],
            "input": case.get("input", ""),
            "status": self._get_status(evaluation),
            "score": round(evaluation.score * 100, 2),
            "passed": evaluation.passed,
            "warning": evaluation.warning,
        }

        # Add context if requested
        if include_context:
            system_msg = case.get("system_message")
            addl_msgs = case.get("additional_messages")
            if system_msg:
                case_data["system_message"] = system_msg
            if addl_msgs:
                case_data["additional_messages"] = addl_msgs

        if evaluation.failure_reason:
            case_data["failure_reason"] = evaluation.failure_reason

        if show_details and evaluation.results:
            case_data["details"] = self._serialize_critic_results(evaluation.results)

        return case_data

    def _serialize_critic_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Serialize critic results for detailed output."""
        serialized = []
        for critic_result in results:
            item: dict[str, Any] = {
                "field": critic_result["field"],
                "match": critic_result["match"],
                "score": critic_result["score"],
                "weight": critic_result["weight"],
                "expected": critic_result["expected"],
                "actual": critic_result["actual"],
            }

            if "is_criticized" in critic_result:
                item["is_criticized"] = critic_result["is_criticized"]

            serialized.append(item)

        return serialized

    def _get_status(self, evaluation: Any) -> str:
        """Get status string from evaluation."""
        if evaluation.passed:
            return "passed"
        elif evaluation.warning:
            return "warned"
        else:
            return "failed"


class CaptureJsonFormatter(CaptureFormatter):
    """JSON formatter for capture results."""

    @property
    def file_extension(self) -> str:
        return "json"

    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """Format capture results as JSON."""
        # Check for multi-model captures
        if is_multi_model_capture(captures):
            output_data = self._format_multi_model(captures, include_context)
        else:
            output_data = {
                "type": "capture",
                "captures": [cap.to_dict(include_context=include_context) for cap in captures],
            }
        return json.dumps(output_data, indent=2)

    def _format_multi_model(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> dict[str, Any]:
        """Format multi-model capture results with track-aware structure."""
        from arcade_cli.formatters.base import group_captures_by_case_then_track

        grouped_data, model_order, track_order = group_captures_by_case_then_track(captures)
        has_tracks = len(track_order) > 1 or (track_order and track_order[0] is not None)

        track_names = [t for t in track_order if t is not None] if has_tracks else []

        output: dict[str, Any] = {
            "type": "multi_model_capture",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "models": model_order,
            "tracks": track_names if track_names else None,
            "summary": {
                "total_suites": len(grouped_data),
                "total_cases": sum(len(cases) for cases in grouped_data.values()),
                "models_count": len(model_order),
                "tracks_count": len(track_names) if track_names else 0,
            },
            "grouped_by_case": {},
        }

        for suite_name, cases in grouped_data.items():
            output["grouped_by_case"][suite_name] = {}

            for case_name, case_data in cases.items():
                case_output: dict[str, Any] = {
                    "user_message": case_data.get("user_message", ""),
                }

                if include_context:
                    if case_data.get("system_message"):
                        case_output["system_message"] = case_data["system_message"]
                    if case_data.get("additional_messages"):
                        case_output["additional_messages"] = case_data["additional_messages"]

                tracks_data = case_data.get("tracks", {})
                track_keys = list(tracks_data.keys())
                has_multiple_tracks = len(track_keys) > 1 or (
                    len(track_keys) == 1 and track_keys[0] != "_default"
                )

                if has_multiple_tracks:
                    # Structure with tracks
                    case_output["tracks"] = {}
                    for track_key in track_keys:
                        track_display = track_key if track_key != "_default" else "default"
                        track_data = tracks_data[track_key]
                        models_dict = track_data.get("models", {})

                        track_output: dict[str, Any] = {"models": {}}
                        for model in model_order:
                            if model not in models_dict:
                                track_output["models"][model] = {"status": "missing"}
                                continue

                            captured_case = models_dict[model]
                            track_output["models"][model] = {
                                "tool_calls": [
                                    {"name": tc.name, "args": tc.args}
                                    for tc in captured_case.tool_calls
                                ],
                            }

                        case_output["tracks"][track_display] = track_output
                else:
                    # No tracks - flat structure
                    track_key = track_keys[0] if track_keys else "_default"
                    track_data = tracks_data.get(track_key, {})
                    models_dict = track_data.get("models", {})

                    case_output["models"] = {}
                    for model in model_order:
                        if model not in models_dict:
                            case_output["models"][model] = {"status": "missing"}
                            continue

                        captured_case = models_dict[model]
                        case_output["models"][model] = {
                            "tool_calls": [
                                {"name": tc.name, "args": tc.args}
                                for tc in captured_case.tool_calls
                            ],
                        }

                output["grouped_by_case"][suite_name][case_name] = case_output

        return output
