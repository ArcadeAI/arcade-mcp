"""Boundary regressions for injected adapters and the actual HTTP opener."""

import asyncio
import copy
import io
import json
import urllib.request
from email.message import Message
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.response import addinfourl

import pytest
from arcade_evals import (
    BinaryCritic,
    CaseQualityGrader,
    CompletenessCritic,
    EvalSuite,
    ExpectedMCPToolCall,
    GroundednessCritic,
    IntentionCritic,
    JevBackend,
    JudgeCriticGroup,
    JudgeScope,
    JudgeVerdict,
    LLMFallbackBackend,
    NumericCritic,
    SemanticSimilarityCritic,
)
from arcade_evals.case_quality import build_quality_questions
from arcade_evals.errors import JudgeError
from arcade_evals.eval import EvalRubric, EvaluationResult, _resolve_pass_rule

pytestmark = pytest.mark.evals
QUESTIONS = {"similarity": {"type": "score", "criteria": ["no", "yes"]}}


class RedirectResponse(urllib.request.HTTPHandler):
    handler_order = 100

    def __init__(self):
        super().__init__()
        self.requests = []

    def http_open(self, request):
        self.requests.append(request)
        headers = Message()
        headers["Location"] = "http://other.invalid/credential-sink"
        response = addinfourl(io.BytesIO(b""), headers, request.full_url, 302)
        response.msg = "Found"
        return response


@pytest.mark.parametrize("kind", ["jev", "llm"])
def test_actual_instance_opener_rejects_redirect_without_second_request(kind, offline_socket_guard):
    backend = (
        JevBackend(api_key="synthetic", base_url="http://localhost/judge")
        if kind == "jev"
        else LLMFallbackBackend(api_key="synthetic", base_url="http://localhost/v1")
    )
    fake = RedirectResponse()
    backend._opener.add_handler(fake)
    with pytest.raises(JudgeError) as error:
        backend.judge(state={}, questions=QUESTIONS)
    assert len(fake.requests) == 1
    assert fake.requests[0].host == "localhost"
    assert "synthetic" not in str(error.value)


def quality_verdicts():
    return {
        qid: JudgeVerdict(None, None, "fixture", label="simple")
        if question["type"] == "choice"
        else JudgeVerdict(0.9 if qid in ("contextScore", "humanNoul") else 0.1, None, "fixture")
        for qid, question in build_quality_questions().items()
    }


@pytest.mark.parametrize("confidence", [True, "bad", float("nan"), float("inf"), -0.1, 1.1])
@pytest.mark.parametrize("qid", ["contextScore", "complexityChoice"])
def test_injected_quality_confidence_is_validated_before_comparison(confidence, qid):
    verdicts = quality_verdicts()
    verdicts[qid].confidence = confidence
    backend = MagicMock()
    backend.judge.return_value = verdicts
    suite = EvalSuite("quality", "Use tools")
    suite.add_case(name="quality", user_message="Read the ticket", expected_tool_calls=[])
    report = CaseQualityGrader(backend=backend).grade(suite.cases[0])
    assert report.status == "invalid"
    assert report.passed is False


@pytest.mark.parametrize(
    "probabilities",
    [
        {"simple": True},
        {"simple": float("nan")},
        {"simple": 1.0},
        {"trivial": 0.5, "simple": 0.5, "complex": 0.5, "adversarial": 0.5},
    ],
)
def test_injected_choice_probabilities_fail_closed(probabilities):
    verdicts = quality_verdicts()
    verdicts["complexityChoice"].probabilities = probabilities
    backend = MagicMock()
    backend.judge.return_value = verdicts
    suite = EvalSuite("quality", "Use tools")
    suite.add_case(name="quality", user_message="Read the ticket", expected_tool_calls=[])
    assert CaseQualityGrader(backend=backend).grade(suite.cases[0]).status == "invalid"


def test_historical_constructor_positions_and_keyword_only_opt_in():
    backend = MagicMock()
    critic = IntentionCritic("text", 1.0, 0.7, 0.5, backend, "jev-latest", None, "Say hello")
    assert critic.backend is backend
    assert critic.intent == "Say hello"
    assert critic.provider is None and critic.fallback == "none"
    with pytest.raises(TypeError):
        SemanticSimilarityCritic("text", 1.0, 0.7, 0.5, backend, "model", None, "jev")


