"""Judge cache and metadata exercised through the real evaluation runner."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from arcade_evals import EvalSuite, ExpectedMCPToolCall, SemanticSimilarityCritic
from arcade_evals.errors import JudgeError
from arcade_evals.judge import JudgeVerdict

pytestmark = pytest.mark.evals


@pytest.fixture(autouse=True)
def offline(monkeypatch, offline_socket_guard):
    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)


class CountingBackend:
    def __init__(self, score=0.8, confidence=0.9):
        self.score = score
        self.confidence = confidence
        self.calls = 0

    def judge(self, *, state, questions):
        self.calls += 1
        return {
            qid: JudgeVerdict(self.score, self.confidence, "test", model="fixed-model")
            for qid in questions
        }


@pytest.mark.parametrize(
    "setting,value",
    [
        ("judge_model", "another-model"),
        ("llm_model", "another-llm"),
        ("min_confidence", 0.95),
        ("LEVELS", ["different", "rubric"]),
    ],
)
def test_cache_invalidates_when_judge_configuration_changes(setting, value):
    backend = CountingBackend()
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    critic.evaluate("hello world", "hello world")
    setattr(critic, setting, value)
    result = critic.evaluate("hello world", "hello world")
    assert backend.calls == 2
    if setting == "min_confidence":
        assert result["status"] == "low_confidence"


def test_cache_invalidates_when_backend_is_replaced():
    critic = SemanticSimilarityCritic("text", 1.0, backend=CountingBackend(0.8))
    assert critic.evaluate("hello", "world")["score"] == 0.8
    replacement = CountingBackend(0.2)
    critic.backend = replacement
    assert critic.evaluate("hello", "world")["score"] == 0.2
    assert replacement.calls == 1


def test_clear_cache_retries_previous_fallback():
    backend = CountingBackend(confidence=0.1)
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    assert critic.evaluate("hello", "hello")["status"] == "low_confidence"
    backend.confidence = 0.9
    assert critic.evaluate("hello", "hello")["backend"] == "test"
    assert backend.calls == 2


def test_weight_and_match_threshold_reuse_unweighted_verdict():
    backend = CountingBackend()
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    assert critic.evaluate("hello", "world")["match"] is True
    critic.weight = 0.5
    critic.match_threshold = 0.9
    result = critic.evaluate("hello", "world")
    assert result["score"] == 0.4
    assert result["match"] is False
    assert backend.calls == 2


def test_diagnostics_count_failed_and_successful_backend_attempts():
    backend = CountingBackend()
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    with patch("time.perf_counter", side_effect=[1.0, 1.025, 2.0, 2.075]):
        first = critic.evaluate("hello", "world")
        second = critic.evaluate("hello", "world")
    assert first["judge_calls"] == second["judge_calls"] == 1
    assert first["judge_latency_ms"] == pytest.approx(25.0)
    assert second["judge_latency_ms"] == pytest.approx(75.0)
    assert critic.judge_calls_total == 2
    assert critic.judge_latency_ms_total == pytest.approx(100.0)
    backend.judge = MagicMock(side_effect=JudgeError("private"))
    assert critic.evaluate("hello", "world")["status"] == "unavailable"
    assert critic.judge_calls_total == 3


def test_none_inputs_do_not_invoke_or_charge_a_judge():
    backend = CountingBackend()
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    result = critic.evaluate(None, None)
    assert result["judge_calls"] == 0
    assert result["judge_latency_ms"] == 0.0
    assert backend.calls == 0


@pytest.mark.asyncio
async def test_shared_cache_under_real_suite_concurrency():
    backend = CountingBackend()
    critic = SemanticSimilarityCritic("text", 1.0, backend=backend)
    suite = EvalSuite(name="Shared judge", system_message="Use echo", max_concurrent=4)
    suite.add_tool_definitions([
        {
            "name": "echo",
            "description": "Echo text",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
    ])
    for index in range(8):
        value = f"reference {index % 2}"
        suite.add_case(
            name=f"case-{index}",
            user_message=value,
            expected_tool_calls=[ExpectedMCPToolCall("echo", {"text": value})],
            critics=[critic],
        )

    active = peak = 0

    async def generate(**kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        value = kwargs["messages"][-1]["content"]
        tool_call = SimpleNamespace(
            type="function",
            id="offline-call",
            function=SimpleNamespace(name="echo", arguments=json.dumps({"text": value})),
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[tool_call]))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=generate)))
    result = await suite.run(client=client, model="offline-model")
    assert peak == 4
    assert len(result["cases"]) == 8
    assert backend.calls == 8  # Each case owns a memo; assignment/final share its pair.
    for case in result["cases"]:
        evaluation = case["evaluation"]
        detail = next(item for item in evaluation.results if item["field"] == "text")
        assert detail["backend"] == "test"
        assert detail["model"] == "fixed-model"
        assert detail["score"] == pytest.approx(0.8)
        assert detail["judge_calls"] == 1
        assert detail["judge_latency_ms"] >= 0.0
        tool_weight = suite.rubric.tool_selection_weight
        assert evaluation.score == pytest.approx((tool_weight + 0.8) / (tool_weight + 1.0))
