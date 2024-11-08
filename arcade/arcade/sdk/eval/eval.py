import asyncio
import functools
import inspect
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from arcade.core.config_model import Config
from arcade.core.schema import TOOL_NAME_SEPARATOR

try:
    import numpy as np
    from scipy.optimize import linear_sum_assignment
except ImportError:
    raise ImportError(
        "Use `pip install arcade-ai[evals]` to install the required dependencies for evaluation."
    )

from openai import AsyncOpenAI

from arcade.sdk.errors import WeightError

if TYPE_CHECKING:
    from arcade.sdk import ToolCatalog
    from arcade.sdk.eval.critic import Critic


@dataclass
class ExpectedToolCall:
    """
    Represents an expected tool call with its name and arguments.

    Attributes:
        name: The name of the tool.
        args: A dictionary containing the expected arguments for the tool.
    """

    name: str
    args: dict[str, Any]


@dataclass
class EvalRubric:
    """
    Defines the rubric for evaluating an AI model's performance on a task.

    Attributes:
        fail_threshold: The minimum score required to pass the evaluation (between 0.0 and 1.0).
        warn_threshold: The score threshold for issuing a warning (between 0.0 and 1.0).
        fail_on_tool_selection: Whether to fail the evaluation if the tool selection is incorrect.
        fail_on_tool_call_quantity: Whether to fail the evaluation if the number of tool calls is incorrect.
        tool_selection_weight: The weight assigned to the tool selection score (between 0.0 and 1.0).
    """

    fail_threshold: float = 0.8
    warn_threshold: float = 0.9
    fail_on_tool_selection: bool = True
    fail_on_tool_call_quantity: bool = True
    tool_selection_weight: float = 1.0

    def __str__(self) -> str:
        return f"Fail threshold: {self.fail_threshold}\nWarn threshold: {self.warn_threshold}\n"


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
        return not self.passed and not self.warning

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


