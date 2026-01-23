import asyncio
import functools
import inspect
import json
import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
from arcade_core.converters.openai import OpenAIToolList, to_openai
from arcade_core.schema import TOOL_NAME_SEPARATOR
from openai import AsyncOpenAI
from scipy.optimize import linear_sum_assignment

from arcade_evals._evalsuite._capture import _EvalSuiteCaptureMixin
from arcade_evals._evalsuite._comparative_execution import _EvalSuiteComparativeMixin
from arcade_evals._evalsuite._convenience import _EvalSuiteConvenienceMixin
from arcade_evals._evalsuite._providers import (
    ProviderName,
    convert_messages_to_anthropic,
)
from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry
from arcade_evals._evalsuite._tracks import TrackManager

# Import shared types from _types module (breaks circular dependencies)
from arcade_evals._evalsuite._types import (
    AnyExpectedToolCall,
    EvalRubric,
    ExpectedMCPToolCall,
    ExpectedToolCall,
    NamedExpectedToolCall,
)
from arcade_evals.critic import NoneCritic
from arcade_evals.weights import validate_and_normalize_critic_weights

if TYPE_CHECKING:
    from arcade_core import ToolCatalog

    from arcade_evals._evalsuite._comparative import ComparativeCaseBuilder
    from arcade_evals.critic import Critic

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility (these are now defined in _types.py)
__all__ = [
    "AnyExpectedToolCall",
    "EvalCase",
    "EvalRubric",
    "EvalSuite",
    "EvaluationResult",
    "ExpectedMCPToolCall",
    "ExpectedToolCall",
    "NamedExpectedToolCall",
]


@dataclass
class EvaluationResult:
    """
    Represents the result of an evaluation case.

    Attributes:
        score: The normalized evaluation score (0.0-1.0).
        passed: Whether the evaluation passed based on the fail_threshold.
        warning: Whether the evaluation issued a warning based on the warn_threshold.
        results: A list of dictionaries containing the results for each critic.
        failure_reason: If the evaluation failed completely due to settings in the rubric,
                        this field contains the reason for failure.
    """

    score: float = 0.0
    passed: bool = False
    warning: bool = False
    results: list[dict[str, Any]] = field(default_factory=list)
    failure_reason: str | None = None

    @property
    def fail(self) -> bool:
        """Returns True if the evaluation failed (excluding warnings)."""
        return not self.passed and not self.warning

    @property
    def warn(self) -> bool:
        """Returns True if the evaluation is in warning state."""
        return self.warning

    def add(
        self,
        field: str,
        result: dict[str, Any],
        weight: float,
        expected: Any,
        actual: Any,
    ) -> None:
        """
        Add a critic result to the list of critic results.

        Args:
            field: The field name for the critic result.
            result: A dictionary containing the critic result.
            weight: The weight of the critic.
            expected: The expected value for the critic.
            actual: The actual value for the critic.
        """
        self.results.append({
            "field": field,
            **result,
            "weight": weight,
            "expected": expected,
            "actual": actual,
        })

    def score_tool_selection(self, expected: str, actual: str, weight: float) -> float:
        """
        Score and record tool selection in results.

        Args:
            expected: The expected tool name.
            actual: The actual tool name.
            weight: The weight for tool selection.

        Returns:
            The score for the tool selection.
        """
        score = weight if compare_tool_name(expected, actual) else 0.0
        self.add(
            "tool_selection",
            {"match": compare_tool_name(expected, actual), "score": score},
            weight,
            expected,
            actual,
        )
        return score

    def compute_final_score(self, total_weight: float) -> None:
        """
        Compute the final score by normalizing the total score with the total weight.
        """
        total_score = sum(result["score"] for result in self.results)
        self.score = total_score / total_weight if total_weight > 0 else 0.0


DEFAULT_EVAL_SEED = 42
PASS_RULE_LAST = "last"  # noqa: S105
PASS_RULE_MEAN = "mean"  # noqa: S105
PASS_RULE_MAJORITY = "majority"  # noqa: S105
_VALID_PASS_RULES = {PASS_RULE_LAST, PASS_RULE_MEAN, PASS_RULE_MAJORITY}


def _compute_mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    avg = mean(values)
    if len(values) < 2:
        return avg, 0.0
    return avg, pstdev(values)


def _resolve_seed_spec(seed: str | int | None) -> tuple[str, int | None]:
    if seed is None:
        return "constant", DEFAULT_EVAL_SEED
    if isinstance(seed, int):
        return "custom", seed
    seed_value = seed.strip().lower()
    if seed_value == "constant":
        return "constant", DEFAULT_EVAL_SEED
    if seed_value == "random":
        return "random", None
    try:
        return "custom", int(seed_value)
    except ValueError as exc:
        raise ValueError("Invalid seed. Use 'constant', 'random', or an integer value.") from exc


