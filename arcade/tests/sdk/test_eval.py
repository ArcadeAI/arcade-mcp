from datetime import timedelta
from unittest.mock import Mock

import pytest
import pytz
from dateutil import parser

from arcade.sdk import tool
from arcade.sdk.errors import WeightError
from arcade.sdk.eval import (
    BinaryCritic,
    DatetimeCritic,
    EvalRubric,
    ExpectedToolCall,
    NamedExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
)
from arcade.sdk.eval.eval import EvalCase, EvalSuite, EvaluationResult

# Test BinaryCritic.evaluate()


@pytest.mark.parametrize(
    "expected, actual, weight, expected_match, expected_score",
    [
        ("value", "value", 1.0, True, 1.0),
        ("value", "different", 1.0, False, 0.0),
        (10, 10, 0.5, True, 0.5),
        (10, 20, 0.5, False, 0.0),
    ],
)
def test_binary_critic_evaluate(expected, actual, weight, expected_match, expected_score):
    """
    Test the BinaryCritic's evaluate method to ensure it correctly computes
    the match and score based on expected and actual values.
    """
    critic = BinaryCritic(critic_field="test_field", weight=weight)
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert result["score"] == expected_score


# Test NumericCritic.evaluate()


@pytest.mark.parametrize(
    "expected, actual, value_range, weight, match_threshold, expected_match, expected_score",
    [
        (5, 5, (0, 10), 1.0, 0.8, True, 1.0),
        (5, 6, (0, 10), 1.0, 0.8, True, 0.9),
        (0, 10, (0, 10), 1.0, 0.8, False, 0.0),
        (2, 8, (0, 10), 1.0, 0.5, False, 0.4),
        (50, 60, (0, 100), 0.5, 0.9, True, 0.45),
    ],
)
def test_numeric_critic_evaluate(
    expected, actual, value_range, weight, match_threshold, expected_match, expected_score
):
    """
    Test the NumericCritic's evaluate method to ensure it calculates
    the correct score based on the proportion of the difference between
    expected and actual values within a specified range.
    """
    critic = NumericCritic(
        critic_field="number",
        weight=weight,
        value_range=value_range,
        match_threshold=match_threshold,
    )
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert pytest.approx(result["score"], 0.01) == expected_score


# Test SimilarityCritic.evaluate()


@pytest.mark.parametrize(
    "expected, actual, weight, similarity_threshold, expected_match, min_expected_score",
    [
        ("hello world", "hello world", 1.0, 0.8, True, 1.0),
        ("hello world", "hello", 1.0, 0.8, False, 0.0),
        ("The quick brown fox", "The quick brown fox jumps over the lazy dog", 1.0, 0.5, True, 0.5),
        ("data science", "machine learning", 0.5, 0.3, False, 0.0),
    ],
)
def test_similarity_critic_evaluate(
    expected, actual, weight, similarity_threshold, expected_match, min_expected_score
):
    """
    Test the SimilarityCritic's evaluate method to ensure it computes
    the similarity score between expected and actual strings and determines
    the match correctly based on the similarity threshold.
    """
    critic = SimilarityCritic(
        critic_field="text",
        weight=weight,
        similarity_threshold=similarity_threshold,
    )
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert result["score"] >= min_expected_score
    assert result["score"] >= 0.0
    assert result["score"] <= weight + 1e-6  # Allow a small epsilon for floating-point comparison


# Test EvaluationResult accumulation and pass/fail logic


def test_evaluation_result_accumulation():
    """
    Test that EvaluationResult correctly accumulates scores and determines
    pass/fail status based on thresholds.
    """
    evaluation = EvaluationResult()
    evaluation.add(
        field="field1",
        result={"match": True, "score": 0.8},
        weight=1.0,
        expected="expected_value",
        actual="actual_value",
    )
    evaluation.add(
        field="field2",
        result={"match": False, "score": 0.0},
        weight=0.5,
        expected="expected_value",
        actual="actual_value",
    )
    total_weight = 1.5
    expected_score = (0.8 * 1.0 + 0.0 * 0.5) / total_weight
    evaluation.compute_final_score(total_weight)
    assert evaluation.score == expected_score


