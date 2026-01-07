"""Base formatter for evaluation and capture results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arcade_evals import CaptureResult

# Type alias for capture results
CaptureResults = list["CaptureResult"]

# --- Type Aliases ---
# The results structure: list of suites, each containing list of model results
EvalResults = list[list[dict[str, Any]]]

# Model -> Suite -> Cases mapping
ModelSuiteGroups = dict[str, dict[str, list[dict[str, Any]]]]

# Statistics tuple: (total, passed, failed, warned)
EvalStats = tuple[int, int, int, int]

# Comparative grouping: model -> base_suite -> case_name -> {input, tracks: {track: case_result}}
ComparativeCaseData = dict[str, Any]  # {input, tracks: {track_name: case_result}}
ComparativeSuiteData = dict[str, ComparativeCaseData]  # case_name -> ComparativeCaseData
ComparativeGroups = dict[str, dict[str, ComparativeSuiteData]]  # model -> suite -> cases

# --- Constants ---
# Maximum field value length before truncation (for display)
MAX_FIELD_DISPLAY_LENGTH = 60
TRUNCATION_SUFFIX = "..."


def truncate_field_value(value: str, max_length: int = MAX_FIELD_DISPLAY_LENGTH) -> str:
    """
    Truncate long field values for display.

    Args:
        value: The string value to potentially truncate.
        max_length: Maximum allowed length (default: 60).

    Returns:
        The original value if within limits, or truncated with "..." suffix.
    """
    if len(value) > max_length:
        return value[: max_length - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX
    return value


def group_results_by_model(
    results: EvalResults,
) -> tuple[ModelSuiteGroups, int, int, int, int]:
    """
    Group evaluation results by model and suite, collecting statistics.

    This is the shared logic used by all formatters and display functions.

    Args:
        results: Nested list of evaluation results by suite and model.

    Returns:
        A tuple of:
        - model_groups: Dict mapping model -> suite -> list of cases
        - total_passed: Count of passed evaluations
        - total_failed: Count of failed evaluations
        - total_warned: Count of warned evaluations
        - total_cases: Total count of all cases
    """
    total_passed = 0
    total_failed = 0
    total_warned = 0
    total_cases = 0
    model_groups: ModelSuiteGroups = {}

    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown Model")

            # suite_name is always set by EvalSuite.evaluate()
            suite_name = model_results.get("suite_name") or "Unnamed Suite"

            cases = model_results.get("cases", [])
            total_cases += len(cases)

            if model not in model_groups:
                model_groups[model] = {}

            if suite_name not in model_groups[model]:
                model_groups[model][suite_name] = []

            for case in cases:
                evaluation = case["evaluation"]
                if evaluation.passed:
                    total_passed += 1
                elif evaluation.warning:
                    total_warned += 1
                else:
                    total_failed += 1

                model_groups[model][suite_name].append(case)

    return model_groups, total_passed, total_failed, total_warned, total_cases


def is_comparative_result(results: EvalResults) -> bool:
    """
    Check if results contain comparative evaluations.

    Comparative results have a 'track_name' field that indicates they came
    from a multi-track comparative evaluation.

    Args:
        results: Nested list of evaluation results.

    Returns:
        True if any result has a 'track_name' field.
    """
    for eval_suite in results:
        for model_results in eval_suite:
            if model_results.get("track_name"):
                return True
    return False


def _extract_base_suite_name(suite_name: str, track_name: str) -> str:
    """
    Extract the base suite name by removing the track suffix.

    Examples:
        "My Suite [track_a]" with track "track_a" -> "My Suite"
        "Suite Name [some_track]" with track "some_track" -> "Suite Name"
    """
    suffix = f" [{track_name}]"
    if suite_name.endswith(suffix):
        return suite_name[: -len(suffix)]
    return suite_name


def group_comparative_by_case(
    results: EvalResults,
) -> tuple[ComparativeGroups, int, int, int, int, dict[str, list[str]]]:
    """
    Group comparative results by model, suite, and case name.

    This allows showing the same case across different tracks side-by-side.

    Args:
        results: Nested list of evaluation results (must be comparative).

    Returns:
        A tuple of:
        - comparative_groups: {model: {base_suite: {case_name: {input, tracks: {track: result}}}}}
        - total_passed: Count of passed evaluations
        - total_failed: Count of failed evaluations
        - total_warned: Count of warned evaluations
        - total_cases: Total count of all cases (unique case_name * tracks)
        - suite_track_order: Dict mapping base_suite -> list of track names for that suite
    """
    total_passed = 0
    total_failed = 0
    total_warned = 0
    total_cases = 0

    # Track order per suite (different suites can have different tracks)
    suite_track_order: dict[str, list[str]] = {}

    # Structure: model -> base_suite -> case_name -> {input, tracks: {track: case_result}}
    comparative_groups: ComparativeGroups = {}

    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown Model")
            suite_name = model_results.get("suite_name") or "Unnamed Suite"
            track_name = model_results.get("track_name", "default")

            # Extract base suite name (without track suffix)
            base_suite = _extract_base_suite_name(suite_name, track_name)

            # Track the order of tracks per suite
            if base_suite not in suite_track_order:
                suite_track_order[base_suite] = []
            if track_name not in suite_track_order[base_suite]:
                suite_track_order[base_suite].append(track_name)

            cases = model_results.get("cases", [])
            total_cases += len(cases)

            if model not in comparative_groups:
                comparative_groups[model] = {}

            if base_suite not in comparative_groups[model]:
                comparative_groups[model][base_suite] = {}

            for case in cases:
                case_name = case["name"]
                evaluation = case["evaluation"]

                # Count stats
                if evaluation.passed:
                    total_passed += 1
                elif evaluation.warning:
                    total_warned += 1
                else:
                    total_failed += 1

                # Initialize case entry if needed
                if case_name not in comparative_groups[model][base_suite]:
                    comparative_groups[model][base_suite][case_name] = {
                        "input": case.get("input", ""),
                        "system_message": case.get("system_message"),
                        "additional_messages": case.get("additional_messages"),
                        "tracks": {},
                    }

                # Store this track's result for this case
                comparative_groups[model][base_suite][case_name]["tracks"][track_name] = {
                    "evaluation": evaluation,
                    "name": case_name,
                    "input": case.get("input", ""),
                }

    return (
        comparative_groups,
        total_passed,
        total_failed,
        total_warned,
        total_cases,
        suite_track_order,
    )


def compute_track_differences(
    case_data: ComparativeCaseData,
    track_order: list[str],
) -> dict[str, list[str]]:
    """
    Compute which fields differ between tracks for a given case.

    Compares each track against the first track (baseline).

    Args:
        case_data: The case data with tracks.
        track_order: List of track names in order.

    Returns:
        Dict mapping track_name -> list of field names that differ from baseline.
    """
    differences: dict[str, list[str]] = {}
    tracks = case_data.get("tracks", {})

    if len(tracks) < 2 or not track_order:
        return differences

    # First track is baseline
    baseline_track = track_order[0]
    if baseline_track not in tracks:
        return differences

    baseline_result = tracks[baseline_track]
    baseline_eval = baseline_result.get("evaluation")
    if not baseline_eval or not hasattr(baseline_eval, "results"):
        return differences

    # Build baseline field values
    baseline_fields: dict[str, Any] = {}
    for critic_result in baseline_eval.results:
        field = critic_result.get("field", "")
        baseline_fields[field] = {
            "actual": critic_result.get("actual"),
            "match": critic_result.get("match"),
            "score": critic_result.get("score"),
        }

    # Compare other tracks to baseline
    for track_name in track_order[1:]:
        if track_name not in tracks:
            continue

        track_result = tracks[track_name]
        track_eval = track_result.get("evaluation")
        if not track_eval or not hasattr(track_eval, "results"):
            continue

        diff_fields: list[str] = []

        for critic_result in track_eval.results:
            field = critic_result.get("field", "")
            actual = critic_result.get("actual")
            match = critic_result.get("match")

            # Check if this field exists in baseline and differs
            if field in baseline_fields:
                baseline_data = baseline_fields[field]
                # Different if actual value differs or match status differs
                if actual != baseline_data["actual"] or match != baseline_data["match"]:
                    diff_fields.append(field)
            else:
                # Field exists in this track but not baseline
                diff_fields.append(field)

        differences[track_name] = diff_fields

    return differences


# Type for case-first comparative grouping
# Structure: suite -> case_name -> model -> {input, tracks: {track: result}}
CaseFirstComparativeGroups = dict[str, dict[str, dict[str, dict[str, Any]]]]


def is_multi_model_comparative(results: EvalResults) -> bool:
    """
    Check if comparative results contain multiple models.

    Args:
        results: Nested list of evaluation results.

    Returns:
        True if this is a comparative result with more than one unique model.
    """
    if not is_comparative_result(results):
        return False

    models: set[str] = set()
    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown")
            models.add(model)
            if len(models) > 1:
                return True
    return False


def group_comparative_by_case_first(
    results: EvalResults,
) -> tuple[CaseFirstComparativeGroups, list[str], dict[str, list[str]], int, int, int, int]:
    """
    Group comparative results by suite -> case -> model for case-first comparison.

    When multiple models run the same comparative evaluation, this groups results
    so the same case from different models appears together.

    Args:
        results: Nested list of comparative evaluation results.

    Returns:
        A tuple of:
        - case_groups: {suite: {case_name: {model: {input, tracks: {track: result}}}}}
        - model_order: List of model names in order of appearance
        - suite_track_order: Dict mapping suite -> list of track names
        - total_passed, total_failed, total_warned, total_cases
    """
    total_passed = 0
    total_failed = 0
    total_warned = 0
    total_cases = 0

    model_order: list[str] = []
    suite_track_order: dict[str, list[str]] = {}

    # Structure: base_suite -> case_name -> model -> {input, tracks: {track: result}}
    case_groups: CaseFirstComparativeGroups = {}

    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown Model")
            suite_name = model_results.get("suite_name") or "Unnamed Suite"
            track_name = model_results.get("track_name", "default")

            # Track model order
            if model not in model_order:
                model_order.append(model)

            # Extract base suite name (without track suffix)
            base_suite = _extract_base_suite_name(suite_name, track_name)

            # Track the order of tracks per suite
            if base_suite not in suite_track_order:
                suite_track_order[base_suite] = []
            if track_name not in suite_track_order[base_suite]:
                suite_track_order[base_suite].append(track_name)

            cases = model_results.get("cases", [])
            total_cases += len(cases)

            # Initialize suite
            if base_suite not in case_groups:
                case_groups[base_suite] = {}

            for case in cases:
                case_name = case["name"]
                evaluation = case["evaluation"]

                # Count stats
                if evaluation.passed:
                    total_passed += 1
                elif evaluation.warning:
                    total_warned += 1
                else:
                    total_failed += 1

                # Initialize case
                if case_name not in case_groups[base_suite]:
                    case_groups[base_suite][case_name] = {}

                # Initialize model entry for this case
                if model not in case_groups[base_suite][case_name]:
                    case_groups[base_suite][case_name][model] = {
                        "input": case.get("input", ""),
                        "system_message": case.get("system_message"),
                        "additional_messages": case.get("additional_messages"),
                        "tracks": {},
                    }

                # Store this track's result
                case_groups[base_suite][case_name][model]["tracks"][track_name] = {
                    "evaluation": evaluation,
                    "name": case_name,
                    "input": case.get("input", ""),
                }

    return (
        case_groups,
        model_order,
        suite_track_order,
        total_passed,
        total_failed,
        total_warned,
        total_cases,
    )


# =============================================================================
# MULTI-MODEL HELPERS
# =============================================================================


def is_multi_model_eval(results: EvalResults) -> bool:
    """
    Check if evaluation results contain multiple models.

    Args:
        results: Nested list of evaluation results.

    Returns:
        True if more than one unique model is present.
    """
    models: set[str] = set()
    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown")
            models.add(model)
            if len(models) > 1:
                return True
    return False


def is_multi_model_capture(captures: CaptureResults) -> bool:
    """
    Check if capture results contain multiple models.

    Args:
        captures: List of CaptureResult objects.

    Returns:
        True if more than one unique model is present.
    """
    models = {c.model for c in captures}
    return len(models) > 1


# Type for multi-model comparison: suite -> case -> model -> case_result
MultiModelComparisonData = dict[str, dict[str, dict[str, dict[str, Any]]]]

# Type for per-model stats: model -> {passed, failed, warned, total, pass_rate}
PerModelStats = dict[str, dict[str, Any]]


def group_eval_for_comparison(
    results: EvalResults,
) -> tuple[MultiModelComparisonData, list[str], PerModelStats]:
    """
    Reorganize evaluation results for cross-model comparison.

    Groups results by suite -> case -> model, enabling side-by-side tables.

    Args:
        results: Nested list of evaluation results.

    Returns:
        A tuple of:
        - comparison_data: {suite: {case_name: {model: case_result}}}
        - model_order: List of model names in order of appearance
        - per_model_stats: {model: {passed, failed, warned, total, pass_rate}}
    """
    comparison_data: MultiModelComparisonData = {}
    model_order: list[str] = []
    per_model_stats: PerModelStats = {}

    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown Model")
            suite_name = model_results.get("suite_name") or "Unnamed Suite"
            cases = model_results.get("cases", [])

            # Track model order
            if model not in model_order:
                model_order.append(model)

            # Initialize per-model stats
            if model not in per_model_stats:
                per_model_stats[model] = {
                    "passed": 0,
                    "failed": 0,
                    "warned": 0,
                    "total": 0,
                }

            # Initialize suite in comparison data
            if suite_name not in comparison_data:
                comparison_data[suite_name] = {}

            for case in cases:
                case_name = case["name"]
                evaluation = case["evaluation"]

                # Update per-model stats
                per_model_stats[model]["total"] += 1
                if evaluation.passed:
                    per_model_stats[model]["passed"] += 1
                elif evaluation.warning:
                    per_model_stats[model]["warned"] += 1
                else:
                    per_model_stats[model]["failed"] += 1

                # Initialize case in suite
                if case_name not in comparison_data[suite_name]:
                    comparison_data[suite_name][case_name] = {}

                # Store this model's result for this case
                comparison_data[suite_name][case_name][model] = {
                    "evaluation": evaluation,
                    "input": case.get("input", ""),
                    "name": case_name,
                }

    # Calculate pass rates
    for _model, stats in per_model_stats.items():
        if stats["total"] > 0:
            stats["pass_rate"] = (stats["passed"] / stats["total"]) * 100
        else:
            stats["pass_rate"] = 0.0

    return comparison_data, model_order, per_model_stats


def find_best_model(
    case_models: dict[str, dict[str, Any]],
) -> tuple[str | None, float]:
    """
    Find the model with the highest score for a case.

    Args:
        case_models: Dict mapping model -> case_result with evaluation.

    Returns:
        Tuple of (best_model_name, best_score). Returns (None, 0.0) if no models
        or if all evaluations are missing.
        Returns ("Tie", score) if multiple models share the highest score.
    """
    if not case_models:
        return None, 0.0

    best_model: str | None = None
    best_score = -1.0
    tie = False
    found_valid_evaluation = False

    for model, case_result in case_models.items():
        evaluation = case_result.get("evaluation")
        if not evaluation:
            continue

        found_valid_evaluation = True
        score = evaluation.score
        if score > best_score:
            best_score = score
            best_model = model
            tie = False
        elif score == best_score:
            tie = True

    # Return 0.0 if no valid evaluations found (not -1.0)
    if not found_valid_evaluation:
        return None, 0.0

    if tie:
        return "Tie", best_score

    return best_model, best_score


# Type for grouped captures: suite -> case_name -> {user_message, models: {model: [tool_calls]}}
GroupedCaptures = dict[str, dict[str, dict[str, Any]]]


def group_captures_by_case(
    captures: CaptureResults,
) -> tuple[GroupedCaptures, list[str]]:
    """
    Group capture results by suite and case for multi-model comparison.

    Args:
        captures: List of CaptureResult objects.

    Returns:
        A tuple of:
        - grouped: {suite: {case_key: {user_message, system_message, track_name, models: {model: captured_case}}}}
        - model_order: List of model names in order of appearance

    Note: For comparative captures with tracks, case_key includes the track name
    to keep them separate (e.g., "weather_case [track_a]").
    """
    grouped: GroupedCaptures = {}
    model_order: list[str] = []

    for capture in captures:
        suite_name = capture.suite_name
        model = capture.model

        # Track model order
        if model not in model_order:
            model_order.append(model)

        # Initialize suite
        if suite_name not in grouped:
            grouped[suite_name] = {}

        for case in capture.captured_cases:
            # Include track_name in the key for comparative captures
            track_name = getattr(case, "track_name", None)
            case_key = f"{case.case_name} [{track_name}]" if track_name else case.case_name

            # Initialize case
            if case_key not in grouped[suite_name]:
                grouped[suite_name][case_key] = {
                    "user_message": case.user_message,
                    "system_message": case.system_message,
                    "additional_messages": case.additional_messages,
                    "track_name": track_name,
                    "models": {},
                }

            # Store this model's captured case
            grouped[suite_name][case_key]["models"][model] = case

    return grouped, model_order


def group_captures_by_case_then_track(
    captures: CaptureResults,
) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str], list[str | None]]:
    """
    Group capture results by suite, case, then track for tab-based display.

    Args:
        captures: List of CaptureResult objects.

    Returns:
        A tuple of:
        - grouped: {suite: {base_case_name: {tracks: {track: {models: {model: case}}}, user_message, ...}}}
        - model_order: List of model names in order
        - track_order: List of track names in order (None for non-comparative)
    """
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    model_order: list[str] = []
    track_order: list[str | None] = []

    for capture in captures:
        suite_name = capture.suite_name
        model = capture.model

        if model not in model_order:
            model_order.append(model)

        if suite_name not in grouped:
            grouped[suite_name] = {}

        for case in capture.captured_cases:
            track_name = getattr(case, "track_name", None)
            base_case_name = case.case_name

            # Track order
            if track_name and track_name not in track_order:
                track_order.append(track_name)

            # Initialize case
            if base_case_name not in grouped[suite_name]:
                grouped[suite_name][base_case_name] = {
                    "user_message": case.user_message,
                    "system_message": case.system_message,
                    "additional_messages": case.additional_messages,
                    "tracks": {},  # {track_name: {models: {model: case}}}
                }

            # Initialize track
            track_key = track_name or "_default"
            if track_key not in grouped[suite_name][base_case_name]["tracks"]:
                grouped[suite_name][base_case_name]["tracks"][track_key] = {
                    "models": {},
                }

            # Store case under track and model
            grouped[suite_name][base_case_name]["tracks"][track_key]["models"][model] = case

    # If no tracks, add None to track_order for consistent handling
    if not track_order:
        track_order = [None]

    return grouped, model_order, track_order


class EvalResultFormatter(ABC):
    """
    Abstract base class for evaluation result formatters.

    Implement this class to add new output formats (txt, md, json, html, etc.).
    """

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the default file extension for this format (e.g., 'txt', 'md')."""
        ...

    @abstractmethod
    def format(
        self,
        results: EvalResults,
        show_details: bool = False,
        failed_only: bool = False,
        original_counts: EvalStats | None = None,
        include_context: bool = False,
    ) -> str:
        """
        Format evaluation results into a string.

        Args:
            results: Nested list of evaluation results by suite and model.
            show_details: Whether to show detailed results for each case.
            failed_only: Whether only failed cases are being displayed.
            original_counts: Optional (total, passed, failed, warned) from before filtering.
            include_context: Whether to include system_message and additional_messages.

        Returns:
            Formatted string representation of the results.
        """
        ...


class CaptureFormatter(ABC):
    """
    Abstract base class for capture result formatters.

    Implement this class to add new output formats for capture mode.
    """

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the default file extension for this format."""
        ...

    @abstractmethod
    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
    ) -> str:
        """
        Format capture results into a string.

        Args:
            captures: List of CaptureResult objects.
            include_context: Whether to include system_message and additional_messages.

        Returns:
            Formatted string representation of the capture results.
        """
        ...
