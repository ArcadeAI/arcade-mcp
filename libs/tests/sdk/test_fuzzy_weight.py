"""Tests for FuzzyWeight functionality."""

import pytest
from arcade_evals import BinaryCritic, EvalRubric, FuzzyWeight, NoneCritic, Weight
from arcade_evals.eval import EvalCase, NamedExpectedToolCall
from arcade_evals.weights import normalize_fuzzy_weights, resolve_weight

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestFuzzyWeightEnum:
    """Test FuzzyWeight enum values."""

    def test_fuzzy_weight_values(self) -> None:
        """Test FuzzyWeight enum has correct base values (linear scale 1-7)."""
        assert FuzzyWeight.MINIMAL.value == 1
        assert FuzzyWeight.VERY_LOW.value == 2
        assert FuzzyWeight.LOW.value == 3
        assert FuzzyWeight.MEDIUM.value == 4
        assert FuzzyWeight.HIGH.value == 5
        assert FuzzyWeight.VERY_HIGH.value == 6
        assert FuzzyWeight.CRITICAL.value == 7

    def test_fuzzy_weight_ordering(self) -> None:
        """Test FuzzyWeight values are properly ordered."""
        assert FuzzyWeight.MINIMAL.value < FuzzyWeight.VERY_LOW.value
        assert FuzzyWeight.VERY_LOW.value < FuzzyWeight.LOW.value
        assert FuzzyWeight.LOW.value < FuzzyWeight.MEDIUM.value
        assert FuzzyWeight.MEDIUM.value < FuzzyWeight.HIGH.value
        assert FuzzyWeight.HIGH.value < FuzzyWeight.VERY_HIGH.value
        assert FuzzyWeight.VERY_HIGH.value < FuzzyWeight.CRITICAL.value

    def test_fuzzy_weight_uniform_increment(self) -> None:
        """Test FuzzyWeight values have uniform increment of 1."""
        values = [fw.value for fw in FuzzyWeight]
        increments = [values[i + 1] - values[i] for i in range(len(values) - 1)]
        assert all(inc == 1 for inc in increments), f"Increments should all be 1: {increments}"

    def test_fuzzy_weight_is_enum(self) -> None:
        """Test that FuzzyWeight is a proper enum."""
        assert len(list(FuzzyWeight)) == 7
        assert FuzzyWeight.MEDIUM.name == "MEDIUM"


