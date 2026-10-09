"""The same categorical contract across Jev and an OpenAI-compatible provider."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from arcade_evals import JevBackend, JudgeBackend, JudgeVerdict, LLMFallbackBackend
from arcade_evals.errors import JudgeError

pytestmark = pytest.mark.evals

QUESTIONS = {
    "complexity": {
        "type": "choice",
        "instructions": "Classify the work needed.",
        "criteria": {"simple": "One clear step", "complex": "Multiple dependent steps"},
    },
    "context": {
        "type": "score",
        "instructions": "Is context sufficient?",
        "criteria": ["no", "yes"],
    },
    "human": {
        "type": "noul",
        "instructions": "Is the request natural?",
        "criteria": {"true": "yes", "false": "no"},
    },
}


def run_judge(provider, answer):
    if provider == "jev":
        payload = {
            "model": "fixed-model",
            "answers": {
                "complexity": {"type": "choice", **answer},
                "context": {"type": "score", "score": 0.9},
                "human": {"type": "noul", "noul": 0.8},
            },
        }
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode()
        backend = JevBackend(api_key="test-key")
        with patch("urllib.request.OpenerDirector.open", return_value=response) as request:
            verdicts = backend.judge(state={"user": "Plan a trip"}, questions=QUESTIONS)
        assert request.call_count == 1
    else:
        payload = {"complexity": answer, "context": {"score": 0.9}, "human": {"score": 0.8}}
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )
        backend = LLMFallbackBackend(client=client, model="fixed-model")
        verdicts = backend.judge(state={"user": "Plan a trip"}, questions=QUESTIONS)
        assert client.chat.completions.create.call_count == 1
    assert isinstance(backend, JudgeBackend)
    return verdicts


@pytest.mark.parametrize("provider", ["jev", "llm"])
def test_mixed_questions_use_one_provider_neutral_contract(provider):
    verdicts = run_judge(provider, {"choice": "complex"})
    choice = verdicts["complexity"]
    assert choice.label == "complex"
    assert choice.score is None  # A category is not a numeric judgment.
    assert choice.confidence is None
    assert choice.probabilities == {}
    assert choice.model == "fixed-model"
    assert verdicts["context"].score == 0.9
    assert verdicts["human"].score == 0.8


def test_jev_choice_preserves_only_reported_confidence_and_distribution():
    verdict = run_judge(
        "jev",
        {
            "choice": "complex",
            "confidence": 0.7,
            "probabilities": {"simple": 0.3, "complex": 0.7},
        },
    )["complexity"]
    assert verdict.confidence == 0.7
    assert verdict.probabilities == {"simple": 0.3, "complex": 0.7}


@pytest.mark.parametrize("provider", ["jev", "llm"])
@pytest.mark.parametrize("answer", [{}, {"choice": "unknown"}, {"choice": []}, {"choice": 1}])
def test_missing_or_unknown_choice_is_a_judge_error(provider, answer):
    with pytest.raises(JudgeError):
        run_judge(provider, answer)


@pytest.mark.parametrize(
    "extra",
    [
        {"probabilities": {"simple": 0.2, "complex": 0.2}},
        {"probabilities": {"simple": -0.1, "complex": 1.1}},
        {"probabilities": {"unknown": 1.0}},
        {"probabilities": {"simple": 1.0}},
        {"probabilities": {"simple": True, "complex": 0.0}},
        {"probabilities": {"simple": float("nan"), "complex": 0.0}},
        {"probabilities": []},
        {"confidence": 2.0},
    ],
)
def test_invalid_jev_choice_metadata_is_rejected(extra):
    with pytest.raises(JudgeError):
        run_judge("jev", {"choice": "complex", **extra})


def test_existing_verdict_positional_arguments_remain_compatible():
    verdict = JudgeVerdict(0.8, None, "custom", "model", {"original": True})
    assert verdict.raw == {"original": True}
    assert verdict.label is None