@dataclass
class EvalCase:
    """
    Represents a single evaluation case within an EvalSuite.

    Attributes:
        name: A descriptive name for this evaluation case.
        system_message: The system message to be sent to the AI model.
        user_message: The user input to be sent to the AI model.
        expected_tool_calls: A list of ExpectedToolCall objects representing the expected tool calls.
        critics: A list of Critic objects used to evaluate tool arguments.
        additional_messages: Optional list of additional context messages.
        rubric: An EvalRubric object defining pass/fail criteria and tool selection behavior.
    """

    name: str
    system_message: str
    user_message: str
    expected_tool_calls: list[ExpectedToolCall]
    critics: list["Critic"] | None = None
    additional_messages: list[dict[str, str]] = field(default_factory=list)
    rubric: EvalRubric = field(default_factory=EvalRubric)

    def __post_init__(self) -> None:
        if self.critics is not None:
            self._validate_critics()
        else:
            # if no critics are provided, set to empty list
            self.critics = []

    def _validate_critics(self) -> None:
        """
        Validate the sum of critic weights.

        Raises:
            WeightError: If the sum of critic weights exceeds 1.0.
        """
        if not self.critics:
            return

        total_weight = sum(critic.weight for critic in self.critics)
        if total_weight > 1.0:
            raise WeightError(f"Sum of critic weights must not exceed 1.0, got {total_weight}")

        for critic in self.critics:
            if critic.weight < 0.1:
                raise WeightError(f"Critic weights should be at least 0.1, got {critic.weight}")

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
                        total_weight += critic.weight
                        evaluation_result.add(
                            critic.critic_field,
                            result,
                            critic.weight,
                            expected_value,
                            actual_value,
                        )
                    except Exception as e:
                        # TODO: log or console
                        print(f"Critic evaluation failed for field '{critic.critic_field}': {e}")
                        evaluation_result.add(
                            critic.critic_field,
                            {"match": False, "score": 0.0},
                            critic.weight,
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
        expected_tool_calls: list[ExpectedToolCall],
    ) -> np.ndarray:
        """
        Create a cost matrix for the assignment problem.

        Args:
            actual_tool_calls: A list of tuples of actual tool calls.
            expected_tool_calls: A list of ExpectedToolCall instances.

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
                                print(
                                    f"Critic evaluation failed for field '{critic.critic_field}': {e}"
                                )
                    cost_matrix[i, j] = score

        return cost_matrix


@dataclass
class EvalSuite:
    """
    A suite for evaluating AI model performance on specific tasks or scenarios.

    EvalSuite manages a collection of EvalCases, each representing a specific test scenario.
    It provides methods to add cases, register tools, and run evaluations against specified models.

    Attributes:
        name: The name of the evaluation suite.
        system_message: The system message to be used for all cases in this suite.
        catalog: A ToolCatalog object containing registered tools.
        cases: A list of EvalCase objects representing individual test scenarios.
        rubric: The evaluation rubric for this case.
        max_concurrent: Maximum number of concurrent evaluations.
    """

    name: str
    system_message: str
    catalog: "ToolCatalog"
    cases: list[EvalCase] = field(default_factory=list)
    rubric: EvalRubric = field(default_factory=EvalRubric)
    max_concurrent: int = 1

    def add_case(
        self,
        name: str,
        user_message: str,
        expected_tool_calls: list[tuple[Callable, dict[str, Any]]],
        critics: list["Critic"] | None = None,
        system_message: str | None = None,
        rubric: EvalRubric | None = None,
        additional_messages: list[dict[str, str]] | None = None,
    ) -> None:
        """
        Add a new evaluation case to the suite.

        Args:
            name: The name of the evaluation case.
            user_message: The user's input message.
            expected_tool_calls: A list of expected tool calls as tuples of (function, args).
            critics: List of critics to evaluate the tool arguments.
            system_message: The system message to be used.
            rubric: The evaluation rubric for this case.
            additional_messages: Optional list of additional messages for context.
        """
        expected = []
        for func, args in expected_tool_calls:
            # Fill in default arguments here
            args_with_defaults = self._fill_args_with_defaults(func, args)
            tool_name = str(self.catalog.find_tool_by_func(func).get_fully_qualified_name())
            expected.append(ExpectedToolCall(name=tool_name, args=args_with_defaults))

        case = EvalCase(
            name=name,
            system_message=system_message or self.system_message,
            user_message=user_message,
            expected_tool_calls=expected,
            rubric=rubric or self.rubric,
            critics=critics,
            additional_messages=additional_messages or [],
        )
        self.cases.append(case)

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
        expected_tool_calls: list[tuple[Callable, dict[str, Any]]] | None = None,
        rubric: EvalRubric | None = None,
        critics: list["Critic"] | None = None,
        additional_messages: list[dict[str, str]] | None = None,
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
            expected = []
            for func, args in expected_tool_calls:
                # Fill in default arguments here
                args_with_defaults = self._fill_args_with_defaults(func, args)
                tool_name = str(self.catalog.find_tool_by_func(func).get_fully_qualified_name())
                expected.append(ExpectedToolCall(name=tool_name, args=args_with_defaults))

        # Create a new case, copying from the last one and updating fields
        new_case = EvalCase(
            name=name,
            system_message=system_message or last_case.system_message,
            user_message=user_message,
            expected_tool_calls=expected,
            rubric=rubric or self.rubric,
            critics=critics or (last_case.critics.copy() if last_case.critics else None),
            additional_messages=new_additional_messages,
        )
        self.cases.append(new_case)

    async def run(self, client: AsyncOpenAI, model: str) -> dict[str, Any]:
        """
        Run the evaluation suite.

        Args:
            client: The AsyncOpenAI client instance.
            model: The model to evaluate.

        Returns:
            A dictionary containing the evaluation results.
        """
        results: dict[str, Any] = {"model": model, "rubric": self.rubric, "cases": []}

        semaphore = asyncio.Semaphore(self.max_concurrent)
        tool_names = list(self.catalog.get_tool_names())

        async def sem_task(case: EvalCase) -> dict[str, Any]:
            async with semaphore:
                # Prepare messages
                messages = [{"role": "system", "content": case.system_message}]
                messages.extend(case.additional_messages)
                messages.append({"role": "user", "content": case.user_message})

                # Get the model response
                response = await client.chat.completions.create(  # type: ignore[call-overload]
                    model=model,
                    messages=messages,
                    tool_choice="auto",
                    tools=(str(name) for name in tool_names),
                    user="eval_user",
                    stream=False,
                )

                # Extract and fill default arguments for actual tool calls
                predicted_args = get_tool_args(response)
                filled_actual_tool_calls = []
                for tool_name, args in predicted_args:
                    tool = self.catalog.get_tool_by_name(tool_name)
                    if tool is None:
                        raise ValueError(f"Tool '{tool_name}' not found in catalog.")
                    func = tool.tool
                    args_with_defaults = self._fill_args_with_defaults(func, args)
                    filled_actual_tool_calls.append((tool_name, args_with_defaults))

                # Evaluate the case
                evaluation = case.evaluate(filled_actual_tool_calls)

                # Prepare the result
                result = {
                    "name": case.name,
                    "input": case.user_message,
                    "expected_tool_calls": [
                        {"name": tc.name, "args": tc.args} for tc in case.expected_tool_calls
                    ],
                    "predicted_tool_calls": [
                        {"name": name, "args": args} for name, args in filled_actual_tool_calls
                    ],
                    "evaluation": evaluation,
                }
                return result

        tasks = [sem_task(case) for case in self.cases]
        case_results = await asyncio.gather(*tasks)

        results["cases"] = case_results
        return results


def get_tool_args(chat_completion: Any) -> list[tuple[str, dict[str, Any]]]:
    """
    Returns the tool arguments from the chat completion object.

    Args:
        chat_completion: The chat completion object.

    Returns:
        A list of tuples containing the tool name and arguments.
    """
    tool_args_list: list[tuple[str, dict[str, Any]]] = []
    message = chat_completion.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            tool_args_list.append((
                normalize_name(tool_call.function.name),
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
            config: Config,
            base_url: str,
            model: str,
            max_concurrency: int = 1,
        ) -> list[dict[str, Any]]:
            suite = func()
            if not isinstance(suite, EvalSuite):
                raise TypeError("Eval function must return an EvalSuite")
            suite.max_concurrent = max_concurrency
            results = []
            async with AsyncOpenAI(
                api_key=config.api.key,
                base_url=base_url + "/v1",
            ) as client:
                result = await suite.run(client, model)
                results.append(result)
            return results

        wrapper.__tool_eval__ = True  # type: ignore[attr-defined]
        return wrapper

    return decorator
