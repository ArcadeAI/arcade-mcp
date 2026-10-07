"""Grouped judgments exercise the real Arcade runner without changing it."""

from unittest.mock import MagicMock

import pytest
from arcade_evals import (
    CompletenessCritic,
    EvalSuite,
    ExpectedMCPToolCall,
    IntentionCritic,
    JudgeCriticGroup,
    JudgeVerdict,
)
from arcade_evals.errors import JudgeError

pytestmark = pytest.mark.evals


def make_group():
    backend = MagicMock()
    backend.judge.side_effect = lambda **request: {
        qid: JudgeVerdict(score, None, "fixture", "fixed-model")
        for qid, score in zip(request["questions"], (0.9, 0.5))
    }
    group = JudgeCriticGroup(
        critic_field="document",
        weight=0.5,
        backend=backend,
        context={"before": {"title": "Sales"}},
        critics=[
            CompletenessCritic("document", 3.0, instructions="Require three named columns"),
            IntentionCritic(
                "document", 1.0, intent="Readable table", context={"audience": "finance"}
            ),
        ],
    )
    return group, backend


def test_group_batches_questions_shares_payload_and_preserves_weights():
    group, backend = make_group()
    expected, actual = {"columns": 3}, {"columns": 3, "style": "bold"}
    result = group.evaluate(expected, actual)
    backend.judge.assert_called_once()
    request = backend.judge.call_args.kwargs
    assert len(request["questions"]) == 2
    assert request["state"]["expected"] == expected
    assert request["state"]["actual"] == actual
    assert request["state"]["context"] == group.context
    for qid, question in request["questions"].items():
        assert f"checks.{qid}" in question["instructions"]
        assert "expected" not in request["state"]["checks"][qid]
        assert "actual" not in request["state"]["checks"][qid]
    assert (
        "Require three named columns" in next(iter(request["questions"].values()))["instructions"]
    )
    assert result["score"] == pytest.approx((0.9 * 0.75 + 0.5 * 0.25) * 0.5)
    assert result["match"] is False
    assert [item["match"] for item in result["details"]] == [True, False]
    assert sum(item["score"] for item in result["details"]) == result["score"]
    assert result["confidence"] is None
    assert result["judge_calls"]["explicit"] == 1
    repeated = group.evaluate(expected, actual)
    assert repeated["cache_hit"] is True
    assert backend.judge.call_count == 1


def test_group_works_inside_existing_eval_suite():
    group, backend = make_group()
    suite = EvalSuite("batch", "Use the document tool")
    suite.add_case(
        name="edit",
        user_message="Create a readable three-column table",
        expected_tool_calls=[ExpectedMCPToolCall("edit", {"document": {"columns": 3}})],
        critics=[group],
    )
    result = suite.cases[0].evaluate([("edit", {"document": {"columns": 3, "style": "bold"}})])
    backend.judge.assert_called_once()  # Assignment and final scoring reuse the batch.
    detail = next(row for row in result.results if row["field"] == "document")
    assert len(detail["details"]) == 2
    assert detail["backend"] == "fixture"
    assert detail["model"] == "fixed-model"
    assert detail["cache_hit"] is True
    assert detail["score"] == pytest.approx(0.4)


def test_duplicate_critic_types_get_distinct_question_ids():
    group, backend = make_group()
    group.critics[1] = CompletenessCritic("document", 1.0, instructions="Require a totals row")
    group.evaluate("table", "table")
    questions = backend.judge.call_args.kwargs["questions"]
    assert len(questions) == 2
    assert len(set(questions)) == 2


def test_group_preserves_member_specific_value_preparation():
    class TrimmedReference(CompletenessCritic):
        def build_state(self, expected, actual):
            return {"expected": expected.strip(), "actual": actual}

    group, backend = make_group()
    group.critics[0] = TrimmedReference("document", 1.0)
    group.evaluate("  table  ", "table")
    state = backend.judge.call_args.kwargs["state"]
    assert state["expected"] == "  table  "
    assert state["checks"]["check_0"]["expected"] == "table"
    assert "expected" not in state["checks"]["check_1"]


def test_group_cache_tracks_context_and_member_guidance():
    group, backend = make_group()
    group.evaluate("table", "table")
    group.context["before"]["title"] = "Revenue"
    group.evaluate("table", "table")
    group.critics[0].instructions = "Require an accessible header"
    group.evaluate("table", "table")
    assert backend.judge.call_count == 3
    group.clear_cache()
    group.evaluate("table", "table")
    assert backend.judge.call_count == 4


