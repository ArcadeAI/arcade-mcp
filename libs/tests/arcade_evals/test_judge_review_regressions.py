"""Boundary regressions for injected adapters and the actual HTTP opener."""

import io
import json
import urllib.request
from email.message import Message
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.response import addinfourl

import pytest
from arcade_evals import (
    CaseQualityGrader,
    CompletenessCritic,
    EvalSuite,
    ExpectedMCPToolCall,
    IntentionCritic,
    JevBackend,
    JudgeCriticGroup,
    JudgeVerdict,
    LLMFallbackBackend,
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
def test_actual_instance_opener_rejects_redirect_without_second_request(kind, monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network"))
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


def make_client(*, finish_reason=None, refusal=None, model=None):
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=json.dumps({"similarity": {"score": 1.0}}), refusal=refusal
                ),
            )
        ],
    )
    return client


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
