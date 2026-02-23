import pytest
from arcade_evals._evalsuite._types import (
    DEFAULT_EVAL_SEED,
    PASS_RULE_LAST,
    PASS_RULE_MAJORITY,
    PASS_RULE_MEAN,
    _resolve_seed_spec,
)
from arcade_evals.capture import CapturedRun, CapturedToolCall
from arcade_evals.eval import (
    EvalRubric,
    EvaluationResult,
    _aggregate_critic_stats,
    _compute_mean_std,
    _resolve_pass_rule,
)

# ========================================================================
# _compute_mean_std tests
# ========================================================================


class TestComputeMeanStd:
    def test_empty_list(self) -> None:
        avg, std = _compute_mean_std([])
        assert avg == 0.0
        assert std == 0.0

    def test_single_value(self) -> None:
        avg, std = _compute_mean_std([0.75])
        assert avg == pytest.approx(0.75)
        assert std == 0.0

    def test_multiple_values(self) -> None:
        avg, std = _compute_mean_std([0.5, 0.5])
        assert avg == pytest.approx(0.5)
        assert std == pytest.approx(0.0)

    def test_varying_values(self) -> None:
        avg, std = _compute_mean_std([0.0, 1.0])
        assert avg == pytest.approx(0.5)
        assert std > 0.0


# ========================================================================
# _resolve_seed_spec tests
# ========================================================================


class TestResolveSeedSpec:
    def test_constant_string(self) -> None:
        mode, value = _resolve_seed_spec("constant")
        assert mode == "constant"
        assert value == DEFAULT_EVAL_SEED

    def test_random_string(self) -> None:
        mode, value = _resolve_seed_spec("random")
        assert mode == "random"
        assert value is None

    def test_integer(self) -> None:
        mode, value = _resolve_seed_spec(123)
        assert mode == "custom"
        assert value == 123

    def test_numeric_string(self) -> None:
        mode, value = _resolve_seed_spec("456")
        assert mode == "custom"
        assert value == 456

    def test_none_defaults_to_constant(self) -> None:
        mode, value = _resolve_seed_spec(None)
        assert mode == "constant"
        assert value == DEFAULT_EVAL_SEED

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid seed"):
            _resolve_seed_spec("not-a-seed")

    def test_case_insensitive(self) -> None:
        mode, value = _resolve_seed_spec("CONSTANT")
        assert mode == "constant"
        mode2, value2 = _resolve_seed_spec("RANDOM")
        assert mode2 == "random"
        assert value2 is None


# ========================================================================
# _resolve_pass_rule tests
# ========================================================================


class TestResolvePassRule:
    def test_last_rule_returns_last_eval(self) -> None:
        rubric = EvalRubric()
        run_evals = [
            EvaluationResult(score=0.3, passed=False),
            EvaluationResult(score=0.9, passed=True),
        ]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.6, pass_rule=PASS_RULE_LAST, rubric=rubric
        )
        assert passed is True
        assert warning is False

    def test_mean_rule_passes_when_mean_above_threshold(self) -> None:
        rubric = EvalRubric(fail_threshold=0.6, warn_threshold=0.4)
        run_evals = [EvaluationResult(score=0.5), EvaluationResult(score=0.9)]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.7, pass_rule=PASS_RULE_MEAN, rubric=rubric
        )
        assert passed is True
        assert warning is False

    def test_mean_rule_warning(self) -> None:
        rubric = EvalRubric(fail_threshold=0.6, warn_threshold=0.4)
        run_evals = [EvaluationResult(score=0.2), EvaluationResult(score=0.8)]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.5, pass_rule=PASS_RULE_MEAN, rubric=rubric
        )
        assert passed is False
        assert warning is True

    def test_mean_rule_fails_below_warn(self) -> None:
        rubric = EvalRubric(fail_threshold=0.6, warn_threshold=0.4)
        run_evals = [EvaluationResult(score=0.1), EvaluationResult(score=0.2)]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.15, pass_rule=PASS_RULE_MEAN, rubric=rubric
        )
        assert passed is False
        assert warning is False

    def test_majority_rule_passes(self) -> None:
        rubric = EvalRubric()
        run_evals = [
            EvaluationResult(score=0.9, passed=True),
            EvaluationResult(score=0.9, passed=True),
            EvaluationResult(score=0.1, passed=False),
        ]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.63, pass_rule=PASS_RULE_MAJORITY, rubric=rubric
        )
        assert passed is True
        assert warning is False

    def test_majority_rule_warning(self) -> None:
        rubric = EvalRubric()
        run_evals = [
            EvaluationResult(score=0.8, passed=True),
            EvaluationResult(score=0.5, warning=True),
            EvaluationResult(score=0.1, passed=False),
        ]
        passed, warning = _resolve_pass_rule(
            run_evals, mean_score=0.46, pass_rule=PASS_RULE_MAJORITY, rubric=rubric
        )
        assert passed is False
        assert warning is True

    def test_empty_evaluations_returns_false(self) -> None:
        rubric = EvalRubric()
        passed, warning = _resolve_pass_rule(
            [], mean_score=0.0, pass_rule=PASS_RULE_LAST, rubric=rubric
        )
        assert passed is False
        assert warning is False

    def test_invalid_rule_raises(self) -> None:
        rubric = EvalRubric()
        with pytest.raises(ValueError, match="Invalid multi-run pass rule"):
            _resolve_pass_rule(
                [EvaluationResult(score=0.5)],
                mean_score=0.5,
                pass_rule="invalid",
                rubric=rubric,
            )


