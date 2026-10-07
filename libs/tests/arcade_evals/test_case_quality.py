"""Quality-gate behavior, independent of any live judge's semantic accuracy."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from arcade_evals import (
    CaseQualityGrader,
    CompletenessCritic,
    JevBackend,
    JudgeCriticGroup,
    LLMFallbackBackend,
    NamedExpectedToolCall,
)
from arcade_evals.case_quality import build_quality_questions
from arcade_evals.errors import JudgeError
from arcade_evals.eval import EvalCase
from arcade_evals.judge import JudgeVerdict

pytestmark = pytest.mark.evals


def make_case(user_message="Summarize the customer issue", **kwargs):
    return EvalCase(
        name="example",
        system_message="Use the support tools",
        user_message=user_message,
        expected_tool_calls=[NamedExpectedToolCall("support", {"id": "7f3a9c2e4b1d"})],
        **kwargs,
    )


def judgments(**overrides):
    result = {
        "context": JudgeVerdict(0.9, None, "custom", "fixed-model"),
        "hint": JudgeVerdict(0.1, None, "custom", "fixed-model"),
        "ambiguity": JudgeVerdict(0.1, None, "custom", "fixed-model"),
        "human": JudgeVerdict(0.9, None, "custom", "fixed-model"),
        "complexity": JudgeVerdict(None, None, "custom", "fixed-model", label="simple"),
    }
    for key, value in overrides.items():
        result[key] = (
            JudgeVerdict(None, None, "custom", label=value)
            if key == "complexity"
            else JudgeVerdict(value, None, "custom")
        )
    return result


def grader(**overrides):
    backend = MagicMock()
    backend.judge.return_value = judgments(**overrides)
    return CaseQualityGrader(backend=backend)


def test_grades_existing_case_in_one_call_without_changing_it():
    case = make_case(additional_messages=[{"role": "user", "content": "Ticket details"}])
    tools = [{"name": "support", "description": "Look up a support ticket"}]
    gate = grader()
    report = gate.grade(case, tools=tools)
    assert report.passed is True
    assert report.reasons == []
    assert report.verdicts["complexity"].label == "simple"
    assert report.verdicts["context"].model == "fixed-model"
    gate.backend.judge.assert_called_once()
    request = gate.backend.judge.call_args.kwargs
    assert set(request["questions"]) == {"context", "hint", "ambiguity", "human", "complexity"}
    assert request["state"]["additional_messages"] == case.additional_messages
    assert request["state"]["tools"] == tools
    assert request["state"]["expected"] == [{"name": "support", "args": {"id": "7f3a9c2e4b1d"}}]
    assert case.critics == []
    assert case.additional_messages == [{"role": "user", "content": "Ticket details"}]


def test_quality_grader_sees_grouped_critic_requirements_without_backend_secrets():
    member = CompletenessCritic("id", 1.0, instructions="Accept equivalent ticket identifiers")
    critic_backend = MagicMock()
    critic_backend.api_key = "synthetic-private-detail"
    group = JudgeCriticGroup(
        "id",
        1.0,
        critics=[member],
        backend=critic_backend,
        instructions="Preserve the referenced customer",
        context={"source": "ticket snapshot"},
    )
    gate = grader()
    gate.grade(make_case(critics=[group]))
    state = gate.backend.judge.call_args.kwargs["state"]
    spec = state["critics"][0]
    assert spec["instructions"] == group.instructions
    assert spec["context"] == group.context
    assert spec["checks"][0]["instructions"] == member.instructions
    assert spec["checks"][0]["match_threshold"] == member.match_threshold
    assert "synthetic-private-detail" not in json.dumps(state)


@pytest.mark.parametrize(
    "dimension,score",
    [
        ("context", 0.2),
        ("hint", 0.9),
        ("ambiguity", 0.9),
        ("human", 0.2),
    ],
)
def test_each_failed_dimension_is_reported(dimension, score):
    report = grader(**{dimension: score}).grade(make_case())
    assert report.passed is False
    assert len(report.reasons) == 1
    assert report.reasons[0].startswith(dimension + ":")


def test_reports_all_failed_dimensions():
    report = grader(context=0.1, hint=0.9, ambiguity=0.9, human=0.1).grade(make_case())
    assert report.passed is False
    assert len(report.reasons) == 4


def test_exact_thresholds_pass():
    gate = grader(context=0.6, hint=0.6, ambiguity=0.4, human=0.5)
    assert gate.grade(make_case()).passed is True


def test_default_hint_threshold_allows_contextual_facts():
    case = make_case(
        additional_messages=[{"role": "assistant", "content": "Ticket INC-742 is open."}]
    )
    assert grader(hint=0.5).grade(case).passed is True


def test_default_ambiguity_threshold_rejects_midrange_competing_options():
    assert grader(ambiguity=0.45).grade(make_case()).passed is False


def test_complexity_is_descriptive_unless_trivial_policy_is_enabled():
    gate = grader(complexity="trivial")
    assert gate.grade(make_case()).passed is True
    gate.fail_on_trivial = True
    report = gate.grade(make_case())
    assert report.passed is False
    assert report.reasons == ["complexity: trivial cases are excluded by policy"]


def test_legitimate_ids_and_literal_arguments_are_not_automatic_failures():
    report = grader().grade(make_case("Check ticket 7f3a9c2e4b1d"))
    assert report.passed is True


def test_hint_rubric_distinguishes_context_facts_from_benchmark_answers():
    instructions = build_quality_questions()["hint"]["instructions"]
    assert "additional messages" in instructions
    assert "benchmark" in instructions
    assert "independently" in instructions
    assert "reference labels" in instructions


@pytest.mark.parametrize(
    "problem", ["missing", "wrong_score", "wrong_label", "not_verdict", "none"]
)
def test_incomplete_or_invalid_judgments_raise_instead_of_fabricating_a_grade(problem):
    gate = grader()
    answers = gate.backend.judge.return_value
    if problem == "missing":
        answers.pop("context")
    elif problem == "wrong_score":
        answers["context"].score = float("nan")
    elif problem == "wrong_label":
        answers["complexity"].label = "unknown"
    elif problem == "not_verdict":
        answers["human"] = {"score": 0.9}
    else:
        gate.backend.judge.return_value = None
    with pytest.raises(JudgeError):
        gate.grade(make_case())


def test_backend_unavailable_raises_without_leaking_details():
    gate = grader()
    gate.backend.judge.side_effect = JudgeError("synthetic-private-provider-detail")
    with pytest.raises(JudgeError, match="unavailable") as error:
        gate.grade(make_case())
    assert "synthetic-private-provider-detail" not in str(error.value)
    assert error.value.__suppress_context__


def test_quality_rubrics_identify_model_visible_messages_and_structured_output_labels():
    questions = build_quality_questions()
    assert "additional_messages" in questions["context"]["instructions"]
    assert "structured document or spreadsheet" in questions["ambiguity"]["instructions"]
    assert "labels" in questions["ambiguity"]["instructions"]


@pytest.mark.parametrize("setting", ["min_context", "max_hint", "max_ambiguity", "min_human"])
@pytest.mark.parametrize("value", [-0.1, 1.1, True, float("nan")])
def test_invalid_quality_thresholds_are_rejected(setting, value):
    with pytest.raises(ValueError):
        CaseQualityGrader(backend=MagicMock(), **{setting: value})


@pytest.mark.parametrize("provider", ["jev", "llm"])
def test_full_quality_gate_with_both_real_adapters(provider):
    if provider == "jev":
        payload = {
            "model": "fixture-model",
            "answers": {
                "context": {"type": "score", "score": 1.8},
                "hint": {"type": "noul", "noul": 0.1},
                "ambiguity": {"type": "score", "score": 0.2},
                "human": {"type": "noul", "noul": 0.9},
                "complexity": {"type": "choice", "choice": "simple"},
            },
        }
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode()
        backend = JevBackend(api_key="test-key")
        with patch("urllib.request.urlopen", return_value=response) as transport:
            report = CaseQualityGrader(backend=backend).grade(make_case())
        assert transport.call_count == 1
    else:
        client = MagicMock()
        payload = {
            key: {"score": score}
            for key, score in (("context", 0.9), ("hint", 0.1), ("ambiguity", 0.1), ("human", 0.9))
        }
        payload["complexity"] = {"choice": "simple"}
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )
        backend = LLMFallbackBackend(client=client, model="fixture-model")
        report = CaseQualityGrader(backend=backend).grade(make_case())
        assert client.chat.completions.create.call_count == 1
    assert report.passed is True
    assert report.verdicts["context"].score == pytest.approx(0.9)
    assert report.verdicts["complexity"].label == "simple"
    assert report.verdicts["complexity"].score is None
    assert all(verdict.model == "fixture-model" for verdict in report.verdicts.values())
