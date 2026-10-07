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

EXPECTED_ID = "7f3a9c2e4b1d"
QUESTION_IDS = {"contextScore", "hintNoul", "ambiguityScore", "humanNoul", "complexityChoice"}


def make_case(user_message="Summarize the customer issue", **kwargs):
    return EvalCase(
        name="example",
        system_message="Use the support tools",
        user_message=user_message,
        expected_tool_calls=[NamedExpectedToolCall("support", {"id": EXPECTED_ID})],
        **kwargs,
    )


def judgments(**overrides):
    result = {
        "contextScore": JudgeVerdict(0.9, None, "custom", "fixed-model"),
        "hintNoul": JudgeVerdict(0.1, None, "custom", "fixed-model"),
        "ambiguityScore": JudgeVerdict(0.1, None, "custom", "fixed-model"),
        "humanNoul": JudgeVerdict(0.9, None, "custom", "fixed-model"),
        "complexityChoice": JudgeVerdict(None, None, "custom", "fixed-model", label="simple"),
    }
    for key, value in overrides.items():
        result[key] = (
            JudgeVerdict(None, None, "custom", label=value)
            if key == "complexityChoice"
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
    assert report.status == "passed"
    assert report.reasons == []
    assert report.verdicts["complexityChoice"].label == "simple"
    assert report.verdicts["contextScore"].model == "fixed-model"
    gate.backend.judge.assert_called_once()
    request = gate.backend.judge.call_args.kwargs
    assert set(request["questions"]) == QUESTION_IDS
    state = request["state"]
    assert state["model_visible"]["additional_messages"] == case.additional_messages
    assert state["tools"] == tools
    assert state["reference_labels"]["expected"] == [
        {"name": "support", "args": {"id": EXPECTED_ID}}
    ]
    assert not case.critics
    assert case.additional_messages == [{"role": "user", "content": "Ticket details"}]


def test_expected_labels_never_enter_model_visible_context():
    gate = grader()
    gate.grade(make_case())
    request = gate.backend.judge.call_args.kwargs
    assert EXPECTED_ID not in json.dumps(request["state"]["model_visible"])
    assert EXPECTED_ID not in json.dumps(request["questions"])
    assert EXPECTED_ID in json.dumps(request["state"]["reference_labels"])


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
        ("contextScore", 0.2),
        ("hintNoul", 0.9),
        ("ambiguityScore", 0.9),
        ("humanNoul", 0.2),
    ],
)
def test_each_failed_dimension_is_reported(dimension, score):
    report = grader(**{dimension: score}).grade(make_case())
    assert report.passed is False
    assert report.status == "failed"
    assert len(report.reasons) == 1
    assert report.reasons[0].startswith(dimension + ":")


def test_reports_all_failed_dimensions():
    report = grader(contextScore=0.1, hintNoul=0.9, ambiguityScore=0.9, humanNoul=0.1).grade(
        make_case()
    )
    assert report.passed is False
    assert len(report.reasons) == 4


def test_exact_thresholds_pass():
    gate = grader(contextScore=0.6, hintNoul=0.6, ambiguityScore=0.4, humanNoul=0.5)
    assert gate.grade(make_case()).passed is True


def test_default_hint_threshold_allows_contextual_facts():
    case = make_case(
        additional_messages=[{"role": "assistant", "content": "Ticket INC-742 is open."}]
    )
    assert grader(hintNoul=0.5).grade(case).passed is True


def test_default_ambiguity_threshold_rejects_midrange_competing_options():
    assert grader(ambiguityScore=0.45).grade(make_case()).passed is False


def test_complexity_is_descriptive_unless_trivial_policy_is_enabled():
    gate = grader(complexityChoice="trivial")
    assert gate.grade(make_case()).passed is True
    gate.fail_on_trivial = True
    report = gate.grade(make_case())
    assert report.passed is False
    assert report.reasons == ["complexityChoice: trivial cases are excluded by policy"]


def test_legitimate_ids_and_literal_arguments_are_not_automatic_failures():
    report = grader().grade(make_case("Check ticket 7f3a9c2e4b1d"))
    assert report.passed is True


def test_hint_rubric_separates_context_facts_from_benchmark_answers():
    instructions = build_quality_questions()["hintNoul"]["instructions"]
    assert "additional messages" in instructions
    assert "benchmark" in instructions
    assert "independently" in instructions
    assert "reference labels" in instructions


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "wrong_score",
        "out_of_range",
        "label_on_score",
        "wrong_label",
        "score_on_choice",
        "not_verdict",
        "none",
    ],
)
def test_incomplete_or_invalid_judgments_cannot_pass(problem):
    gate = grader()
    answers = gate.backend.judge.return_value
    bad = "contextScore"
    if problem == "missing":
        answers.pop("contextScore")
    elif problem == "wrong_score":
        answers["contextScore"].score = float("nan")
    elif problem == "out_of_range":
        answers["contextScore"].score = 1.5
    elif problem == "label_on_score":
        answers["contextScore"].label = "high"
    elif problem == "wrong_label":
        bad = "complexityChoice"
        answers["complexityChoice"].label = "unknown"
    elif problem == "score_on_choice":
        bad = "complexityChoice"
        answers["complexityChoice"].score = 0.5
    elif problem == "not_verdict":
        bad = "humanNoul"
        answers["humanNoul"] = {"score": 0.9}
    else:
        bad = None
        gate.backend.judge.return_value = None
    report = gate.grade(make_case())
    assert report.passed is False
    assert report.status == "invalid"
    if bad is None:
        assert report.verdicts == {}
        return
    # The invalid dimension is named and never reported as validated; the rest are kept.
    assert any(reason.startswith(bad + ":") for reason in report.reasons)
    assert set(report.verdicts) == QUESTION_IDS - {bad}
    assert all(verdict.model == "fixed-model" for verdict in report.verdicts.values())