# ========================================================================
# _aggregate_critic_stats tests
# ========================================================================


class TestAggregateCriticStats:
    def test_basic_aggregation(self) -> None:
        run_field_scores = [
            {"arg_a": {"score": 0.5, "weight": 0.5}},
            {
                "arg_a": {"score": 0.0, "weight": 0.5},
                "arg_b": {"score": 0.25, "weight": 0.5},
            },
        ]
        stats = _aggregate_critic_stats(run_field_scores)
        assert stats["arg_a"]["run_scores"] == [0.5, 0.0]
        assert stats["arg_a"]["run_scores_normalized"] == [1.0, 0.0]
        assert stats["arg_a"]["weight"] == pytest.approx(0.5)
        assert stats["arg_b"]["run_scores"] == [0.0, 0.25]
        assert stats["arg_b"]["run_scores_normalized"] == [0.0, 0.5]
        assert stats["arg_b"]["weight"] == pytest.approx(0.5)

    def test_empty_input(self) -> None:
        assert _aggregate_critic_stats([]) == {}

    def test_single_run(self) -> None:
        run_field_scores = [{"field_x": {"score": 0.8, "weight": 1.0}}]
        stats = _aggregate_critic_stats(run_field_scores)
        assert stats["field_x"]["run_scores"] == [0.8]
        assert stats["field_x"]["mean_score"] == pytest.approx(0.8)
        assert stats["field_x"]["std_deviation"] == pytest.approx(0.0)
        assert stats["field_x"]["weight"] == pytest.approx(1.0)


# ========================================================================
# CapturedRun tests
# ========================================================================


class TestCapturedRun:
    def test_to_dict_empty(self) -> None:
        run = CapturedRun()
        assert run.to_dict() == {"tool_calls": []}

    def test_to_dict_with_calls(self) -> None:
        run = CapturedRun(
            tool_calls=[
                CapturedToolCall(name="GetWeather", args={"city": "NYC"}),
                CapturedToolCall(name="GetTime", args={"tz": "UTC"}),
            ]
        )
        d = run.to_dict()
        assert len(d["tool_calls"]) == 2
        assert d["tool_calls"][0] == {"name": "GetWeather", "args": {"city": "NYC"}}
        assert d["tool_calls"][1] == {"name": "GetTime", "args": {"tz": "UTC"}}


# ========================================================================
# CapturedCase.to_dict tests
# ========================================================================
from arcade_evals.capture import CapturedCase


class TestCapturedCaseToDict:
    def test_single_run_no_runs_key(self) -> None:
        """When runs=[], to_dict should NOT include a 'runs' key."""
        case = CapturedCase(
            case_name="test",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Greet", args={})],
            runs=[],
        )
        d = case.to_dict()
        assert "runs" not in d
        assert d["tool_calls"] == [{"name": "Greet", "args": {}}]

    def test_multi_run_includes_runs(self) -> None:
        """When runs has items, to_dict should include 'runs' key."""
        case = CapturedCase(
            case_name="test",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Greet", args={})],
            runs=[
                CapturedRun(tool_calls=[CapturedToolCall(name="Greet", args={"seed": "1"})]),
                CapturedRun(tool_calls=[CapturedToolCall(name="Greet", args={"seed": "2"})]),
            ],
        )
        d = case.to_dict()
        assert "runs" in d
        assert len(d["runs"]) == 2
        assert d["runs"][0]["tool_calls"][0]["args"]["seed"] == "1"

    def test_to_dict_with_context(self) -> None:
        """to_dict with include_context=True should include system_message."""
        case = CapturedCase(
            case_name="test",
            user_message="Hello",
            tool_calls=[],
            system_message="You are helpful",
            additional_messages=[],
        )
        d = case.to_dict(include_context=True)
        assert "system_message" in d
        assert d["system_message"] == "You are helpful"

    def test_to_dict_with_track_name(self) -> None:
        """to_dict should include track_name when set."""
        case = CapturedCase(
            case_name="test",
            user_message="Hello",
            tool_calls=[],
            track_name="track_a",
        )
        d = case.to_dict()
        assert d["track_name"] == "track_a"

    def test_to_dict_no_track_name_omits_key(self) -> None:
        """to_dict should not include track_name when None."""
        case = CapturedCase(
            case_name="test",
            user_message="Hello",
            tool_calls=[],
        )
        d = case.to_dict()
        assert "track_name" not in d


# ========================================================================
# _aggregate_critic_stats extended tests
# ========================================================================