# Test EvalCase.evaluate()


def test_eval_case_evaluate():
    """
    Test EvalCase's evaluate method to ensure it calculates the overall score
    correctly based on tool selection and critics, and applies the rubric's
    thresholds to determine pass/fail/warning status.
    """
    # Define expected tool calls and actual tool calls
    expected_tool_calls = [
        NamedExpectedToolCall(name="ToolA", args={"param": "value1"}),
        NamedExpectedToolCall(name="ToolB", args={"param": "value2"}),
    ]
    actual_tool_calls = [
        ("ToolA", {"param": "value1"}),
        ("ToolB", {"param": "wrong_value"}),
    ]

    # Define critics
    critics = [
        BinaryCritic(critic_field="param", weight=1.0),
    ]

    # Create EvalCase with a rubric
    case = EvalCase(
        name="TestCase",
        system_message="System message",
        user_message="User message",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(fail_threshold=0.75, warn_threshold=0.9, tool_selection_weight=1.0),
    )

    # Evaluate the case
    result = case.evaluate(actual_tool_calls)

    # Expected calculations:
    # - Tool selection score should be 2 * 1.0 = 2.0 (both tools are correct)
    # - First critic score: match (1.0)
    # - Second critic score: no match (0.0)
    # - Total critic score: 1.0 + 0.0 = 1.0
    # - Total weight: tool selection (2.0) + critics (2.0) = 4.0
    # - Total score: (2.0 + 1.0) / 4.0 = 0.75

    assert result.score == 0.75
    assert result.passed is True


# Test EvalCase with mismatched tool calls


def test_eval_case_evaluate_mismatched_tools():
    """
    Test EvalCase's evaluate method when the actual tool calls do not match
    the expected tool calls to ensure tool selection scoring is correct.
    """
    expected_tool_calls = [
        NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
    ]
    actual_tool_calls = [
        ("ToolB", {"param": "value"}),
    ]

    critics = [BinaryCritic(critic_field="param", weight=1.0)]

    case = EvalCase(
        name="TestCase",
        system_message="",
        user_message="",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(tool_selection_weight=1.0),
    )

    result = case.evaluate(actual_tool_calls)

    # Tool selection score should be 0.0 since the tools don't match
    # Critic is not evaluated since the tool selection failed
    # Total score: 0.0

    assert result.score == 0.0
    assert result.passed is False


# Test EvalCase with multiple critics and weights


def test_eval_case_multiple_critics():
    """
    Test EvalCase's evaluate method with multiple critics having different weights
    to ensure individual critic scores are correctly combined into the total score.
    """
    expected_tool_calls = [
        NamedExpectedToolCall(name="ToolA", args={"param1": "value1", "param2": "value2"}),
    ]
    actual_tool_calls = [
        ("ToolA", {"param1": "value1", "param2": "wrong_value"}),
    ]

    critics = [
        BinaryCritic(critic_field="param1", weight=0.6),
        SimilarityCritic(critic_field="param2", weight=0.4, similarity_threshold=0.8),
    ]

    case = EvalCase(
        name="TestCase",
        system_message="",
        user_message="",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(fail_threshold=0.7),
    )

    result = case.evaluate(actual_tool_calls)

    # Tool selection score: 1.0
    # Critic scores:
    # - param1: match (score 0.6)
    # - param2: likely not match (score ~0.0)
    # Total score: (1.0 + 0.6 + 0.0) / (1.0 + 0.6 + 0.4) = 1.6 / 2.0 = 0.8

    assert pytest.approx(result.score, 0.01) == 0.8
    assert result.passed


# Test EvalCase with missing expected and actual values in args


def test_eval_case_with_none_values():
    """
    Test that when expected or actual values are None, the critic evaluates them appropriately.
    """
    expected_args = {"param": None}
    actual_args = {"param": None}

    expected_tool_calls = [NamedExpectedToolCall(name="ToolA", args=expected_args)]
    actual_tool_calls = [("ToolA", actual_args)]

    critics = [BinaryCritic(critic_field="param", weight=1.0)]

    case = EvalCase(
        name="TestCase",
        system_message="",
        user_message="",
        expected_tool_calls=expected_tool_calls,
        critics=critics,
        rubric=EvalRubric(tool_selection_weight=1.0),
    )

    result = case.evaluate(actual_tool_calls)

    # Both values are None, so the critic should return a match
    assert result.score == 2.0 / 2.0  # Full score (tool selection + critic score)