def test_withheld_group_preserves_siblings_and_uncertain_evidence():
    backend = MagicMock()
    backend.judge.return_value = {
        "check_0": JudgeVerdict(0.9, 0.9, "fixture", "v1", raw={"reason": "supported"}),
        "check_1": JudgeVerdict(0.8, 0.1, "fixture", "v1", raw={"reason": "uncertain"}),
    }
    group = JudgeCriticGroup(
        "text", 1.0, [CompletenessCritic("text", 1.0), CompletenessCritic("text", 1.0)], backend
    )
    result = group.evaluate("reference", "candidate")
    assert result["status"] == "low_confidence"
    assert result["score"] == 0.0 and not result["match"] and not result["judged"]
    assert [item["status"] for item in result["details"]] == ["ok", "low_confidence"]
    assert result["details"][1]["confidence"] == 0.1
    assert result["details"][1]["evidence"] == {"reason": "uncertain"}
    backend.judge.return_value.pop("check_1")
    missing = group.evaluate("reference", "candidate")
    assert missing["status"] == "unavailable" and len(missing["details"]) == 2
    assert missing["details"][0]["evidence"] == {"reason": "supported"}


def make_client(*, finish_reason=None, refusal=None, model=None, answer=None):
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=json.dumps({
                        "similarity": {"score": 1.0} if answer is None else answer
                    }),
                    refusal=refusal,
                ),
            )
        ],
    )
    return client


def llm_question(kind):
    return {
        "type": kind,
        "criteria": ["no", "yes"]
        if kind == "score"
        else {"true": "yes", "false": "no"}
        if kind == "noul"
        else {"simple": "One decision", "complex": "Dependent decisions"},
    }


@pytest.mark.parametrize(
    "kind,answer",
    [
        ("score", {"score": 1, "noul": 0}),
        ("score", {"score": 1, "type": "choice"}),
        ("score", {"score": 1, "type": "noul"}),
        ("score", {"score": 1, "choice": None}),
        ("score", {"score": 1, "label": "simple"}),
        ("noul", {"score": 1, "type": "score"}),
        ("noul", {"score": 1, "noul": 0}),
        ("noul", {"score": 1, "choice": "simple"}),
        ("noul", {"score": 1, "label": None}),
        ("choice", {"choice": "simple", "type": "score"}),
        ("choice", {"choice": "simple", "type": "noul"}),
        ("choice", {"choice": "simple", "score": 1}),
        ("choice", {"choice": "simple", "noul": 0}),
        ("choice", {"choice": "simple", "label": "complex"}),
        ("score", {"score": 1, "type": None}),
        ("noul", {"score": 1, "type": 1}),
        ("choice", {"choice": "simple", "type": []}),
    ],
)
def test_llm_conflicting_answer_kinds_fail_closed(kind, answer):
    client = make_client(finish_reason="stop", answer=answer)
    backend = LLMFallbackBackend(client=client)
    with pytest.raises(JudgeError):
        backend.judge(state={}, questions={"similarity": llm_question(kind)})


@pytest.mark.parametrize("kind", ["score", "noul", "choice"])
@pytest.mark.parametrize("declared_type", [False, True])
def test_llm_valid_answer_kinds_preserve_normalized_contract(kind, declared_type):
    answer = {"choice": "simple"} if kind == "choice" else {"score": 0.75}
    if declared_type:
        answer["type"] = kind
    client = make_client(answer=answer)
    verdict = LLMFallbackBackend(client=client).judge(
        state={}, questions={"similarity": llm_question(kind)}
    )["similarity"]
    assert verdict.label == ("simple" if kind == "choice" else None)
    assert verdict.score == (None if kind == "choice" else 0.75)
    assert client.chat.completions.create.call_args.kwargs["response_format"] == {
        "type": "json_object"
    }