def _resolve_pass_rule(
    run_evaluations: list[EvaluationResult],
    mean_score: float,
    pass_rule: str,
    rubric: EvalRubric,
) -> tuple[bool, bool]:
    if pass_rule not in _VALID_PASS_RULES:
        raise ValueError(
            f"Invalid multi-run pass rule '{pass_rule}'. "
            f"Valid values: {', '.join(sorted(_VALID_PASS_RULES))}"
        )
    if not run_evaluations:
        return False, False
    if pass_rule == PASS_RULE_MEAN:
        passed = mean_score >= rubric.fail_threshold
        warning = not passed and mean_score >= rubric.warn_threshold
        return passed, warning
    if pass_rule == PASS_RULE_MAJORITY:
        majority = len(run_evaluations) // 2 + 1
        passed_count = sum(1 for ev in run_evaluations if ev.passed)
        warned_count = sum(1 for ev in run_evaluations if ev.warning)
        if passed_count >= majority:
            return True, False
        if (passed_count + warned_count) >= majority:
            return False, True
        return False, False
    last_eval = run_evaluations[-1]
    return last_eval.passed, last_eval.warning


def _aggregate_critic_stats(
    run_field_scores: list[dict[str, dict[str, float]]],
) -> dict[str, dict[str, Any]]:
    if not run_field_scores:
        return {}
    all_fields: set[str] = set()
    for field_scores in run_field_scores:
        all_fields.update(field_scores.keys())

    critic_stats: dict[str, dict[str, Any]] = {}
    for critic_field in sorted(all_fields):
        weighted_scores = [
            run_scores.get(critic_field, {}).get("score", 0.0)
            for run_scores in run_field_scores
        ]
        weights = [
            run_scores.get(critic_field, {}).get("weight", 0.0)
            for run_scores in run_field_scores
        ]
        normalized_scores = [
            (score / weight) if weight > 0 else 0.0
            for score, weight in zip(weighted_scores, weights)
        ]
        avg, std_dev = _compute_mean_std(weighted_scores)
        avg_norm, std_norm = _compute_mean_std(normalized_scores)
        non_zero_weights = [w for w in weights if w > 0]
        avg_weight = max(non_zero_weights) if non_zero_weights else 0.0
        critic_stats[critic_field] = {
            "run_scores": weighted_scores,
            "mean_score": avg,
            "std_deviation": std_dev,
            "run_scores_normalized": normalized_scores,
            "mean_score_normalized": avg_norm,
            "std_deviation_normalized": std_norm,
            "weight": avg_weight,
        }
    return critic_stats


# Import capture mode helpers (defined in capture.py to keep this file focused)
from arcade_evals.capture import (  # noqa: E402
    _capture_with_anthropic,
    _capture_with_openai,
)