# Test that WeightError is raised for invalid critic weights


@pytest.mark.parametrize(
    "critic_class, weight",
    [
        (BinaryCritic, -0.1),
        (BinaryCritic, 1.1),
        (NumericCritic, -0.5),
        (SimilarityCritic, 1.5),
    ],
)
def test_critic_invalid_weight(critic_class, weight):
    """
    Test that initializing a critic with an invalid weight raises a WeightError.
    """
    with pytest.raises(WeightError):
        if critic_class == NumericCritic:
            critic_class(critic_field="test_field", weight=weight, value_range=(0, 1))
        elif critic_class == SimilarityCritic:
            critic_class(critic_field="test_field", weight=weight)
        else:
            critic_class(critic_field="test_field", weight=weight)


# Test NumericCritic with invalid value range


def test_numeric_critic_invalid_range():
    """
    Test that initializing a NumericCritic with an invalid value range raises a ValueError.
    """
    with pytest.raises(ValueError):
        NumericCritic(critic_field="number", weight=1.0, value_range=(10, 0))  # Invalid range


# Test SimilarityCritic with unsupported metric


def test_similarity_critic_unsupported_metric():
    """
    Test that initializing a SimilarityCritic with an unsupported metric raises a ValueError.
    """
    with pytest.raises(ValueError):
        SimilarityCritic(critic_field="text", weight=1.0, metric="unsupported_metric")


# Test DatetimeCritic


# Parameterized tests for DatetimeCritic with various datetime formats and default timezones
@pytest.mark.parametrize(
    "critic_params, expected, actual, expected_match, expected_score",
    [
        # Test with time component and timezone
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00-07:00",
            "2024-09-26T12:00:00-07:00",
            True,
            1.0,
        ),
        # Test without time component (dates only)
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26",
            "2024-09-26",
            True,
            1.0,
        ),
        # Test with and without timezone (assumes UTC)
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00Z",
            "2024-09-26T12:00:00",
            True,
            1.0,
        ),
        # Test naive datetimes
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00",
            "2024-09-26T12:00:00",
            True,
            1.0,
        ),
    ],
)
def test_datetime_critic_basic(critic_params, expected, actual, expected_match, expected_score):
    """
    Test DatetimeCritic with various datetime formats and default timezones.
    """
    critic = DatetimeCritic(**critic_params)
    result = critic.evaluate(expected, actual)
    assert result["match"] == expected_match
    assert result["score"] == expected_score


# Parameterized tests for DatetimeCritic's handling of tolerances and max differences
@pytest.mark.parametrize(
    "critic_params, expected, actual, expected_match, expected_score_func",
    [
        # Test time difference within tolerance
        (
            {"critic_field": "start_datetime", "weight": 1.0, "tolerance": timedelta(seconds=60)},
            "2024-09-26T12:00:00",
            "2024-09-26T12:00:30",
            True,
            lambda critic: critic.weight,
        ),
        # Test time difference outside tolerance but within max_difference
        (
            {
                "critic_field": "start_datetime",
                "weight": 1.0,
                "tolerance": timedelta(seconds=60),
                "max_difference": timedelta(minutes=5),
            },
            "2024-09-26T12:00:00",
            "2024-09-26T12:04:00",
            False,
            lambda critic: critic.weight * (1 - (240 / 300)),
        ),
        # Test time difference exceeds max_difference
        (
            {
                "critic_field": "start_datetime",
                "weight": 1.0,
                "max_difference": timedelta(minutes=5),
            },
            "2024-09-26T12:00:00",
            "2024-09-26T12:10:00",
            False,
            lambda critic: 0.0,
        ),
    ],
)
def test_datetime_critic_tolerances(
    critic_params, expected, actual, expected_match, expected_score_func
):
    """
    Test DatetimeCritic's handling of tolerances and max differences.
    """
    critic = DatetimeCritic(**critic_params)
    result = critic.evaluate(expected, actual)
    assert result["match"] == expected_match
    expected_score = expected_score_func(critic)
    assert pytest.approx(result["score"], abs=1e-6) == expected_score