class TestNormalizeFuzzyWeights:
    """Test normalize_fuzzy_weights function."""

    def test_normalize_two_weights(self) -> None:
        """Test normalization with two weights."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.LOW),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # HIGH=5, LOW=3, total=8
        # HIGH: 5/8 = 0.625, LOW: 3/8 = 0.375
        assert normalized[0] == pytest.approx(5 / 8)
        assert normalized[1] == pytest.approx(3 / 8)
        assert sum(normalized) == pytest.approx(1.0)

    def test_normalize_equal_weights(self) -> None:
        """Test normalization with equal weights."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.MEDIUM),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.MEDIUM),
            BinaryCritic(critic_field="c", weight=FuzzyWeight.MEDIUM),
        ]
        normalized = normalize_fuzzy_weights(critics)

        assert all(w == pytest.approx(1 / 3) for w in normalized)
        assert sum(normalized) == pytest.approx(1.0)

    def test_normalize_mixed_weights(self) -> None:
        """Test normalization with mixed weight levels."""
        critics = [
            BinaryCritic(critic_field="owner", weight=FuzzyWeight.HIGH),
            BinaryCritic(critic_field="repo", weight=FuzzyWeight.HIGH),
            BinaryCritic(critic_field="number", weight=FuzzyWeight.MEDIUM),
            BinaryCritic(critic_field="state", weight=FuzzyWeight.LOW),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # HIGH=5, HIGH=5, MEDIUM=4, LOW=3, total=17
        assert normalized[0] == pytest.approx(5 / 17)
        assert normalized[1] == pytest.approx(5 / 17)
        assert normalized[2] == pytest.approx(4 / 17)
        assert normalized[3] == pytest.approx(3 / 17)
        assert sum(normalized) == pytest.approx(1.0)

    def test_normalize_empty_list(self) -> None:
        """Test normalization with empty list."""
        normalized = normalize_fuzzy_weights([])
        assert normalized == []

    def test_normalize_single_weight(self) -> None:
        """Test normalization with single critic."""
        critics = [BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH)]
        normalized = normalize_fuzzy_weights(critics)

        assert len(normalized) == 1
        assert normalized[0] == pytest.approx(1.0)

    def test_normalize_with_float_weights(self) -> None:
        """Test normalization works with float weights too."""
        critics = [
            BinaryCritic(critic_field="a", weight=3.0),  # Acts like HIGH
            BinaryCritic(critic_field="b", weight=1.0),  # Acts like LOW
        ]
        normalized = normalize_fuzzy_weights(critics)

        # 3.0 / 4.0 = 0.75, 1.0 / 4.0 = 0.25
        assert normalized[0] == pytest.approx(0.75)
        assert normalized[1] == pytest.approx(0.25)

    def test_small_weights_allowed(self) -> None:
        """Test that small weights are preserved after normalization."""
        # Create scenario where one weight would be relatively small
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.VERY_HIGH),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.VERY_HIGH),
            BinaryCritic(critic_field="c", weight=FuzzyWeight.VERY_HIGH),
            BinaryCritic(critic_field="d", weight=FuzzyWeight.VERY_HIGH),
            BinaryCritic(critic_field="e", weight=FuzzyWeight.VERY_LOW),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # VERY_LOW=2, VERY_HIGH=6*4=24, total=26
        # VERY_LOW: 2/26, VERY_HIGH: 6/26
        assert normalized[4] == pytest.approx(2 / 26)
        assert normalized[0] == pytest.approx(6 / 26)
        assert sum(normalized) == pytest.approx(1.0)

    def test_normalize_all_very_low(self) -> None:
        """Test normalization when all weights are VERY_LOW."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.VERY_LOW),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.VERY_LOW),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # Both equal, should split 50/50
        assert normalized[0] == pytest.approx(0.5)
        assert normalized[1] == pytest.approx(0.5)

    def test_normalize_all_very_high(self) -> None:
        """Test normalization when all weights are VERY_HIGH."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.VERY_HIGH),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.VERY_HIGH),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # Both equal, should split 50/50
        assert normalized[0] == pytest.approx(0.5)
        assert normalized[1] == pytest.approx(0.5)

    def test_normalize_extreme_weights(self) -> None:
        """Test normalization with MINIMAL and CRITICAL weights."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.CRITICAL),
            BinaryCritic(critic_field="b", weight=FuzzyWeight.MINIMAL),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # CRITICAL=7, MINIMAL=1, total=8
        assert normalized[0] == pytest.approx(7 / 8)  # 0.875
        assert normalized[1] == pytest.approx(1 / 8)  # 0.125
        assert sum(normalized) == pytest.approx(1.0)


class TestResolveWeight:
    """Test resolve_weight function."""

    def test_resolve_fuzzy_weight(self) -> None:
        """Test resolving FuzzyWeight to float."""
        assert resolve_weight(FuzzyWeight.MINIMAL) == 1
        assert resolve_weight(FuzzyWeight.VERY_LOW) == 2
        assert resolve_weight(FuzzyWeight.LOW) == 3
        assert resolve_weight(FuzzyWeight.MEDIUM) == 4
        assert resolve_weight(FuzzyWeight.HIGH) == 5
        assert resolve_weight(FuzzyWeight.VERY_HIGH) == 6
        assert resolve_weight(FuzzyWeight.CRITICAL) == 7

    def test_resolve_float_weight(self) -> None:
        """Test resolving float weight (passthrough)."""
        assert resolve_weight(0.5) == 0.5
        assert resolve_weight(1.0) == 1.0
        assert resolve_weight(0.0) == 0.0


class TestCriticWithFuzzyWeight:
    """Test Critic classes with FuzzyWeight."""

    def test_binary_critic_accepts_fuzzy_weight(self) -> None:
        """Test BinaryCritic accepts FuzzyWeight."""
        critic = BinaryCritic(critic_field="test", weight=FuzzyWeight.HIGH)
        assert critic.weight == FuzzyWeight.HIGH

    def test_critic_resolved_weight_property(self) -> None:
        """Test resolved_weight property returns float."""
        critic = BinaryCritic(critic_field="test", weight=FuzzyWeight.HIGH)
        assert critic.resolved_weight == 5

    def test_critic_still_accepts_float(self) -> None:
        """Test backwards compatibility with float weights."""
        critic = BinaryCritic(critic_field="test", weight=0.5)
        assert critic.weight == 0.5
        assert critic.resolved_weight == 0.5

    def test_none_critic_works_with_fuzzy_system(self) -> None:
        """Test NoneCritic still works alongside FuzzyWeight critics."""
        none_critic = NoneCritic(critic_field="optional")
        assert none_critic.weight == 0.0

    def test_all_fuzzy_weight_levels_on_critic(self) -> None:
        """Test all FuzzyWeight levels can be assigned to critics."""
        for fw in FuzzyWeight:
            critic = BinaryCritic(critic_field="test", weight=fw)
            assert critic.weight == fw
            assert critic.resolved_weight == fw.value


class TestEvalCaseWithFuzzyWeight:
    """Test EvalCase integration with FuzzyWeight."""

    def test_eval_case_normalizes_fuzzy_weights(self) -> None:
        """Test EvalCase normalizes FuzzyWeight critics."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=[
                BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
                BinaryCritic(critic_field="b", weight=FuzzyWeight.LOW),
            ],
            rubric=EvalRubric(),
        )

        # Weights should be normalized after __post_init__
        # HIGH=5, LOW=3, total=8
        assert case.critics[0].weight == pytest.approx(5 / 8)
        assert case.critics[1].weight == pytest.approx(3 / 8)

    def test_eval_case_mixed_fuzzy_and_float_normalizes(self) -> None:
        """Test EvalCase with mixed FuzzyWeight and float normalizes all."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=[
                BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
                BinaryCritic(critic_field="b", weight=3.0),  # Same value as LOW
            ],
            rubric=EvalRubric(),
        )

        # Mixed: if any FuzzyWeight present, all normalize
        # HIGH=5, float=3.0, total=8
        assert sum(c.weight for c in case.critics) == pytest.approx(1.0)
        assert case.critics[0].weight == pytest.approx(5 / 8)
        assert case.critics[1].weight == pytest.approx(3 / 8)

    def test_eval_case_float_only_legacy_validation(self) -> None:
        """Test EvalCase with only float weights uses legacy validation."""
        # This should work (valid legacy weights)
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=[
                BinaryCritic(critic_field="a", weight=0.5),
                BinaryCritic(critic_field="b", weight=0.5),
            ],
            rubric=EvalRubric(),
        )
        assert case.critics[0].weight == 0.5
        assert case.critics[1].weight == 0.5

    def test_eval_case_preserves_original_weight(self) -> None:
        """Test EvalCase preserves original FuzzyWeight for reference."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=[
                BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
            ],
            rubric=EvalRubric(),
        )

        # Original weight should be stored
        assert case.critics[0]._original_weight == FuzzyWeight.HIGH  # type: ignore[attr-defined]
        # Normalized weight should be 1.0 (only one critic)
        assert case.critics[0].weight == pytest.approx(1.0)

    def test_eval_case_with_none_critics_and_fuzzy(self) -> None:
        """Test EvalCase handles NoneCritic alongside FuzzyWeight critics."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={"a": 1, "b": 2, "c": 3})],
            critics=[
                BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
                BinaryCritic(critic_field="b", weight=FuzzyWeight.LOW),
                NoneCritic(critic_field="c"),  # Should be ignored in normalization
            ],
            rubric=EvalRubric(),
        )

        # NoneCritic should keep weight=0
        assert case.critics[2].weight == 0.0
        # Only non-None critics should be normalized to sum to 1.0
        non_none_sum = sum(c.weight for c in case.critics if not isinstance(c, NoneCritic))
        assert non_none_sum == pytest.approx(1.0)

    def test_eval_case_empty_critics(self) -> None:
        """Test EvalCase with no critics."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=None,
            rubric=EvalRubric(),
        )
        assert case.critics == []