@dataclass
class EvalCase:
    """
    Represents a single evaluation case within an EvalSuite.

    Attributes:
        name: A descriptive name for this evaluation case.
        system_message: The system message to be sent to the AI model.
        user_message: The user input to be sent to the AI model.
        expected_tool_calls: A list of NamedExpectedToolCall objects representing the expected tool calls.
        critics: A list of Critic objects used to evaluate tool arguments.
        additional_messages: Optional list of additional context messages.
        rubric: An EvalRubric object defining pass/fail criteria and tool selection behavior.
    """

    name: str
    system_message: str
    user_message: str
    expected_tool_calls: list[NamedExpectedToolCall]
    critics: list["Critic"] | None = None
    additional_messages: list[dict[str, Any]] = field(default_factory=list)
    rubric: EvalRubric = field(default_factory=EvalRubric)

    def __post_init__(self) -> None:
        if self.critics is not None:
            validate_and_normalize_critic_weights(self.critics)
        else:
            # if no critics are provided, set to empty list
            self.critics = []

    def check_tool_selection_failure(self, actual_tools: list[str]) -> bool:
        """
        Check if tool selection failure should occur.

        Args:
            actual_tools: The list of actual tool names used.

        Returns:
            True if tool selection failure should occur, False otherwise.
        """
        sorted_expected_tools = sorted([tc.name for tc in self.expected_tool_calls])
        sorted_actual_tools = sorted(actual_tools)
        return self.rubric.fail_on_tool_selection and not all(
            compare_tool_name(expected, actual)
            for expected, actual in zip(sorted_expected_tools, sorted_actual_tools)
        )

    def check_tool_call_quantity_failure(self, actual_count: int) -> bool:
        """
        Check if tool call quantity failure should occur.

        Args:
            actual_count: The number of actual tool calls made.

        Returns:
            True if tool call quantity failure should occur, False otherwise.
        """
        expected_count = len(self.expected_tool_calls)
        return self.rubric.fail_on_tool_call_quantity and expected_count != actual_count

    def evaluate(
        self,
        actual_tool_calls: list[tuple[str, dict[str, Any]]],
    ) -> EvaluationResult:
        """
        Evaluate the actual tool calls against the expected tool calls and critics.

        Args:
            actual_tool_calls: A list of tuples containing the actual tool name and arguments.

        Returns:
            An EvaluationResult object containing the evaluation results.
        """
        evaluation_result = EvaluationResult()

        actual_tools = [tool_name for tool_name, _ in actual_tool_calls]
        actual_count = len(actual_tool_calls)

        if self.check_tool_call_quantity_failure(actual_count):
            evaluation_result.score = 0.0
            evaluation_result.passed = False
            expected_count = len(self.expected_tool_calls)
            expected_tool_names = ", ".join(
                tool_call.name for tool_call in self.expected_tool_calls
            )
            evaluation_result.failure_reason = (
                f"Expected {expected_count} tool call(s), but got {actual_count}. "
                + f"\nExpected tool calls: {expected_tool_names}.\nActual tool calls: {', '.join(actual_tools)}"
            )
            return evaluation_result

        if not self.expected_tool_calls and not actual_tools:
            evaluation_result.score = 1.0
            evaluation_result.passed = True
            return evaluation_result

        if self.check_tool_selection_failure(actual_tools):
            evaluation_result.score = 0.0
            evaluation_result.passed = False
            expected_tools = [tc.name for tc in self.expected_tool_calls]
            evaluation_result.failure_reason = f"Tool selection mismatch. Expected tools: {expected_tools}, but got: {actual_tools}"
            return evaluation_result

        if not self.critics:
            evaluation_result.score = 1.0
            evaluation_result.passed = True
            return evaluation_result

        # Create a cost matrix for the assignment problem
        cost_matrix = self._create_cost_matrix(actual_tool_calls, self.expected_tool_calls)

        # Use the Linear Sum Assignment algorithm to find the optimal assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix, maximize=True)

        total_score = 0.0
        total_weight = 0.0

        for i, j in zip(row_ind, col_ind):
            if i < len(self.expected_tool_calls) and j < len(actual_tool_calls):
                expected = self.expected_tool_calls[i]
                actual_name, actual_args = actual_tool_calls[j]

                # Tool selection
                tool_selection_score = evaluation_result.score_tool_selection(
                    expected.name, actual_name, self.rubric.tool_selection_weight
                )
                total_score += tool_selection_score
                total_weight += self.rubric.tool_selection_weight

                # Evaluate arguments using critics
                for critic in self.critics:
                    expected_value = expected.args.get(critic.critic_field)
                    actual_value = actual_args.get(critic.critic_field)

                    try:
                        result = critic.evaluate(expected_value, actual_value)
                        total_score += result["score"]
                        total_weight += critic.resolved_weight
                        evaluation_result.add(
                            critic.critic_field,
                            result,
                            critic.resolved_weight,
                            expected_value,
                            actual_value,
                        )
                    except Exception as e:
                        logger.warning(
                            "Critic evaluation failed for field '%s': %s",
                            critic.critic_field,
                            e,
                            exc_info=True,
                        )
                        evaluation_result.add(
                            critic.critic_field,
                            {"match": False, "score": 0.0},
                            critic.resolved_weight,
                            expected_value,
                            actual_value,
                        )
                        continue

        # Compute the final score
        evaluation_result.compute_final_score(total_weight)

        # Set pass/fail and warning status
        evaluation_result.passed = evaluation_result.score >= self.rubric.fail_threshold
        evaluation_result.warning = (
            not evaluation_result.passed and evaluation_result.score >= self.rubric.warn_threshold
        )

        return evaluation_result

    def _create_cost_matrix(
        self,
        actual_tool_calls: list[tuple[str, dict[str, Any]]],
        expected_tool_calls: list[NamedExpectedToolCall],
    ) -> np.ndarray:
        """
        Create a cost matrix for the assignment problem.

        Args:
            actual_tool_calls: A list of tuples of actual tool calls.
            expected_tool_calls: A list of NamedExpectedToolCall instances.

        Returns:
            A numpy array representing the cost matrix.
        """
        num_expected = len(expected_tool_calls)
        num_actual = len(actual_tool_calls)
        n = max(num_expected, num_actual)

        cost_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i < num_expected and j < num_actual:
                    expected = expected_tool_calls[i]
                    actual_name, actual_args = actual_tool_calls[j]
                    score = 0.0

                    # Tool selection
                    if compare_tool_name(expected.name, actual_name):
                        score += self.rubric.tool_selection_weight

                    # Critics evaluation
                    for critic in self.critics:  # type: ignore[union-attr]
                        expected_value = expected.args.get(critic.critic_field)
                        actual_value = actual_args.get(critic.critic_field)
                        if expected_value is not None and actual_value is not None:
                            try:
                                result = critic.evaluate(expected_value, actual_value)
                                score += result.get("score", 0.0)
                            except Exception as e:
                                logger.warning(
                                    "Critic evaluation failed for field '%s': %s",
                                    critic.critic_field,
                                    e,
                                )
                    cost_matrix[i, j] = score

        return cost_matrix