@pytest.mark.parametrize("raises", [False, True])
def test_quality_backend_mutation_cannot_change_case_or_caller_inputs(raises):
    member = CompletenessCritic("text", 1.0, context={"source": ["member fact"]})
    group = JudgeCriticGroup("text", 1.0, [member], MagicMock(), context={"source": ["group fact"]})
    suite = EvalSuite("quality", "Use tools")
    suite.add_case(
        name="quality",
        user_message="Read the ticket",
        expected_tool_calls=[ExpectedMCPToolCall("read", {"text": ["reference"]})],
        additional_messages=[{"role": "user", "content": [{"text": "prior fact"}]}],
        critics=[group],
    )
    case = suite.cases[0]
    tools = [{"name": "read", "parameters": {"required": ["text"]}}]
    original = copy.deepcopy([
        case.additional_messages,
        case.expected_tool_calls[0].args,
        tools,
        group.context,
        member.context,
    ])

    def mutate(*, state, questions):
        state["model_visible"]["additional_messages"][0]["content"][0]["text"] = "MUTATED"
        state["reference_labels"]["expected"][0]["args"]["text"].append("MUTATED")
        state["tools"][0]["parameters"]["required"].append("MUTATED")
        state["critics"][0]["context"]["source"].append("MUTATED")
        state["critics"][0]["checks"][0]["context"]["source"].append("MUTATED")
        if raises:
            raise RuntimeError("Synthetic backend failure")
        return quality_verdicts()

    backend = MagicMock()
    backend.judge.side_effect = mutate
    report = CaseQualityGrader(backend=backend).grade(case, tools=tools)
    assert report.status == ("unavailable" if raises else "passed")
    assert report.passed is not raises
    assert [
        case.additional_messages,
        case.expected_tool_calls[0].args,
        tools,
        group.context,
        member.context,
    ] == original


@pytest.mark.parametrize(
    "reason,refusal", [("length", None), ("content_filter", None), ("stop", "refused")]
)
def test_interrupted_or_refused_llm_cannot_pass(reason, refusal):
    client = make_client(finish_reason=reason, refusal=refusal)
    critic = SemanticSimilarityCritic("text", 1.0, backend=LLMFallbackBackend(client=client))
    assert critic.evaluate("reference", "candidate")["status"] == "unavailable"


@pytest.mark.parametrize("reason,reported", [(None, None), ("stop", "actual-version")])
def test_successful_llm_timeout_and_reported_model(reason, reported):
    client = make_client(finish_reason=reason, model=reported)
    backend = LLMFallbackBackend(client=client, model="alias", timeout=0.1)
    verdict = backend.judge(state={}, questions=QUESTIONS)["similarity"]
    assert verdict.score == 1.0 and verdict.model == (reported or "alias")
    assert client.chat.completions.create.call_args.kwargs["timeout"] == 0.1


@pytest.mark.parametrize(
    "question",
    [
        {"type": "unsupported", "criteria": ["no", "yes"]},
        {"type": "score", "criteria": ["single"]},
        {"type": "score", "criteria": {"wrong": "shape"}},
        {"type": "noul", "criteria": []},
        {"type": "noul", "criteria": {"yes": "yes", "no": "no"}},
    ],
)
@pytest.mark.parametrize("kind", ["jev", "llm"])
def test_invalid_rubrics_are_rejected_before_transport(question, kind):
    client = make_client()
    backend = (
        JevBackend(api_key="synthetic") if kind == "jev" else LLMFallbackBackend(client=client)
    )
    backend._opener = MagicMock()
    with pytest.raises(JudgeError):
        backend.judge(state={}, questions={"similarity": question})
    backend._opener.open.assert_not_called()
    client.chat.completions.create.assert_not_called()


def test_runner_exception_is_sanitized_and_tiny_weight_cannot_pass(caplog):
    class Raising(CompletenessCritic):
        def evaluate_in_scope(self, expected, actual, scope=None):
            raise RuntimeError("SYNTHETIC_PRIVATE_MARKER")

    suite = EvalSuite("unavailable", "Use echo")
    suite.add_case(
        name="case",
        user_message="Echo hello",
        expected_tool_calls=[ExpectedMCPToolCall("echo", {"text": "hello"})],
        critics=[Raising("text", 0.0001)],
    )
    result = suite.cases[0].evaluate([("echo", {"text": "hello"})])
    assert result.score > 0.99 and not result.passed
    assert "SYNTHETIC_PRIVATE_MARKER" not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.parametrize("rule", ["last", "mean", "majority"])
def test_unavailable_run_cannot_be_hidden_by_repeated_run_aggregation(rule):
    unavailable = EvaluationResult(score=0.9999, passed=False, unavailable=True)
    success = EvaluationResult(score=1.0, passed=True)
    assert _resolve_pass_rule([unavailable, success, success], 0.9999, rule, EvalRubric()) == (
        False,
        False,
    )