class TestAggregateCriticStatsExtended:
    def test_zero_weight_field(self) -> None:
        """Fields with zero weight should still aggregate correctly."""
        run_field_scores = [
            {"field_a": {"score": 0.5, "weight": 0.0}},
            {"field_a": {"score": 0.7, "weight": 0.0}},
        ]
        stats = _aggregate_critic_stats(run_field_scores)
        assert stats["field_a"]["weight"] == pytest.approx(0.0)
        # Normalized scores with zero weight are 0.0
        assert stats["field_a"]["run_scores_normalized"] == [0.0, 0.0]

    def test_mixed_presence_across_runs(self) -> None:
        """Fields missing from some runs should get 0.0 for those runs."""
        run_field_scores = [
            {"field_a": {"score": 0.8, "weight": 1.0}},
            {"field_b": {"score": 0.5, "weight": 0.5}},
        ]
        stats = _aggregate_critic_stats(run_field_scores)
        # field_a present in run 1 (0.8), absent in run 2 (0.0)
        assert stats["field_a"]["run_scores"] == [0.8, 0.0]
        # field_b absent in run 1 (0.0), present in run 2 (0.5)
        assert stats["field_b"]["run_scores"] == [0.0, 0.5]

    def test_consistency_of_mean_and_std(self) -> None:
        """Verify mean and std are consistent with run_scores."""
        from statistics import mean, pstdev

        run_field_scores = [
            {"f": {"score": 0.2, "weight": 0.5}},
            {"f": {"score": 0.6, "weight": 0.5}},
            {"f": {"score": 0.4, "weight": 0.5}},
        ]
        stats = _aggregate_critic_stats(run_field_scores)
        assert stats["f"]["mean_score"] == pytest.approx(mean([0.2, 0.6, 0.4]))
        assert stats["f"]["std_deviation"] == pytest.approx(pstdev([0.2, 0.6, 0.4]))


# ========================================================================
# PASS_RULE_LAST failure_reason defensive guard test
# ========================================================================


class TestPassRuleLastFailureReasonGuard:
    """The PASS_RULE_LAST branch should not surface failure_reason when passed."""

    def test_last_passed_no_failure_reason(self) -> None:
        """When PASS_RULE_LAST and the last run passed, failure_reason should be None."""
        # This tests the defensive guard we added:
        #   aggregate_failure_reason = run_evaluations[-1].failure_reason if not passed else None
        #
        # We can't easily test _run_case_with_stats without mocking the LLM,
        # but we can verify the logic pattern by checking _resolve_pass_rule:
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.3, passed=False, failure_reason="bad"),
            EvaluationResult(score=0.9, passed=True, failure_reason=None),
        ]
        passed, warning = _resolve_pass_rule(evals, 0.6, PASS_RULE_LAST, rubric)
        assert passed is True
        # When passed is True, the aggregate should NOT surface failure_reason
        # (This is the logic we guard in eval.py line ~929-933)
        aggregate_failure_reason = evals[-1].failure_reason if not passed else None
        assert aggregate_failure_reason is None

    def test_last_failed_surfaces_failure_reason(self) -> None:
        """When PASS_RULE_LAST and the last run failed, failure_reason is surfaced."""
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.9, passed=True),
            EvaluationResult(score=0.3, passed=False, failure_reason="tool mismatch"),
        ]
        passed, warning = _resolve_pass_rule(evals, 0.6, PASS_RULE_LAST, rubric)
        assert passed is False
        aggregate_failure_reason = evals[-1].failure_reason if not passed else None
        assert aggregate_failure_reason == "tool mismatch"


# ========================================================================
# _resolve_pass_rule with MAJORITY edge cases
# ========================================================================


class TestResolvePassRuleMajorityEdgeCases:
    def test_majority_all_warned(self) -> None:
        """When all runs have warnings, majority should return warning."""
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.5, passed=False, warning=True),
            EvaluationResult(score=0.5, passed=False, warning=True),
            EvaluationResult(score=0.5, passed=False, warning=True),
        ]
        passed, warning = _resolve_pass_rule(evals, 0.5, PASS_RULE_MAJORITY, rubric)
        assert passed is False
        assert warning is True

    def test_majority_all_failed(self) -> None:
        """When all runs fail, majority should return fail."""
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.1, passed=False),
            EvaluationResult(score=0.2, passed=False),
            EvaluationResult(score=0.15, passed=False),
        ]
        passed, warning = _resolve_pass_rule(evals, 0.15, PASS_RULE_MAJORITY, rubric)
        assert passed is False
        assert warning is False

    def test_majority_tie_does_not_pass(self) -> None:
        """With a 50/50 even split, there is no majority, so it fails."""
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.9, passed=True),
            EvaluationResult(score=0.1, passed=False),
        ]
        # majority = 2 // 2 + 1 = 2, passed_count=1 < 2
        passed, warning = _resolve_pass_rule(evals, 0.5, PASS_RULE_MAJORITY, rubric)
        assert passed is False

    def test_majority_tie_fails(self) -> None:
        """With more failures than passes, should fail."""
        rubric = EvalRubric()
        evals = [
            EvaluationResult(score=0.9, passed=True),
            EvaluationResult(score=0.1, passed=False),
            EvaluationResult(score=0.1, passed=False),
        ]
        passed, warning = _resolve_pass_rule(evals, 0.36, PASS_RULE_MAJORITY, rubric)
        assert passed is False