@dataclass
class EvalSuite(_EvalSuiteCaptureMixin, _EvalSuiteConvenienceMixin, _EvalSuiteComparativeMixin):
    """
    A suite for evaluating AI model performance on specific tasks or scenarios.

    EvalSuite manages a collection of EvalCases, each representing a specific test scenario.
    It provides methods to add cases, register tools, and run evaluations against specified models.

    Attributes:
        name: The name of the evaluation suite.
        system_message: The system message to be used for all cases in this suite.
        catalog: A ToolCatalog containing registered Python tools.
        cases: A list of EvalCase objects representing individual test scenarios.
        rubric: The evaluation rubric for this case.
        max_concurrent: Maximum number of concurrent evaluations.
        strict_mode: Whether to enable strict-mode schema conversion for MCP-style tools.
    """

    name: str
    system_message: str
    catalog: "ToolCatalog | None" = None
    cases: list[EvalCase] = field(default_factory=list)
    rubric: EvalRubric = field(default_factory=EvalRubric)
    max_concurrent: int = 1
    strict_mode: bool = True

    # Internal unified registry for MCP-style tools added via convenience methods.
    _internal_registry: EvalSuiteToolRegistry | None = field(default=None, init=False, repr=False)

    # Track manager for comparative evaluations (isolated registries per track).
    _track_manager: TrackManager = field(default_factory=TrackManager, init=False, repr=False)

    # Comparative case builders for multi-track evaluations (validated at execution time).
    _comparative_case_builders: list["ComparativeCaseBuilder"] = field(
        default_factory=list, init=False, repr=False
    )

    # Python tool helpers (used when Python tools are added via add_tool_catalog()).
    _python_tool_func_map: dict[str, Callable] = field(default_factory=dict, init=False, repr=False)
    _python_func_to_tool_name: dict[Callable, str] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize internal registry and auto-convert catalog if provided."""
        # Always create the internal registry
        self._internal_registry = EvalSuiteToolRegistry(strict_mode=self.strict_mode)

        # If catalog was passed, convert those tools to the internal registry
        if self.catalog is not None:
            self._register_catalog_tools(self.catalog)

    def _register_catalog_tools(self, catalog: "ToolCatalog", *, track: str | None = None) -> None:
        """Convert and register tools from a ToolCatalog to the internal registry.

        This helper is used by both __post_init__ (for catalog= parameter) and
        add_tool_catalog() (for post-init registration).

        Args:
            catalog: The ToolCatalog to register.
            track: Optional track name for comparative evaluations.
        """
        registry = self._get_registry(track)

        # Convert Python tools from ToolCatalog and store in unified registry format.
        # We use to_openai() to extract the normalized tool schema, then pass the
        # original MaterializedTool to the registry. This allows:
        # - OpenAI: Uses the extracted MCP-style schema (stored in registry)
        # - Anthropic: Uses direct to_anthropic() converter (via stored MaterializedTool)
        # This avoids double-conversion overhead while maintaining unified storage.
        for tool in catalog:
            # Use OpenAI converter to get the tool name and base schema
            openai_tool = to_openai(tool)
            func_schema = openai_tool.get("function", {})
            tool_name = func_schema.get("name")
            if not tool_name:
                continue

            description = func_schema.get("description") or ""
            parameters = func_schema.get("parameters") or {"type": "object", "properties": {}}
            registry.add_tool(
                {
                    "name": tool_name,
                    "description": description,
                    "inputSchema": dict(parameters),
                },
                materialized_tool=tool,  # Pass for direct Anthropic conversion
            )

            # Keep track of Python function for defaults
            python_func = getattr(tool, "tool", None)
            if callable(python_func):
                self._python_tool_func_map[tool_name] = python_func
                self._python_func_to_tool_name[python_func] = tool_name

    def _convert_to_named_expected_tool_call(
        self, tc: AnyExpectedToolCall | tuple[Callable, dict[str, Any]]
    ) -> NamedExpectedToolCall:
        """
        Convert an ExpectedToolCall, ExpectedMCPToolCall, or tuple to a NamedExpectedToolCall
        with default arguments populated.

        Args:
            tc: The tool call - ExpectedToolCall (Python), ExpectedMCPToolCall (MCP), or tuple.

        Returns:
            A NamedExpectedToolCall instance.
        """
        # Handle MCP tools (ExpectedMCPToolCall)
        if isinstance(tc, ExpectedMCPToolCall):
            return self._convert_mcp_tool_call(tc.tool_name, tc.args)

        # Handle Python tools (ExpectedToolCall or tuple)
        if isinstance(tc, tuple):
            func, args = tc
        else:
            # ExpectedToolCall
            func = tc.func
            args = tc.args

        args_with_defaults = self._fill_args_with_defaults(func, args)
        # Try convenience method registration first, then fall back to catalog
        tool_name = self._python_func_to_tool_name.get(func)
        if not tool_name:
            if self.catalog is not None:
                tool_name = str(self.catalog.find_tool_by_func(func).get_fully_qualified_name())
            else:
                raise ValueError(
                    "Python tool callables require ToolCatalog or add_tool_catalog() registration."
                )
        return NamedExpectedToolCall(name=tool_name, args=args_with_defaults)

    def _convert_mcp_tool_call(self, tool_name: str, args: dict[str, Any]) -> NamedExpectedToolCall:
        """Convert an MCP tool reference to a NamedExpectedToolCall (NEW in this PR)."""
        args_with_defaults = dict(args)
        # Apply schema defaults from internal registry
        if self._internal_registry is not None and self._internal_registry.has_tool(tool_name):
            args_with_defaults = self._internal_registry.normalize_args(
                tool_name, args_with_defaults
            )
        return NamedExpectedToolCall(name=tool_name, args=args_with_defaults)

    def _create_eval_case(
        self,
        name: str,
        system_message: str,
        user_message: str,
        expected_tool_calls: list[NamedExpectedToolCall],
        rubric: EvalRubric,
        critics: list["Critic"],
        additional_messages: list[dict[str, Any]],
    ) -> "EvalCase":
        """Factory method to create EvalCase instances.

        Used by the comparative mixin to create EvalCase without circular imports.
        """
        return EvalCase(
            name=name,
            system_message=system_message,
            user_message=user_message,
            expected_tool_calls=expected_tool_calls,
            rubric=rubric,
            critics=critics,
            additional_messages=additional_messages,
        )

    def add_case(
        self,
        name: str,
        user_message: str,
        expected_tool_calls: Sequence[AnyExpectedToolCall]
        | Sequence[tuple[Callable, dict[str, Any]]],
        critics: list["Critic"] | None = None,
        system_message: str | None = None,
        rubric: EvalRubric | None = None,
        additional_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Add a new evaluation case to the suite.

        Args:
            name: The name of the evaluation case.
            user_message: The user's input message.
            expected_tool_calls: A list of expected tool calls (ExpectedToolCall, ExpectedMCPToolCall, or tuples).
            critics: List of critics to evaluate the tool arguments.
            system_message: The system message to be used.
            rubric: The evaluation rubric for this case.
            additional_messages: Optional list of additional messages for context.
        """
        expected_tool_calls_with_defaults = [
            self._convert_to_named_expected_tool_call(tc) for tc in expected_tool_calls
        ]

        # Add NoneCritics for any expected tool call fields not in the critics list
        critics = self._add_none_critics(expected_tool_calls_with_defaults, critics)

        self._validate_critics(critics, name)

        case = EvalCase(
            name=name,
            system_message=system_message or self.system_message,
            user_message=user_message,
            expected_tool_calls=expected_tool_calls_with_defaults,
            rubric=rubric or self.rubric,
            critics=critics,
            additional_messages=additional_messages or [],
        )
        self.cases.append(case)

    def _add_none_critics(
        self,
        expected_tool_calls_with_defaults: list[NamedExpectedToolCall],
        critics: list["Critic"] | None,
    ) -> list["Critic"]:
        """
        Add NoneCritics for any fields in the expected tool calls that are not already in the critics list.

        Args:
            expected_tool_calls_with_defaults: The list of expected tool calls with defaults.
            critics: The list of critics.

        Returns:
            The updated list of critics.
        """
        if not critics:
            critics = []
            critic_field_names = set()
        else:
            critic_field_names = {critic.critic_field for critic in critics}

        for tc in expected_tool_calls_with_defaults:
            for field_name in tc.args:
                if field_name not in critic_field_names:
                    critics.append(NoneCritic(critic_field=field_name))
                    critic_field_names.add(field_name)
        return critics

    def _validate_critics(self, critics: list["Critic"] | None, name: str) -> None:
        """
        Validate the critics.

        Args:
            critics: The list of critics.
            name: The name of the evaluation case.

        Raises:
            ValueError: If multiple critics are detected for the same field.
        """
        if critics is None:
            return
        critic_fields = [critic.critic_field for critic in critics]
        duplicate_fields = {field for field in critic_fields if critic_fields.count(field) > 1}
        if duplicate_fields:
            raise ValueError(
                f"Multiple critics detected for the field(s) '{', '.join(duplicate_fields)}' in evaluation case '{name}'. Only one critic per field is permitted."
            )

    def _fill_args_with_defaults(
        self, func: Callable, provided_args: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Fill in default arguments for a tool function.

        Args:
            func: The tool function.
            provided_args: The provided arguments.

        Returns:
            A dictionary with default arguments filled in.
        """
        sig = inspect.signature(func)
        args_with_defaults = {}
        for param in sig.parameters.values():
            if param.name in provided_args:
                args_with_defaults[param.name] = provided_args[param.name]
            elif param.default is not inspect.Parameter.empty:
                args_with_defaults[param.name] = param.default
            else:
                args_with_defaults[param.name] = None  # or raise an error
        return args_with_defaults

    def extend_case(
        self,
        name: str,
        user_message: str,
        system_message: str | None = None,
        expected_tool_calls: list[ExpectedToolCall]
        | list[tuple[Callable, dict[str, Any]]]
        | None = None,
        rubric: EvalRubric | None = None,
        critics: list["Critic"] | None = None,
        additional_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Extend the last added case with new information.

        Args:
            name: The name of the extended case.
            user_message: The new user message for this extended case.
            system_message: The new system message for this extended case.
            expected_tool_calls: New or updated expected tool calls.
            rubric: A new rubric (if different from the last case).
            critics: New critics (if different from the last case).
            additional_messages: New additional messages (if different from the last case).
                to be added before the new user message.
        """
        if not self.cases:
            raise ValueError("No cases to extend. Add a case first.")

        last_case = self.cases[-1]

        # Create a new message list with the previous case's messages and user message
        new_additional_messages = [
            *last_case.additional_messages,
        ]
        if additional_messages:
            new_additional_messages.extend(additional_messages)

        expected = last_case.expected_tool_calls
        if expected_tool_calls:
            expected = [self._convert_to_named_expected_tool_call(tc) for tc in expected_tool_calls]

        # Add NoneCritics for any expected tool call fields not in the critics list
        critics = self._add_none_critics(
            expected, critics or (last_case.critics.copy() if last_case.critics else None)
        )

        self._validate_critics(critics, name)

        # Create a new case, copying from the last one and updating fields
        new_case = EvalCase(
            name=name,
            system_message=system_message or last_case.system_message,
            user_message=user_message,
            expected_tool_calls=expected,
            rubric=rubric or self.rubric,
            critics=critics,
            additional_messages=new_additional_messages,
        )
        self.cases.append(new_case)

    def _process_tool_calls(
        self,
        tool_calls: list[tuple[str, dict[str, Any]]],
        registry: EvalSuiteToolRegistry | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Process tool calls by resolving names and applying defaults.

        Args:
            tool_calls: List of (tool_name, args) tuples.
            registry: Optional registry to use. If None, uses _internal_registry.

        Returns:
            List of processed (tool_name, args_with_defaults) tuples.
        """
        effective_registry = registry or self._internal_registry
        if effective_registry is None:
            return tool_calls

        processed_calls = []
        for tool_name, args in tool_calls:
            # Resolve name and apply schema defaults (handles Anthropic "Google_Search" -> "Google.Search")
            resolved_name, args_with_defaults = effective_registry.process_tool_call(
                tool_name, args
            )

            # Apply Python function defaults if available
            if resolved_name in self._python_tool_func_map:
                args_with_defaults = self._fill_args_with_defaults(
                    self._python_tool_func_map[resolved_name], args_with_defaults
                )

            processed_calls.append((resolved_name, args_with_defaults))
        return processed_calls

    def _compute_run_field_scores(
        self, evaluation: EvaluationResult
    ) -> dict[str, dict[str, float]]:
        field_scores: dict[str, list[float]] = {}
        field_weights: dict[str, list[float]] = {}
        for result in evaluation.results:
            field = result["field"]
            if field == "tool_selection":
                continue
            field_scores.setdefault(field, []).append(result["score"])
            field_weights.setdefault(field, []).append(result["weight"])

        run_scores: dict[str, dict[str, float]] = {}
        for field, scores in field_scores.items():
            weights = field_weights.get(field, [])
            run_scores[field] = {
                "score": mean(scores) if scores else 0.0,
                "weight": mean(weights) if weights else 0.0,
            }
        return run_scores

    async def _run_case_with_stats(
        self,
        case: "EvalCase",
        client: Any,
        model: str,
        provider: ProviderName,
        *,
        num_runs: int,
        seed: str | int | None,
        pass_rule: str,
        registry: EvalSuiteToolRegistry | None = None,
    ) -> dict[str, Any]:
        if num_runs < 1:
            raise ValueError("num_runs must be >= 1")

        seed_policy, seed_value = _resolve_seed_spec(seed)
        seed_policy_display = seed_policy
        if provider == "openai":
            if seed_policy == "random":
                run_seeds: list[int | None] = [
                    random.randint(0, 2**31 - 1) for _ in range(num_runs)  # noqa: S311
                ]
            else:
                run_seeds = [seed_value for _ in range(num_runs)]
        else:
            seed_policy_display = f"{seed_policy} (ignored)"
            run_seeds = [None for _ in range(num_runs)]

        run_evaluations: list[EvaluationResult] = []
        run_scores: list[float] = []
        run_passed: list[bool] = []
        run_warned: list[bool] = []
        run_field_scores: list[dict[str, dict[str, float]]] = []
        last_processed_calls: list[tuple[str, dict[str, Any]]] = []
        run_details: list[dict[str, Any]] = []

        for run_index in range(num_runs):
            run_seed = run_seeds[run_index]
            if provider == "anthropic":
                predicted_args = await self._run_anthropic(
                    client, model, case, registry=registry
                )
            else:
                predicted_args = await self._run_openai(
                    client, model, case, registry=registry, seed=run_seed
                )

            processed_calls = self._process_tool_calls(predicted_args, registry=registry)
            evaluation = case.evaluate(processed_calls)

            run_evaluations.append(evaluation)
            run_scores.append(evaluation.score)
            run_passed.append(evaluation.passed)
            run_warned.append(evaluation.warning)
            run_field_scores.append(self._compute_run_field_scores(evaluation))
            last_processed_calls = processed_calls
            run_details.append(
                {
                    "score": evaluation.score,
                    "passed": evaluation.passed,
                    "warning": evaluation.warning,
                    "failure_reason": evaluation.failure_reason,
                    "details": evaluation.results,
                }
            )

        mean_score, std_dev = _compute_mean_std(run_scores)
        passed, warning = _resolve_pass_rule(run_evaluations, mean_score, pass_rule, case.rubric)

        aggregate = EvaluationResult(
            score=mean_score,
            passed=passed,
            warning=warning,
            results=run_evaluations[-1].results if run_evaluations else [],
            failure_reason=(
                run_evaluations[-1].failure_reason
                if pass_rule == PASS_RULE_LAST and run_evaluations
                else None
            ),
        )

        run_stats = {
            "num_runs": num_runs,
            "scores": run_scores,
            "mean_score": mean_score,
            "std_deviation": std_dev,
            "passed": run_passed,
            "warned": run_warned,
            "seed_policy": seed_policy_display,
            "run_seeds": run_seeds,
            "pass_rule": pass_rule,
            "runs": run_details,
        }

        return {
            "evaluation": aggregate,
            "predicted_tool_calls": last_processed_calls,
            "run_stats": run_stats,
            "critic_stats": _aggregate_critic_stats(run_field_scores),
        }

    async def run(
        self,
        client: Any,  # AsyncOpenAI | AsyncAnthropic - use Any to avoid import dependency
        model: str,
        provider: ProviderName = "openai",
        num_runs: int = 1,
        seed: str | int | None = "constant",
        multi_run_pass_rule: str = PASS_RULE_LAST,
    ) -> dict[str, Any]:
        """
        Run the evaluation suite.

        Args:
            client: The LLM client instance (AsyncOpenAI or AsyncAnthropic).
            model: The model to evaluate.
            provider: The provider name ("openai" or "anthropic").
            num_runs: Number of runs per case.
            seed: Seed policy ("constant", "random", or an integer seed).
            multi_run_pass_rule: How to determine pass/warn for multi-run cases.

        Returns:
            A dictionary containing the evaluation results.
        """
        results: dict[str, Any] = {
            "model": model,
            "suite_name": self.name,
            "rubric": self.rubric,
            "cases": [],
        }

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def sem_task(case: EvalCase) -> dict[str, Any]:
            async with semaphore:
                # All tools are in internal registry (unified container)
                if self._internal_registry is None or self._internal_registry.tool_count() == 0:
                    raise ValueError(
                        "No tools registered. Use add_* convenience methods or pass catalog=ToolCatalog."
                    )

                case_result = await self._run_case_with_stats(
                    case,
                    client,
                    model,
                    provider,
                    num_runs=num_runs,
                    seed=seed,
                    pass_rule=multi_run_pass_rule,
                )

                # Prepare the result
                result = {
                    "name": case.name,
                    "input": case.user_message,
                    "system_message": case.system_message,
                    "additional_messages": case.additional_messages,
                    "expected_tool_calls": [
                        {"name": tc.name, "args": tc.args} for tc in case.expected_tool_calls
                    ],
                    "predicted_tool_calls": [
                        {"name": name, "args": args}
                        for name, args in case_result["predicted_tool_calls"]
                    ],
                    "evaluation": case_result["evaluation"],
                }
                if num_runs > 1:
                    result["run_stats"] = case_result["run_stats"]
                    if case_result["critic_stats"]:
                        result["critic_stats"] = case_result["critic_stats"]
                return result

        tasks = [sem_task(case) for case in self.cases]
        case_results = await asyncio.gather(*tasks)

        results["cases"] = case_results
        return results

    async def _run_openai(
        self,
        client: AsyncOpenAI,
        model: str,
        case: "EvalCase",
        registry: EvalSuiteToolRegistry | None = None,
        seed: int | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Run evaluation using OpenAI client.

        Args:
            client: The OpenAI client.
            model: The model name.
            case: The evaluation case.
            registry: Optional registry to use. If None, uses _internal_registry.

        Returns:
            List of tool calls.
        """
        effective_registry = registry or self._internal_registry
        if effective_registry is None:
            raise RuntimeError("No registry available")

        # Prepare messages
        messages: list[dict[str, Any]] = [{"role": "system", "content": case.system_message}]
        messages.extend(case.additional_messages)
        messages.append({"role": "user", "content": case.user_message})

        tools = effective_registry.list_tools_for_model(tool_format="openai")

        # Get the model response
        request_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tool_choice": "auto",
            "tools": tools,
            "user": "eval_user",
            "stream": False,
        }
        if seed is not None:
            request_params["seed"] = seed

        response = await client.chat.completions.create(**request_params)

        return get_tool_args(response, normalize_names=False)

    async def _run_anthropic(
        self,
        client: Any,  # AsyncAnthropic
        model: str,
        case: "EvalCase",
        registry: EvalSuiteToolRegistry | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Run evaluation using Anthropic client.

        Args:
            client: The Anthropic client.
            model: The model name.
            case: The evaluation case.
            registry: Optional registry to use. If None, uses _internal_registry.

        Returns:
            List of tool calls.
        """
        effective_registry = registry or self._internal_registry
        if effective_registry is None:
            raise RuntimeError("No registry available")

        # Convert OpenAI-format messages to Anthropic format
        anthropic_messages = convert_messages_to_anthropic(case.additional_messages)
        anthropic_messages.append({"role": "user", "content": case.user_message})

        tools = effective_registry.list_tools_for_model(tool_format="anthropic")

        # Get the model response
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=case.system_message,
            messages=anthropic_messages,
            tools=tools,
        )

        # Extract tool calls from Anthropic response
        tool_calls: list[tuple[str, dict[str, Any]]] = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append((block.name, block.input))

        return tool_calls


def get_formatted_tools(catalog: "ToolCatalog", tool_format: str = "openai") -> OpenAIToolList:
    """Get the formatted tools from the catalog.

    Args:
        catalog: The catalog of Arcade tools.
        tool_format: The format of the tools to return

    Returns:
        The formatted tools.
    """
    if tool_format == "openai":
        tools = [to_openai(tool) for tool in catalog]
        return tools
    else:
        raise ValueError(f"Tool format for '{tool_format}' is not supported")


def get_tool_args(
    chat_completion: Any, normalize_names: bool = True
) -> list[tuple[str, dict[str, Any]]]:
    """
    Returns the tool arguments from the chat completion object.

    Args:
        chat_completion: The chat completion object.
        normalize_names: Whether to normalize tool names (convert _ to .).
                        Set to False for MCP tools that use underscores.

    Returns:
        A list of tuples containing the tool name and arguments.
    """
    tool_args_list: list[tuple[str, dict[str, Any]]] = []
    message = chat_completion.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            if normalize_names:
                tool_name = normalize_name(tool_name)
            tool_args_list.append((
                tool_name,
                json.loads(tool_call.function.arguments),
            ))
    return tool_args_list


def compare_tool_name(expected: str, actual: str) -> bool:
    """
    Compare the tool names by replacing all separators with the TOOL_NAME_SEPARATOR
    and comparing the normalized names.

    Converts names like 'Google_ListEmails' to 'Google.ListEmails' if
    TOOL_NAME_SEPARATOR is '.'.

    Args:
        expected: The expected tool name.
        actual: The actual tool name.

    Returns:
        True if the normalized tool names match, False otherwise.
    """
    separators = "-_."
    expected_normalized = normalize_name(expected, separators)
    actual_normalized = normalize_name(actual, separators)

    return expected_normalized.lower() == actual_normalized.lower()


def normalize_name(name: str, separators: str = "-_.") -> str:
    for sep in separators:
        if sep != TOOL_NAME_SEPARATOR:
            name = name.replace(sep, TOOL_NAME_SEPARATOR)
    return name


def tool_eval() -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
            provider_api_key: str,
            model: str,
            max_concurrency: int = 1,
            provider: ProviderName = "openai",
            capture_mode: bool = False,
            include_context: bool = False,
            num_runs: int = 1,
            seed: str | int | None = "constant",
            multi_run_pass_rule: str = PASS_RULE_LAST,
        ) -> list[Any]:
            """
            Run evaluation or capture mode.

            Returns:
                In evaluation mode: list[dict[str, Any]] with evaluation results.
                In capture mode: list[CaptureResult] with captured tool calls.
            """
            # Support both sync and async suite creation functions
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(func):
                suite = await func()
            else:
                result = func()
                # Handle case where sync func returns a coroutine
                if asyncio.iscoroutine(result):
                    suite = await result
                else:
                    suite = result

            if not isinstance(suite, EvalSuite):
                raise TypeError("Eval function must return an EvalSuite")
            suite.max_concurrent = max_concurrency

            if capture_mode:
                # Run in capture mode
                if provider == "anthropic":
                    capture_result = await _capture_with_anthropic(
                        suite,
                        provider_api_key,
                        model,
                        include_context=include_context,
                        num_runs=num_runs,
                        seed=seed,
                    )
                else:
                    capture_result = await _capture_with_openai(
                        suite,
                        provider_api_key,
                        model,
                        include_context=include_context,
                        num_runs=num_runs,
                        seed=seed,
                    )
                return [capture_result]
            else:
                # Run in evaluation mode
                if provider == "anthropic":
                    eval_result = await _run_with_anthropic(
                        suite,
                        provider_api_key,
                        model,
                        num_runs=num_runs,
                        seed=seed,
                        multi_run_pass_rule=multi_run_pass_rule,
                    )
                else:
                    eval_result = await _run_with_openai(
                        suite,
                        provider_api_key,
                        model,
                        num_runs=num_runs,
                        seed=seed,
                        multi_run_pass_rule=multi_run_pass_rule,
                    )

                # For comparative evaluations, eval_result is already a list of track results
                # For regular evaluations, it's a single dict that needs wrapping
                if isinstance(eval_result, list):
                    return eval_result
                return [eval_result]

        wrapper.__tool_eval__ = True  # type: ignore[attr-defined]
        return wrapper

    return decorator


async def _run_with_openai(
    suite: "EvalSuite",
    api_key: str,
    model: str,
    *,
    num_runs: int,
    seed: str | int | None,
    multi_run_pass_rule: str,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Run evaluation suite with OpenAI client.

    Returns:
        For regular evaluations: A single result dict.
        For comparative evaluations: A list of result dicts (one per track).
    """
    async with AsyncOpenAI(api_key=api_key) as client:
        # Check if this suite has comparative cases
        if suite._comparative_case_builders:
            # Run comparative evaluation - returns dict[track_name, result]
            track_results = await suite.run_comparative(
                client,
                model,
                provider="openai",
                num_runs=num_runs,
                seed=seed,
                multi_run_pass_rule=multi_run_pass_rule,
            )
            # Convert to list of results for consistent handling
            return list(track_results.values())
        else:
            # Run regular evaluation
            return await suite.run(
                client,
                model,
                provider="openai",
                num_runs=num_runs,
                seed=seed,
                multi_run_pass_rule=multi_run_pass_rule,
            )


async def _run_with_anthropic(
    suite: "EvalSuite",
    api_key: str,
    model: str,
    *,
    num_runs: int,
    seed: str | int | None,
    multi_run_pass_rule: str,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Run evaluation suite with Anthropic client.

    Returns:
        For regular evaluations: A single result dict.
        For comparative evaluations: A list of result dicts (one per track).
    """
    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:
        raise ImportError(
            "The 'anthropic' package is required for Anthropic provider. "
            "Install it with: pip install anthropic"
        ) from e

    async with AsyncAnthropic(api_key=api_key) as client:
        # Check if this suite has comparative cases
        if suite._comparative_case_builders:
            # Run comparative evaluation - returns dict[track_name, result]
            track_results = await suite.run_comparative(
                client,
                model,
                provider="anthropic",
                num_runs=num_runs,
                seed=seed,
                multi_run_pass_rule=multi_run_pass_rule,
            )
            # Convert to list of results for consistent handling
            return list(track_results.values())
        else:
            # Run regular evaluation
            return await suite.run(
                client,
                model,
                provider="anthropic",
                num_runs=num_runs,
                seed=seed,
                multi_run_pass_rule=multi_run_pass_rule,
            )
