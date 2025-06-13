from unittest.mock import Mock

import pytest
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    ExpectedToolCall,
    NamedExpectedToolCall,
    NoneCritic,
    SimilarityCritic,
)
from arcade_evals.eval import EvalCase, EvalSuite, EvaluationResult
from arcade_tdk import tool


@tool
def mock_tool(param1: str):
    pass


@tool
def mock_tool_no_args():
    pass


@tool
def mock_tool_multiple_args(
    param1: str, param2: str, param3: str = "value3", param4: str = "value4"
):
    pass


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


# Test EvalSuite.add_case()
def test_eval_suite_add_case():
    """
    Test that add_case correctly adds a new evaluation case to the suite.
    """
    mock_catalog = Mock()
    mock_catalog.find_tool_by_func.return_value.get_fully_qualified_name.return_value = "MockTool"

    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    expected_tool_calls = [
        ExpectedToolCall(
            func=mock_tool,
            args={"param1": "value"},
        ),
        (
            mock_tool,
            {"param1": "value"},
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
        name="MockTool", args={"param1": "value"}
    )
    assert case.expected_tool_calls[1] == NamedExpectedToolCall(
        name="MockTool", args={"param1": "value"}
    )


# Test EvalSuite.extend_case()
def test_eval_suite_extend_case():
    """
    Test that extend_case correctly extends the last added case with new information.
    """
    mock_catalog = Mock()
    mock_catalog.find_tool_by_func.return_value.get_fully_qualified_name.return_value = "MockTool"

    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    expected_tool_calls = [
        ExpectedToolCall(
            func=mock_tool,
            args={"param1": "value"},
        ),
        (
            mock_tool,
            {"param1": "value"},
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
        name="MockTool", args={"param1": "value"}
    )
    assert extended_case.expected_tool_calls[1] == NamedExpectedToolCall(
        name="MockTool", args={"param1": "value"}
    )


def test_eval_suite_validate_critics_raises_value_error():
    """
    Test that validate_critics raises a ValueError if multiple critics are detected for the same field.
    """
    mock_catalog = Mock()
    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    case_name = "TestCase"
    critics = [
        BinaryCritic(critic_field="param", weight=0.5),
        SimilarityCritic(critic_field="param", weight=0.5),
    ]
    with pytest.raises(ValueError):
        suite._validate_critics(critics, case_name)


def test_eval_suite_validate_critics_no_error():
    """
    Test that validate_critics does not raise an error when critics are valid.
    """
    mock_catalog = Mock()
    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    case_name = "TestCase"
    critics = [
        BinaryCritic(critic_field="param1", weight=0.5),
    ]

    suite._validate_critics(critics, case_name)


@pytest.mark.parametrize(
    "expected_tool_calls, critics, expected_critics_count, expected_critics_types",
    [
        (
            # Test case 1: No arguments, expect no critics
            [NamedExpectedToolCall(name="MockToolNoArgs", args={})],
            None,
            0,
            [],
        ),
        (
            # Test case 2: Single argument, expect one NoneCritic
            [NamedExpectedToolCall(name="MockTool", args={"param1": "value"})],
            None,
            1,
            [(NoneCritic, "param1")],
        ),
        (
            # Test case 3: Multiple arguments with some critics, expect BinaryCritics for specified fields and NoneCritics for others
            [
                NamedExpectedToolCall(
                    name="MockToolMultipleArgs",
                    args={
                        "param1": "value1",
                        "param2": "value2",
                        "param3": "value3",
                        "param4": "value4",
                    },
                )
            ],
            [
                BinaryCritic(critic_field="param1", weight=0.5),
                BinaryCritic(critic_field="param2", weight=0.5),
            ],
            4,
            [
                (BinaryCritic, "param1"),
                (BinaryCritic, "param2"),
                (NoneCritic, "param3"),
                (NoneCritic, "param4"),
            ],
        ),
        (
            # Test case 4: Mixed tool calls with multiple critics, expect BinaryCritics for specified fields and NoneCritics for others
            [
                NamedExpectedToolCall(name="MockTool", args={"param1": "value"}),
                NamedExpectedToolCall(name="MockToolNoArgs", args={}),
                NamedExpectedToolCall(
                    name="MockToolMultipleArgs",
                    args={
                        "param1": "value1",
                        "param2": "value2",
                        "param3": "value3",
                        "param4": "value4",
                    },
                ),
            ],
            [
                BinaryCritic(critic_field="param1", weight=0.3),
                BinaryCritic(critic_field="param2", weight=0.3),
                BinaryCritic(critic_field="param3", weight=0.3),
            ],
            4,
            [
                (BinaryCritic, "param1"),
                (BinaryCritic, "param2"),
                (BinaryCritic, "param3"),
                (NoneCritic, "param4"),
            ],
        ),
    ],
)
def test_eval_suite_add_none_critics(
    expected_tool_calls, critics, expected_critics_count, expected_critics_types
):
    mock_catalog = Mock()
    suite = EvalSuite(name="TestSuite", system_message="System message", catalog=mock_catalog)

    critics_with_none = suite._add_none_critics(expected_tool_calls, critics)
    assert len(critics_with_none) == expected_critics_count
    for i, (expected_type, expected_field) in enumerate(expected_critics_types):
        assert isinstance(critics_with_none[i], expected_type)
        assert critics_with_none[i].critic_field == expected_field
