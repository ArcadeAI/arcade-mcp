import pytest
from arcade_evals.eval import (
    DEFAULT_EVAL_SEED,
    PASS_RULE_MAJORITY,
    PASS_RULE_MEAN,
    EvalRubric,
    EvaluationResult,
    _aggregate_critic_stats,
    _resolve_pass_rule,
    _resolve_seed_spec,
)


def test_resolve_seed_spec_constant() -> None:
    mode, value = _resolve_seed_spec("constant")
    assert mode == "constant"
    assert value == DEFAULT_EVAL_SEED


def test_resolve_seed_spec_random() -> None:
    mode, value = _resolve_seed_spec("random")
    assert mode == "random"
    assert value is None


def test_resolve_seed_spec_integer() -> None:
    mode, value = _resolve_seed_spec(123)
    assert mode == "custom"
    assert value == 123


def test_resolve_seed_spec_numeric_string() -> None:
    mode, value = _resolve_seed_spec("456")
    assert mode == "custom"
    assert value == 456


def test_resolve_seed_spec_invalid() -> None:
    with pytest.raises(ValueError):
        _resolve_seed_spec("not-a-seed")


def test_pass_rule_mean_warning() -> None:
    rubric = EvalRubric(fail_threshold=0.6, warn_threshold=0.4)
    run_evals = [EvaluationResult(score=0.2), EvaluationResult(score=0.8)]
    passed, warning = _resolve_pass_rule(
        run_evals, mean_score=0.5, pass_rule=PASS_RULE_MEAN, rubric=rubric
    )
    assert passed is False
    assert warning is True


def test_pass_rule_majority_warning() -> None:
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


def test_aggregate_critic_stats() -> None:
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
