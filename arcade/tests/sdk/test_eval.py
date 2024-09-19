import pytest

from arcade.sdk.error import WeightError
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    ExpectedToolCall,
    NumericCritic,
    SimilarityCritic,
)
from arcade.sdk.eval.eval import EvalCase, EvaluationResult

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
        ExpectedToolCall(name="ToolA", args={"param": "value1"}),
        ExpectedToolCall(name="ToolB", args={"param": "value2"}),
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
        ExpectedToolCall(name="ToolA", args={"param": "value"}),
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
        ExpectedToolCall(name="ToolA", args={"param1": "value1", "param2": "value2"}),
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


@pytest.mark.parametrize(
    "expected_args, actual_args, expected_score",
    [
        ({"param": "value"}, {}, 1.0),  # Missing actual value
        ({}, {"param": "value"}, 1.0),  # Missing expected value
        ({"param": "value"}, {"param": "value"}, 2.0),  # Both values present
    ],
)
def test_eval_case_missing_values(expected_args, actual_args, expected_score):
    """
    Test that when either expected or actual values are missing for a critic,
    the critic evaluation is skipped, and the total score is computed accordingly.
    """
    expected_tool_calls = [ExpectedToolCall(name="ToolA", args=expected_args)]
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

    # If critic is skipped, only tool selection score is counted
    # Otherwise, tool selection + critic score
    total_weight = 1.0  # At least tool selection weight
    if "param" in expected_args and "param" in actual_args:
        total_weight += 1.0  # Critic weight

    expected_total_score = expected_score / total_weight

    assert result.score == expected_total_score


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
