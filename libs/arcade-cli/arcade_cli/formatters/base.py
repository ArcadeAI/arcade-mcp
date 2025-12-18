"""Base formatter for evaluation results."""

from abc import ABC, abstractmethod
from typing import Any

# --- Type Aliases ---
# The results structure: list of suites, each containing list of model results
EvalResults = list[list[dict[str, Any]]]

# Model -> Suite -> Cases mapping
ModelSuiteGroups = dict[str, dict[str, list[dict[str, Any]]]]

# Statistics tuple: (total, passed, failed, warned)
EvalStats = tuple[int, int, int, int]

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

            # Get suite name with safe fallback
            suite_name = model_results.get("suite_name", "")
            if not suite_name:
                rubric_obj = model_results.get("rubric")
                if rubric_obj is not None:
                    # Safe conversion: use name attribute if available, else default
                    if hasattr(rubric_obj, "name") and rubric_obj.name:
                        suite_name = rubric_obj.name
                    elif hasattr(rubric_obj, "__name__"):
                        suite_name = rubric_obj.__name__
                    elif isinstance(rubric_obj, str) and rubric_obj:
                        suite_name = rubric_obj
                    else:
                        suite_name = "Unnamed Suite"
                else:
                    suite_name = "Unnamed Suite"

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
    ) -> str:
        """
        Format evaluation results into a string.

        Args:
            results: Nested list of evaluation results by suite and model.
            show_details: Whether to show detailed results for each case.
            failed_only: Whether only failed cases are being displayed.
            original_counts: Optional (total, passed, failed, warned) from before filtering.

        Returns:
            Formatted string representation of the results.
        """
        ...

    def _collect_stats(
        self,
        results: list[list[dict[str, Any]]],
    ) -> tuple[int, int, int, int, list[dict[str, Any]]]:
        """
        Collect statistics from evaluation results.

        Returns:
            Tuple of (total_cases, passed, failed, warned, flat_cases_list)
        """
        total_passed = 0
        total_failed = 0
        total_warned = 0
        total_cases = 0
        all_cases: list[dict[str, Any]] = []

        for eval_suite in results:
            for model_results in eval_suite:
                cases = model_results.get("cases", [])
                total_cases += len(cases)

                for case in cases:
                    evaluation = case["evaluation"]
                    if evaluation.passed:
                        total_passed += 1
                    elif evaluation.warning:
                        total_warned += 1
                    else:
                        total_failed += 1
                    all_cases.append({
                        "model": model_results.get("model", "Unknown"),
                        "rubric": model_results.get("rubric", ""),
                        **case,
                    })

        return total_cases, total_passed, total_failed, total_warned, all_cases