def numeric_error_suite(**rubric):
    suite = EvalSuite("critic-error", "Use echo", rubric=EvalRubric(**rubric))
    suite.add_case(
        name="case",
        user_message="Echo",
        expected_tool_calls=[ExpectedMCPToolCall("echo", {"flag": True, "n": 5})],
        critics=[BinaryCritic("flag", 0.9), NumericCritic("n", 0.1, value_range=(0, 10))],
    )
    return suite


def test_traditional_critic_error_fails_closed_and_is_not_judge_unavailability(caplog):
    suite = numeric_error_suite()
    healthy = suite.cases[0].evaluate([("echo", {"flag": True, "n": 5})])
    assert healthy.passed and not healthy.unavailable and not healthy.critic_error

    result = suite.cases[0].evaluate([("echo", {"flag": True, "n": "SYNTHETIC_PRIVATE_MARKER"})])
    weight = suite.rubric.tool_selection_weight
    # The failed critic's weight stays in the denominator: never approval.
    assert result.score == pytest.approx((weight + 0.9) / (weight + 1.0))
    assert not result.passed and not result.warning
    assert result.critic_error and not result.unavailable
    assert "critic" in result.failure_reason and "judge" not in result.failure_reason.lower()
    numeric = next(item for item in result.results if item["field"] == "n")
    assert numeric["status"] == "critic_error" and numeric["weight"] == 0.1
    assert numeric["score"] == 0.0 and numeric["match"] is False
    assert "NumericCritic" in caplog.text and "judge" not in caplog.text.lower()
    assert "SYNTHETIC_PRIVATE_MARKER" not in caplog.text and "Traceback" not in caplog.text


def test_traditional_critic_error_cannot_warn_or_pass_under_lenient_thresholds():
    suite = numeric_error_suite(fail_threshold=0.1, warn_threshold=0.05)
    result = suite.cases[0].evaluate([("echo", {"flag": True, "n": "abc"})])
    assert result.score > 0.9
    assert result.passed is False and result.warning is False and result.fail


def test_judge_exception_stays_judge_unavailability_not_critic_error():
    class Raising(CompletenessCritic):
        def evaluate_in_scope(self, expected, actual, scope=None):
            raise RuntimeError("synthetic")

    suite = EvalSuite("judge", "Use echo")
    suite.add_case(
        name="case",
        user_message="Echo",
        expected_tool_calls=[ExpectedMCPToolCall("echo", {"text": "hello"})],
        critics=[Raising("text", 0.5)],
    )
    result = suite.cases[0].evaluate([("echo", {"text": "hello"})])
    assert result.unavailable and not result.critic_error and not result.passed
    assert "judge" in result.failure_reason.lower()
    assert result.results[-1]["status"] == "unavailable"


def test_critic_and_judge_failures_are_both_reported():
    class Raising(CompletenessCritic):
        def evaluate_in_scope(self, expected, actual, scope=None):
            raise RuntimeError("synthetic")

    suite = EvalSuite("both", "Use echo")
    suite.add_case(
        name="case",
        user_message="Echo",
        expected_tool_calls=[ExpectedMCPToolCall("echo", {"text": "hello", "n": 1})],
        critics=[Raising("text", 0.5), NumericCritic("n", 0.5, value_range=(0, 2))],
    )
    result = suite.cases[0].evaluate([("echo", {"text": "hello", "n": "bad"})])
    assert result.unavailable and result.critic_error
    assert "judge" in result.failure_reason.lower() and "critic" in result.failure_reason.lower()


@pytest.mark.parametrize("rule", ["last", "mean", "majority"])
def test_critic_error_run_cannot_be_hidden_by_repeated_run_aggregation(rule):
    errored = EvaluationResult(score=0.9999, passed=False, critic_error=True)
    success = EvaluationResult(score=1.0, passed=True)
    assert _resolve_pass_rule([errored, success, success], 0.9999, rule, EvalRubric()) == (
        False,
        False,
    )