class TestEvalCaseEvaluationWithFuzzyWeight:
    """Test that EvalCase.evaluate works correctly with normalized FuzzyWeight critics."""

    def test_evaluation_with_fuzzy_weights(self) -> None:
        """Test that evaluation scoring works correctly after FuzzyWeight normalization."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="TestTool", args={"owner": "arcade", "repo": "tools"}),
        ]
        actual_tool_calls = [
            ("TestTool", {"owner": "arcade", "repo": "wrong"}),  # owner matches, repo doesn't
        ]

        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[
                BinaryCritic(critic_field="owner", weight=FuzzyWeight.HIGH),
                BinaryCritic(critic_field="repo", weight=FuzzyWeight.LOW),
            ],
            rubric=EvalRubric(tool_selection_weight=0.0, fail_threshold=0.5),
        )

        result = case.evaluate(actual_tool_calls)

        # HIGH=5/8=0.625, LOW=3/8=0.375 after normalization
        # owner matches: 0.625 score
        # repo doesn't match: 0.0 score
        # Total score = 0.625 / (0.625 + 0.375) = 0.625
        assert result.score == pytest.approx(5 / 8)
        assert result.passed is True  # 0.625 >= 0.5

    def test_evaluation_all_match_fuzzy_weights(self) -> None:
        """Test evaluation where all critics match with FuzzyWeight."""
        expected_tool_calls = [
            NamedExpectedToolCall(name="TestTool", args={"a": "x", "b": "y"}),
        ]
        actual_tool_calls = [
            ("TestTool", {"a": "x", "b": "y"}),
        ]

        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=expected_tool_calls,
            critics=[
                BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
                BinaryCritic(critic_field="b", weight=FuzzyWeight.MEDIUM),
            ],
            rubric=EvalRubric(tool_selection_weight=0.0),
        )

        result = case.evaluate(actual_tool_calls)

        # All match, should be 1.0
        assert result.score == pytest.approx(1.0)
        assert result.passed is True


class TestWeightTypeAlias:
    """Test Weight type alias works correctly."""

    def test_weight_accepts_float(self) -> None:
        """Test Weight type accepts float."""
        w: Weight = 0.5
        assert w == 0.5

    def test_weight_accepts_fuzzy_weight(self) -> None:
        """Test Weight type accepts FuzzyWeight."""
        w: Weight = FuzzyWeight.HIGH
        assert w == FuzzyWeight.HIGH


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_existing_float_weights_work(self) -> None:
        """Test that existing float weight patterns continue to work."""
        case = EvalCase(
            name="Test",
            system_message="",
            user_message="",
            expected_tool_calls=[NamedExpectedToolCall(name="test", args={})],
            critics=[
                BinaryCritic(critic_field="owner", weight=0.2),
                BinaryCritic(critic_field="repo", weight=0.2),
                BinaryCritic(critic_field="number", weight=0.2),
                BinaryCritic(critic_field="entity_type", weight=0.2),
                BinaryCritic(critic_field="add_labels", weight=0.2),
            ],
            rubric=EvalRubric(),
        )

        # Float weights should remain unchanged
        for critic in case.critics:
            assert critic.weight == 0.2

        # Sum should still be 1.0
        assert sum(c.weight for c in case.critics) == pytest.approx(1.0)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_weight_handling(self) -> None:
        """Test that zero weight is allowed and handled correctly."""
        critics = [
            BinaryCritic(critic_field="a", weight=FuzzyWeight.HIGH),
            BinaryCritic(critic_field="b", weight=0),  # Zero weight
        ]
        normalized = normalize_fuzzy_weights(critics)

        # HIGH=5, zero=0, total=5
        assert normalized[0] == pytest.approx(1.0)
        assert normalized[1] == pytest.approx(0.0)
        assert sum(normalized) == pytest.approx(1.0)

    def test_all_zero_weights(self) -> None:
        """Test that all zero weights are handled (equal distribution)."""
        critics = [
            BinaryCritic(critic_field="a", weight=0),
            BinaryCritic(critic_field="b", weight=0),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # All zero -> return zeros (no scoring should occur)
        assert normalized[0] == 0.0
        assert normalized[1] == 0.0

    def test_large_float_weights(self) -> None:
        """Test that large float weights are handled correctly."""
        critics = [
            BinaryCritic(critic_field="a", weight=100.0),
            BinaryCritic(critic_field="b", weight=50.0),
        ]
        normalized = normalize_fuzzy_weights(critics)

        # 100/150, 50/150
        assert normalized[0] == pytest.approx(100 / 150)
        assert normalized[1] == pytest.approx(50 / 150)

    def test_negative_weight_raises_error(self) -> None:
        """Test that negative weights raise WeightError."""
        from arcade_evals.errors import WeightError

        with pytest.raises(WeightError):
            BinaryCritic(critic_field="test", weight=-1.0)

    def test_numeric_critic_with_fuzzy_weight(self) -> None:
        """Test NumericCritic works with FuzzyWeight."""
        from arcade_evals import NumericCritic

        critic = NumericCritic(
            critic_field="score",
            weight=FuzzyWeight.HIGH,
            value_range=(0, 100),
        )
        assert critic.weight == FuzzyWeight.HIGH
        assert critic.resolved_weight == 5

    def test_similarity_critic_with_fuzzy_weight(self) -> None:
        """Test SimilarityCritic works with FuzzyWeight."""
        from arcade_evals import SimilarityCritic

        critic = SimilarityCritic(
            critic_field="text",
            weight=FuzzyWeight.MEDIUM,
        )
        assert critic.weight == FuzzyWeight.MEDIUM
        assert critic.resolved_weight == 4

    def test_datetime_critic_with_fuzzy_weight(self) -> None:
        """Test DatetimeCritic works with FuzzyWeight."""
        from arcade_evals import DatetimeCritic

        critic = DatetimeCritic(
            critic_field="timestamp",
            weight=FuzzyWeight.CRITICAL,
        )
        assert critic.weight == FuzzyWeight.CRITICAL
        assert critic.resolved_weight == 7