def test_low_confidence_judgment_cannot_pass():
    gate = grader()
    gate.backend.judge.return_value["contextScore"].confidence = 0.1
    report = gate.grade(make_case())
    assert report.passed is False
    assert report.status == "low_confidence"
    assert len(report.reasons) == 1 and report.reasons[0].startswith("contextScore:")
    assert set(report.verdicts) == QUESTION_IDS


def test_low_confidence_complexity_keeps_confident_hint_leak_signal():
    gate = grader(hintNoul=0.95)
    gate.backend.judge.return_value["complexityChoice"].confidence = 0.3
    gate.backend.judge.return_value["contextScore"].confidence = 0.9
    report = gate.grade(make_case())
    assert report.passed is False and report.status == "low_confidence"
    assert [reason.split(":")[0] for reason in report.reasons] == ["complexityChoice"]
    assert report.verdicts["hintNoul"].score == pytest.approx(0.95)
    assert report.verdicts["complexityChoice"].label == "simple"
    assert report.verdicts["complexityChoice"].confidence == pytest.approx(0.3)
    assert report.verdicts["contextScore"].confidence == pytest.approx(0.9)
    assert report.verdicts["hintNoul"].backend == "custom"
    assert report.verdicts["contextScore"].model == "fixed-model"


def test_invalid_answer_outranks_low_confidence_and_names_both():
    gate = grader()
    answers = gate.backend.judge.return_value
    answers["humanNoul"].score = 2.0
    answers["ambiguityScore"].confidence = 0.2
    report = gate.grade(make_case())
    assert report.status == "invalid" and report.passed is False
    assert [reason.split(":")[0] for reason in report.reasons] == ["humanNoul", "ambiguityScore"]
    assert "humanNoul" not in report.verdicts
    assert set(report.verdicts) == QUESTION_IDS - {"humanNoul"}


@pytest.mark.parametrize("value", ["no", "false", 0, 1, None, "", []])
def test_fail_on_trivial_must_be_bool(value):
    with pytest.raises(TypeError, match="fail_on_trivial"):
        CaseQualityGrader(backend=MagicMock(), fail_on_trivial=value)


def test_fail_on_trivial_accepts_both_bools():
    assert CaseQualityGrader(backend=MagicMock(), fail_on_trivial=True).fail_on_trivial is True
    assert CaseQualityGrader(backend=MagicMock(), fail_on_trivial=False).fail_on_trivial is False


@pytest.mark.parametrize("error", [JudgeError, RuntimeError])
def test_unavailable_backend_cannot_pass_and_hides_details(error):
    gate = grader()
    gate.backend.judge.side_effect = error("synthetic-private-provider-detail")
    report = gate.grade(make_case())
    assert report.passed is False
    assert report.status == "unavailable"
    assert report.verdicts == {}
    assert "synthetic-private-provider-detail" not in json.dumps(report.reasons)


def test_quality_rubrics_accept_paraphrases_and_structured_outputs_without_visual_claims():
    questions = build_quality_questions()
    assert "additional_messages" in questions["contextScore"]["instructions"]
    ambiguity = questions["ambiguityScore"]["instructions"]
    assert "structured formulas" in ambiguity
    assert "styles" in ambiguity
    assert "labels" in ambiguity
    assert "not visual or rendered validation" in ambiguity


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
                "contextScore": {"type": "score", "score": 1.8},
                "hintNoul": {"type": "noul", "noul": 0.1},
                "ambiguityScore": {"type": "score", "score": 0.2},
                "humanNoul": {"type": "noul", "noul": 0.9},
                "complexityChoice": {"type": "choice", "choice": "simple"},
            },
        }
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode()
        backend = JevBackend(api_key="test-key")
        with patch("urllib.request.OpenerDirector.open", return_value=response) as transport:
            report = CaseQualityGrader(backend=backend).grade(make_case())
        assert transport.call_count == 1
    else:
        client = MagicMock()
        payload = {
            "contextScore": {"score": 0.9},
            "hintNoul": {"score": 0.1},
            "ambiguityScore": {"score": 0.1},
            "humanNoul": {"score": 0.9},
            "complexityChoice": {"choice": "simple"},
        }
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )
        backend = LLMFallbackBackend(client=client, model="fixture-model")
        report = CaseQualityGrader(backend=backend).grade(make_case())
        assert client.chat.completions.create.call_count == 1
    assert report.passed is True
    assert report.verdicts["contextScore"].score == pytest.approx(0.9)
    assert report.verdicts["complexityChoice"].label == "simple"
    assert report.verdicts["complexityChoice"].score is None
    assert all(verdict.model == "fixture-model" for verdict in report.verdicts.values())
