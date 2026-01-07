import pytest
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    ExpectedMCPToolCall,
    ExpectedToolCall,
    NamedExpectedToolCall,
    NoneCritic,
    SimilarityCritic,
)
from arcade_evals.eval import EvalCase, EvalSuite, EvaluationResult
from arcade_tdk import tool

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


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


class TestEvaluationResultProperties:
    """Tests for EvaluationResult.passed, .fail, and .warn properties."""

    def test_passed_true_no_warning(self):
        """Test .passed=True, .fail=False, .warn=False for passing evaluation."""
        evaluation = EvaluationResult()
        evaluation.passed = True
        evaluation.warning = False

        assert evaluation.passed is True
        assert evaluation.fail is False
        assert evaluation.warn is False

    def test_passed_true_with_warning(self):
        """Test .passed=True, .fail=False, .warn=True for passing with warning."""
        evaluation = EvaluationResult()
        evaluation.passed = True
        evaluation.warning = True

        assert evaluation.passed is True
        assert evaluation.fail is False
        assert evaluation.warn is True

    def test_not_passed_with_warning(self):
        """Test that warning=True does NOT classify as fail."""
        evaluation = EvaluationResult()
        evaluation.passed = False
        evaluation.warning = True

        # This is the key case: warning should NOT be a fail
        assert evaluation.passed is False
        assert evaluation.fail is False  # Not passed but warning, so not a fail
        assert evaluation.warn is True

    def test_not_passed_no_warning_is_fail(self):
        """Test .passed=False, .warning=False means it's a real fail."""
        evaluation = EvaluationResult()
        evaluation.passed = False
        evaluation.warning = False

        assert evaluation.passed is False
        assert evaluation.fail is True
        assert evaluation.warn is False

    def test_fail_property_distinguishes_warnings_from_failures(self):
        """Test that the fail property correctly excludes warnings from failures."""
        # Case 1: Passed - not a fail
        passed_eval = EvaluationResult()
        passed_eval.passed = True
        passed_eval.warning = False
        assert passed_eval.fail is False

        # Case 2: Warning (not passed but warning set) - not a fail
        warning_eval = EvaluationResult()
        warning_eval.passed = False
        warning_eval.warning = True
        assert warning_eval.fail is False

        # Case 3: Actual failure (not passed and not warning) - is a fail
        failed_eval = EvaluationResult()
        failed_eval.passed = False
        failed_eval.warning = False
        assert failed_eval.fail is True


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
    suite = EvalSuite(name="TestSuite", system_message="System message")

    expected_tool_calls = [
        ExpectedMCPToolCall(tool_name="MockTool", args={"param1": "value"}),
        ExpectedMCPToolCall(tool_name="MockTool", args={"param1": "value"}),
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
    suite = EvalSuite(name="TestSuite", system_message="System message")

    expected_tool_calls = [
        ExpectedMCPToolCall(tool_name="MockTool", args={"param1": "value"}),
        ExpectedMCPToolCall(tool_name="MockTool", args={"param1": "value"}),
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
    suite = EvalSuite(name="TestSuite", system_message="System message")

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
    suite = EvalSuite(name="TestSuite", system_message="System message")

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
    suite = EvalSuite(name="TestSuite", system_message="System message")

    critics_with_none = suite._add_none_critics(expected_tool_calls, critics)
    assert len(critics_with_none) == expected_critics_count
    for i, (expected_type, expected_field) in enumerate(expected_critics_types):
        assert isinstance(critics_with_none[i], expected_type)
        assert critics_with_none[i].critic_field == expected_field


# =============================================================================
# Tests for ExpectedToolCall and ExpectedMCPToolCall classes
# =============================================================================


class TestExpectedToolCall:
    """Tests for the ExpectedToolCall dataclass (Python tools)."""

    def test_keyword_args(self):
        """Test creating with keyword arguments."""
        tc = ExpectedToolCall(func=mock_tool, args={"param1": "value"})
        assert tc.func == mock_tool
        assert tc.args == {"param1": "value"}

    def test_positional_args(self):
        """Test creating with positional arguments (restored feature)."""
        tc = ExpectedToolCall(mock_tool, {"param1": "value"})
        assert tc.func == mock_tool
        assert tc.args == {"param1": "value"}

    def test_default_empty_args(self):
        """Test that args defaults to empty dict."""
        tc = ExpectedToolCall(func=mock_tool)
        assert tc.func == mock_tool
        assert tc.args == {}

    def test_func_is_required(self):
        """Test that func is required (no default)."""
        with pytest.raises(TypeError):
            ExpectedToolCall()  # type: ignore[call-arg]

    def test_func_with_positional_only(self):
        """Test creating with just func as positional."""
        tc = ExpectedToolCall(mock_tool)
        assert tc.func == mock_tool
        assert tc.args == {}


class TestExpectedMCPToolCall:
    """Tests for the ExpectedMCPToolCall dataclass (MCP tools)."""

    def test_keyword_args(self):
        """Test creating with keyword arguments."""
        tc = ExpectedMCPToolCall(tool_name="Calculator_Add", args={"a": 5, "b": 3})
        assert tc.tool_name == "Calculator_Add"
        assert tc.args == {"a": 5, "b": 3}

    def test_positional_args(self):
        """Test creating with positional arguments."""
        tc = ExpectedMCPToolCall("Calculator_Add", {"a": 5, "b": 3})
        assert tc.tool_name == "Calculator_Add"
        assert tc.args == {"a": 5, "b": 3}

    def test_default_empty_args(self):
        """Test that args defaults to empty dict."""
        tc = ExpectedMCPToolCall(tool_name="Calculator_Add")
        assert tc.tool_name == "Calculator_Add"
        assert tc.args == {}

    def test_tool_name_is_required(self):
        """Test that tool_name is required (no default)."""
        with pytest.raises(TypeError):
            ExpectedMCPToolCall()  # type: ignore[call-arg]

    def test_tool_name_with_positional_only(self):
        """Test creating with just tool_name as positional."""
        tc = ExpectedMCPToolCall("MyTool")
        assert tc.tool_name == "MyTool"
        assert tc.args == {}


class TestAnyExpectedToolCall:
    """Tests for mixed usage of ExpectedToolCall and ExpectedMCPToolCall."""

    def test_import_any_expected_tool_call(self):
        """Test that AnyExpectedToolCall can be imported."""
        from arcade_evals import AnyExpectedToolCall

        # Type alias should work with both types
        python_tc: AnyExpectedToolCall = ExpectedToolCall(func=mock_tool, args={"param1": "v"})
        mcp_tc: AnyExpectedToolCall = ExpectedMCPToolCall(tool_name="MyTool", args={"a": 1})
        assert python_tc is not None
        assert mcp_tc is not None

    def test_mixed_list(self):
        """Test that mixed lists work correctly."""
        from arcade_evals import AnyExpectedToolCall

        mixed_list: list[AnyExpectedToolCall] = [
            ExpectedToolCall(func=mock_tool, args={"param1": "value"}),
            ExpectedMCPToolCall(tool_name="RemoteTool", args={"x": 1}),
        ]
        assert len(mixed_list) == 2
        assert isinstance(mixed_list[0], ExpectedToolCall)
        assert isinstance(mixed_list[1], ExpectedMCPToolCall)

    def test_isinstance_checks(self):
        """Test that isinstance works correctly for type narrowing."""
        from arcade_evals import AnyExpectedToolCall

        tc: AnyExpectedToolCall = ExpectedToolCall(func=mock_tool, args={})

        if isinstance(tc, ExpectedToolCall):
            assert tc.func == mock_tool
        elif isinstance(tc, ExpectedMCPToolCall):
            pytest.fail("Should not reach here")


class TestExpectedToolCallConversion:
    """Tests for conversion of ExpectedToolCall types to NamedExpectedToolCall."""

    def test_add_case_with_expected_mcp_tool_call(self):
        """Test add_case correctly converts ExpectedMCPToolCall."""
        suite = EvalSuite(name="TestSuite", system_message="System message")

        suite.add_case(
            name="MCP Test",
            user_message="Test message",
            expected_tool_calls=[
                ExpectedMCPToolCall(tool_name="RemoteTool", args={"x": 1}),
            ],
        )

        assert len(suite.cases) == 1
        assert suite.cases[0].expected_tool_calls[0].name == "RemoteTool"
        assert suite.cases[0].expected_tool_calls[0].args == {"x": 1}

    def test_add_case_with_mixed_tool_calls(self):
        """Test add_case with both Python and MCP tools in same case."""
        from typing import Annotated

        from arcade_core import ToolCatalog

        @tool
        def annotated_tool(value: Annotated[str, "The input value"]) -> str:
            """A tool with proper annotations."""
            return value

        catalog = ToolCatalog()
        catalog.add_tool(annotated_tool, "Test")

        suite = EvalSuite(
            name="MixedSuite",
            system_message="System message",
            catalog=catalog,
        )

        suite.add_case(
            name="Mixed Test",
            user_message="Test message",
            expected_tool_calls=[
                ExpectedToolCall(func=annotated_tool, args={"value": "test"}),
                ExpectedMCPToolCall(tool_name="RemoteTool", args={"x": 1}),
            ],
        )

        assert len(suite.cases) == 1
        case = suite.cases[0]
        assert len(case.expected_tool_calls) == 2
        # First is Python tool - name should be toolkit_name + tool_name (PascalCase)
        assert case.expected_tool_calls[0].name == "Test_AnnotatedTool"
        # Second is MCP tool - name should be as-is
        assert case.expected_tool_calls[1].name == "RemoteTool"


class TestToolSelectionFailure:
    """Tests for tool selection failure scenarios and partial matching."""

    def test_tool_mismatch_with_fail_on_tool_selection_true(self):
        """Test that tool mismatch fails immediately when fail_on_tool_selection=True (default)."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
        ]
        actual_tool_calls = [
            ("ToolB", {"param": "value"}),  # Wrong tool
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(fail_on_tool_selection=True),
        )

        result = case.evaluate(actual_tool_calls)

        assert result.score == 0.0
        assert result.passed is False
        assert result.failure_reason is not None
        assert "Tool selection mismatch" in result.failure_reason

    def test_tool_mismatch_with_fail_on_tool_selection_false_partial_scoring(self):
        """Test that tool mismatch allows partial scoring when fail_on_tool_selection=False."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
        ]
        actual_tool_calls = [
            ("ToolB", {"param": "value"}),  # Wrong tool but correct param
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(
                fail_on_tool_selection=False,
                tool_selection_weight=1.0,
                fail_threshold=0.3,
            ),
        )

        result = case.evaluate(actual_tool_calls)

        # Tool selection: 0.0 (wrong tool)
        # Critic (param match): 1.0
        # Total: 1.0 / 2.0 = 0.5
        assert result.score == pytest.approx(0.5)
        assert result.failure_reason is None  # No early failure
        assert result.passed is True  # 0.5 >= 0.3 threshold


class TestToolCallQuantityFailure:
    """Tests for tool call quantity mismatch scenarios."""

    def test_more_tool_calls_than_expected_fails(self):
        """Test that calling the right tool more times than expected fails by default."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
        ]
        actual_tool_calls = [
            ("ToolA", {"param": "value"}),
            ("ToolA", {"param": "value2"}),  # Extra call
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(fail_on_tool_call_quantity=True),
        )

        result = case.evaluate(actual_tool_calls)

        assert result.score == 0.0
        assert result.passed is False
        assert result.failure_reason is not None
        assert "Expected 1 tool call(s), but got 2" in result.failure_reason

    def test_fewer_tool_calls_than_expected_fails(self):
        """Test that calling fewer tools than expected fails by default."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value1"}),
            NamedExpectedToolCall(name="ToolB", args={"param": "value2"}),
        ]
        actual_tool_calls = [
            ("ToolA", {"param": "value1"}),  # Only one call
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(fail_on_tool_call_quantity=True),
        )

        result = case.evaluate(actual_tool_calls)

        assert result.score == 0.0
        assert result.passed is False
        assert result.failure_reason is not None
        assert "Expected 2 tool call(s), but got 1" in result.failure_reason

    def test_quantity_mismatch_with_fail_on_quantity_false(self):
        """Test partial scoring when fail_on_tool_call_quantity=False."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
        ]
        actual_tool_calls = [
            ("ToolA", {"param": "value"}),
            ("ToolA", {"param": "extra"}),  # Extra call - should be ignored
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(
                fail_on_tool_call_quantity=False,
                fail_on_tool_selection=False,
                tool_selection_weight=1.0,
            ),
        )

        result = case.evaluate(actual_tool_calls)

        # Should not fail early - evaluation continues
        assert result.failure_reason is None
        # Score depends on matching logic (Hungarian algorithm matches best pairs)
        assert result.score > 0.0

    def test_right_tool_called_multiple_times_partial_score(self):
        """Test calling the right tool multiple times with quantity check disabled."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="Calculator_Add", args={"a": 5, "b": 3}),
        ]
        actual_tool_calls = [
            ("Calculator_Add", {"a": 5, "b": 3}),  # Correct call
            ("Calculator_Add", {"a": 10, "b": 20}),  # Extra call with different args
        ]

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[
                BinaryCritic(critic_field="a", weight=0.5),
                BinaryCritic(critic_field="b", weight=0.5),
            ],
            rubric=EvalRubric(
                fail_on_tool_call_quantity=False,
                fail_on_tool_selection=False,
                tool_selection_weight=1.0,
                fail_threshold=0.5,
            ),
        )

        result = case.evaluate(actual_tool_calls)

        # Should not fail immediately
        assert result.failure_reason is None
        # The Hungarian algorithm will match expected[0] with the best actual call
        # First actual call matches perfectly: tool(1.0) + a(0.5) + b(0.5) = 2.0
        assert result.score > 0.0

    def test_no_tool_calls_when_one_expected_fails(self):
        """Test that zero tool calls when some expected fails by default."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="ToolA", args={"param": "value"}),
        ]
        actual_tool_calls = []  # No calls

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[BinaryCritic(critic_field="param", weight=1.0)],
            rubric=EvalRubric(fail_on_tool_call_quantity=True),
        )

        result = case.evaluate(actual_tool_calls)

        assert result.score == 0.0
        assert result.passed is False
        assert "Expected 1 tool call(s), but got 0" in result.failure_reason

    def test_both_empty_passes(self):
        """Test that no expected and no actual tool calls results in pass."""
        expected_tool_calls = []
        actual_tool_calls = []

        case = EvalCase(
            name="TestCase",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[],
            rubric=EvalRubric(),
        )

        result = case.evaluate(actual_tool_calls)

        assert result.score == 1.0
        assert result.passed is True
        assert result.failure_reason is None