@pytest.mark.parametrize("rule", ["last", "mean", "majority"])
def test_repeated_runs_with_one_critic_error_fail_and_explain_why(rule):
    suite = numeric_error_suite()
    runs = iter([
        [("echo", {"flag": True, "n": 5})],
        [("echo", {"flag": True, "n": "abc"})],
        [("echo", {"flag": True, "n": 5})],
    ])

    async def predicted(*args, **kwargs):
        return next(runs)

    suite._run_openai = predicted  # type: ignore[method-assign]
    suite._process_tool_calls = lambda calls, registry=None: calls  # type: ignore[method-assign]
    outcome = asyncio.run(
        suite._run_case_with_stats(
            suite.cases[0], None, "model", "openai", num_runs=3, seed=None, pass_rule=rule
        )
    )
    aggregate = outcome["evaluation"]
    assert not aggregate.passed and not aggregate.warning
    assert aggregate.critic_error and not aggregate.unavailable
    assert aggregate.failure_reason and "judge" not in aggregate.failure_reason.lower()
    assert outcome["run_stats"]["passed"] == [True, False, True]


def echo_backend():
    backend = MagicMock()
    backend.judge.side_effect = lambda **request: {
        qid: JudgeVerdict(1.0, None, "fixture") for qid in request["questions"]
    }
    return backend


@pytest.mark.parametrize(
    "critic_cls,options",
    [(IntentionCritic, {"intent": "Answer from the source"}), (GroundednessCritic, {})],
)
def test_standalone_rubric_prefers_supplied_evidence_over_expected(critic_cls, options):
    # Checks what the judge is asked and shown; it cannot prove a model obeys the rubric.
    backend = echo_backend()
    context = {"source": "The office is in Berlin"}
    critic = critic_cls("text", 1.0, backend=backend, context=context, **options)
    scope = JudgeScope(user="Where is the office?")
    critic.evaluate_in_scope("Paris", "Paris", scope)
    request = backend.judge.call_args.kwargs
    assert request["state"]["context"] == context
    assert request["state"]["scope"]["user"] == "Where is the office?"
    assert request["state"]["expected"] == "Paris"
    instructions = request["questions"][critic.question_id]["instructions"]
    assert "`scope` or `context`" in instructions and "authoritative" in instructions
    assert "reference label" in instructions and "contradict" in instructions


@pytest.mark.parametrize(
    "critic_cls,options",
    [(IntentionCritic, {"intent": "Answer from the source"}), (GroundednessCritic, {})],
)
def test_standalone_without_evidence_sends_only_expected_as_source(critic_cls, options):
    backend = echo_backend()
    critic = critic_cls("text", 1.0, backend=backend, **options)
    critic.evaluate("Paris", "Paris")
    state = backend.judge.call_args.kwargs["state"]
    assert "context" not in state and "scope" not in state and state["expected"] == "Paris"
    instructions = backend.judge.call_args.kwargs["questions"][critic.question_id]["instructions"]
    assert "expected" in instructions


def test_grouped_checks_keep_their_own_evidence_and_precedence():
    backend = echo_backend()
    group = JudgeCriticGroup(
        "text",
        1.0,
        [
            GroundednessCritic("text", 1.0, context={"note": "CHECK_ZERO_ONLY"}),
            IntentionCritic("text", 1.0, intent="Cite the source", context="CHECK_ONE_ONLY"),
        ],
        backend,
        context={"source": "SHARED_SOURCE"},
    )
    group.evaluate_in_scope("Paris", "Paris", JudgeScope(user="Where is the office?"))
    request = backend.judge.call_args.kwargs
    state, checks = request["state"], request["state"]["checks"]
    assert state["context"] == {"source": "SHARED_SOURCE"} and state["scope"]["user"]
    assert checks["check_0"]["context"] == {"note": "CHECK_ZERO_ONLY"}
    assert checks["check_1"]["context"] == "CHECK_ONE_ONLY"
    assert "CHECK_ONE_ONLY" not in str(checks["check_0"])
    assert "CHECK_ZERO_ONLY" not in str(checks["check_1"])
    assert "intent" in checks["check_1"] and "intent" not in checks["check_0"]
    for qid, question in request["questions"].items():
        text = question["instructions"]
        assert f"`checks.{qid}`" in text and "takes precedence over the shared `context`" in text
        assert "Do not use other checks' evidence" in text and "authoritative" in text


def test_noul_llm_prompt_defines_true_probability_without_changing_score_rubric():
    prompt = LLMFallbackBackend.SYSTEM_PROMPT
    assert 'probability (0.0-1.0) that the criterion keyed "true" holds' in prompt
    assert "not a general quality score" in prompt
    assert "normalize to 0..1 using the first and last criterion as endpoints" in prompt