def test_datetime_critic_naive_and_timezone_aware():
    """
    Test DatetimeCritic when comparing naive and timezone-aware datetimes.
    """
    critic = DatetimeCritic(critic_field="start_datetime", weight=1.0)
    expected = "2024-09-26T12:00:00Z"
    actual = "2024-09-26T07:00:00"
    result = critic.evaluate(expected, actual)
    assert result["match"] is False

    # Compute expected score based on time difference
    expected_dt = parser.parse(expected)
    actual_dt = parser.parse(actual)
    if actual_dt.tzinfo is None:
        actual_dt = pytz.utc.localize(actual_dt)
    if expected_dt.tzinfo is None:
        expected_dt = pytz.utc.localize(expected_dt)

    time_diff_seconds = abs((expected_dt - actual_dt).total_seconds())
    if time_diff_seconds <= critic.tolerance.total_seconds():
        expected_score = critic.weight
    elif time_diff_seconds >= critic.max_difference.total_seconds():
        expected_score = 0.0
    else:
        ratio = 1 - (time_diff_seconds / critic.max_difference.total_seconds())
        expected_score = critic.weight * ratio

    assert pytest.approx(result["score"], abs=1e-6) == expected_score


# Test EvalSuite.add_case()
def test_eval_suite_add_case():
    """
    Test that add_case correctly adds a new evaluation case to the suite.
    """

    @tool
    def mock_tool(param: str):
        pass

    mock_catalog = Mock()
    mock_catalog.find_tool_by_func.return_value.get_fully_qualified_name.return_value = "MockTool"

    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    expected_tool_calls = [
        ExpectedToolCall(
            func=mock_tool,
            args={"param": "value"},
        ),
        (
            mock_tool,
            {"param": "value"},
        ),
    ]

    suite.add_case(
        name="TestCase",
        user_message="User message",
        expected_tool_calls=expected_tool_calls,
    )

    assert len(suite.cases) == 1
    case = suite.cases[0]
    assert len(case.expected_tool_calls) == 2
    assert case.name == "TestCase"
    assert case.user_message == "User message"
    assert case.system_message == "System message"
    assert case.expected_tool_calls[0] == NamedExpectedToolCall(
        name="MockTool", args={"param": "value"}
    )
    assert case.expected_tool_calls[1] == NamedExpectedToolCall(
        name="MockTool", args={"param": "value"}
    )


# Test EvalSuite.extend_case()
def test_eval_suite_extend_case():
    """
    Test that extend_case correctly extends the last added case with new information.
    """

    @tool
    def mock_tool(param: str):
        pass

    mock_catalog = Mock()
    mock_catalog.find_tool_by_func.return_value.get_fully_qualified_name.return_value = "MockTool"

    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    expected_tool_calls = [
        ExpectedToolCall(
            func=mock_tool,
            args={"param": "value"},
        ),
        (
            mock_tool,
            {"param": "value"},
        ),
    ]

    suite.add_case(
        name="InitialCase",
        user_message="Initial user message",
        expected_tool_calls=expected_tool_calls,
    )

    suite.extend_case(
        name="ExtendedCase",
        user_message="Extended user message",
        expected_tool_calls=expected_tool_calls,
    )

    assert len(suite.cases) == 2
    initial_case = suite.cases[0]
    extended_case = suite.cases[1]

    assert initial_case.name == "InitialCase"
    assert extended_case.name == "ExtendedCase"
    assert extended_case.user_message == "Extended user message"
    assert extended_case.system_message == "System message"
    assert len(extended_case.expected_tool_calls) == 2
    assert extended_case.expected_tool_calls[0] == NamedExpectedToolCall(
        name="MockTool", args={"param": "value"}
    )
    assert extended_case.expected_tool_calls[1] == NamedExpectedToolCall(
        name="MockTool", args={"param": "value"}
    )