@pytest.mark.parametrize("problem", ["unavailable", "missing", "low_confidence", "invalid"])
def test_batch_failure_never_becomes_a_lexical_score(problem):
    group, backend = make_group()
    backend.judge.side_effect = None
    backend.judge.return_value = {
        "check_0": JudgeVerdict(0.9, None, "fixture"),
        "check_1": JudgeVerdict(0.9, None, "fixture"),
    }
    if problem == "unavailable":
        backend.judge.side_effect = JudgeError("synthetic-private-detail")
    elif problem == "missing":
        backend.judge.return_value.pop("check_1")
    elif problem == "low_confidence":
        backend.judge.return_value["check_1"].confidence = 0.1
    else:
        backend.judge.return_value["check_1"].score = float("nan")
    result = group.evaluate("identical", "identical")
    assert result["status"] == "unavailable"
    assert result["match"] is False
    assert result["score"] == 0.0
    assert result["backend"] == "unavailable"
    assert "synthetic-private-detail" not in repr(result)


def test_unavailable_group_keeps_its_weight_in_arcade_aggregation():
    group, backend = make_group()
    backend.judge.side_effect = JudgeError("offline")
    suite = EvalSuite("batch", "Use edit")
    suite.add_case(
        name="missing-judge",
        user_message="Edit the document",
        expected_tool_calls=[ExpectedMCPToolCall("edit", {"document": "table"})],
        critics=[group],
    )
    result = suite.cases[0].evaluate([("edit", {"document": "table"})])
    tool_weight = suite.rubric.tool_selection_weight
    assert result.score == pytest.approx(tool_weight / (tool_weight + group.resolved_weight))
    assert result.passed is False
    detail = next(row for row in result.results if row["field"] == "document")
    assert detail["status"] == "unavailable"


def test_low_confidence_batch_is_reused_by_assignment_and_final_scoring():
    group, backend = make_group()
    # Scores from the live flawed-document check; uncertainty is not an outage.
    backend.judge.side_effect = None
    backend.judge.return_value = {
        "check_0": JudgeVerdict(0.24, 0.28, "jev", "jev-1.13.0"),
        "check_1": JudgeVerdict(0.05, None, "jev", "jev-1.13.0"),
    }
    suite = EvalSuite("batch", "Use edit")
    suite.add_case(
        name="uncertain-judge",
        user_message="Create the table",
        expected_tool_calls=[ExpectedMCPToolCall("edit", {"document": "full table"})],
        critics=[group],
    )
    result = suite.cases[0].evaluate([("edit", {"document": "incomplete table"})])
    backend.judge.assert_called_once()
    detail = next(row for row in result.results if row["field"] == "document")
    assert result.passed is False
    assert detail["status"] == "unavailable"
    assert detail["score"] == 0.0
    assert detail["cache_hit"] is True
    assert detail["judge_calls"]["explicit"] == 1

    # Confidence policy is re-applied to cached evidence, not bypassed by it.
    group.critics[0].min_confidence = 0.2
    accepted = group.evaluate("full table", "incomplete table")
    assert accepted["status"] == "ok"
    assert accepted["match"] is False
    assert accepted["cache_hit"] is True
    backend.judge.assert_called_once()
    group.critics[0].min_confidence = 0.5
    assert group.evaluate("full table", "incomplete table")["status"] == "unavailable"
    backend.judge.assert_called_once()
    group.clear_cache()
    group.evaluate("full table", "incomplete table")
    assert backend.judge.call_count == 2


@pytest.mark.parametrize("problem", ["unavailable", "missing", "invalid"])
def test_failed_batch_is_not_cached(problem):
    group, backend = make_group()
    backend.judge.side_effect = None
    backend.judge.return_value = {
        "check_0": JudgeVerdict(0.9, None, "fixture"),
        "check_1": JudgeVerdict(0.9, None, "fixture"),
    }
    if problem == "unavailable":
        backend.judge.side_effect = JudgeError("offline")
    elif problem == "missing":
        backend.judge.return_value.pop("check_1")
    else:
        backend.judge.return_value["check_1"].score = float("nan")
    for _ in range(2):
        result = group.evaluate("table", "table")
        assert result["status"] == "unavailable"
        assert result["cache_hit"] is False
    assert backend.judge.call_count == 2


@pytest.mark.parametrize(
    "critics",
    [
        [],
        [CompletenessCritic("other", 1.0)],
        [CompletenessCritic("document", 0.0)],
        [CompletenessCritic("document", float("nan"))],
    ],
)
def test_group_rejects_invalid_members(critics):
    with pytest.raises(ValueError):
        JudgeCriticGroup("document", 1.0, critics=critics, backend=MagicMock())
