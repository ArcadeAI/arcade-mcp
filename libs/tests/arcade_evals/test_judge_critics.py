"""Tests for Jev judge backends and judge critics (offline only, no network)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from arcade_evals.critic import JudgeCriticBase
from arcade_evals.judge import JevBackend, resolve_jev_api_key

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


def _score_response(score=1.6, confidence=0.8, model="jev-1.13.0"):
    payload = {
        "model": model,
        "answers": {
            "q": {
                "type": "score",
                "score": score,
                "confidence": confidence,
                "legend": {"0": "a", "1": "b", "2": "c"},
                "probabilities": {"0": 0.2, "1": 0.0, "2": 0.8},
            }
        },
    }
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__.return_value = resp
    return resp


class TestJevBackend:
    """Tests for the Jev HTTP backend."""

    def test_normalizes_score_to_unit_range(self) -> None:
        backend = JevBackend(api_key="k")
        questions = {"q": {"type": "score", "instructions": "x", "criteria": ["a", "b", "c"]}}
        with patch("urllib.request.urlopen", return_value=_score_response()):
            verdicts = backend.judge(state={"expected": "a", "actual": "b"}, questions=questions)
        assert verdicts["q"].score == pytest.approx(0.8)  # 1.6 / (3 - 1)
        assert verdicts["q"].confidence == pytest.approx(0.8)
        assert verdicts["q"].backend == "jev"
        assert verdicts["q"].model == "jev-1.13.0"

    def test_noul_carries_no_confidence(self) -> None:
        payload = {"model": "jev-1.13.0", "answers": {"q": {"type": "noul", "noul": 0.93}}}
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode()
        resp.__enter__.return_value = resp
        backend = JevBackend(api_key="k")
        with patch("urllib.request.urlopen", return_value=resp):
            verdicts = backend.judge(
                state={}, questions={"q": {"type": "noul", "instructions": "x"}}
            )
        assert verdicts["q"].score == pytest.approx(0.93)
        assert verdicts["q"].confidence is None

    def test_http_error_raises_judge_error(self) -> None:
        from arcade_evals.judge import JudgeError

        backend = JevBackend(api_key="k")
        with (
            patch("urllib.request.urlopen", side_effect=OSError("down")),
            pytest.raises(JudgeError),
        ):
            backend.judge(state={}, questions={"q": {"type": "noul", "instructions": "x"}})

    def test_missing_key_raises_judge_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from arcade_evals.judge import JudgeError

        monkeypatch.delenv("JEV_API_KEY", raising=False)
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        with pytest.raises(JudgeError):
            JevBackend()

    def test_non_http_base_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="http"):
            JevBackend(api_key="k", base_url="file:///etc/passwd")


class TestJudgeKeyResolution:
    """Tests for JEV_API_KEY / TYPESAFE_API_KEY resolution order."""

    def test_prefers_jev_over_typesafe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JEV_API_KEY", "jev-key")
        monkeypatch.setenv("TYPESAFE_API_KEY", "ts-key")
        assert resolve_jev_api_key() == "jev-key"

    def test_falls_back_to_typesafe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        monkeypatch.setenv("TYPESAFE_API_KEY", "ts-key")
        assert resolve_jev_api_key() == "ts-key"

    def test_returns_none_without_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        assert resolve_jev_api_key() is None


class _FakeCompletions:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def create(self, **kwargs: object) -> object:
        assert kwargs["response_format"] == {"type": "json_object"}
        assert kwargs["temperature"] == 0
        message = type("M", (), {"content": json.dumps(self._payload)})()
        choice = type("C", (), {"message": message})()
        return type("R", (), {"choices": [choice]})()


class _FakeOpenAIClient:
    def __init__(self, payload: object) -> None:
        self.chat = type("Chat", (), {"completions": _FakeCompletions(payload)})()


class TestLLMFallbackBackend:
    """Tests for the OpenAI-compatible LLM fallback (fake client, no network)."""

    def test_parses_scores_per_question(self) -> None:
        from arcade_evals.judge import LLMFallbackBackend

        client = _FakeOpenAIClient({"q": {"score": 0.7}})
        backend = LLMFallbackBackend(client=client, model="test-model")
        verdicts = backend.judge(
            state={"expected": "a"}, questions={"q": {"type": "noul", "instructions": "x"}}
        )
        assert verdicts["q"].score == pytest.approx(0.7)
        assert verdicts["q"].confidence is None  # LLM reports no confidence
        assert verdicts["q"].backend == "llm"
        assert verdicts["q"].model == "test-model"

    def test_bad_json_raises_judge_error(self) -> None:
        from arcade_evals.judge import JudgeError, LLMFallbackBackend

        client = _FakeOpenAIClient({"q": {"score": "high"}})
        backend = LLMFallbackBackend(client=client, model="test-model")
        with pytest.raises(JudgeError):
            backend.judge(state={}, questions={"q": {"type": "noul", "instructions": "x"}})

    def test_out_of_range_score_raises_judge_error(self) -> None:
        from arcade_evals.judge import JudgeError, LLMFallbackBackend

        client = _FakeOpenAIClient({"q": {"score": 1.5}})
        backend = LLMFallbackBackend(client=client, model="test-model")
        with pytest.raises(JudgeError):
            backend.judge(state={}, questions={"q": {"type": "noul", "instructions": "x"}})

    def test_transport_failure_raises_judge_error(self) -> None:
        from arcade_evals.judge import JudgeError, LLMFallbackBackend

        class _BrokenCompletions:
            def create(self, **kwargs: object) -> object:
                raise ConnectionError("down")

        client = type(
            "Broken", (), {"chat": type("Chat", (), {"completions": _BrokenCompletions()})()}
        )()
        backend = LLMFallbackBackend(client=client, model="test-model")
        with pytest.raises(JudgeError):
            backend.judge(state={}, questions={"q": {"type": "noul", "instructions": "x"}})


class FakeBackend:
    """Scripted backend: maps question id -> verdict or exception."""

    def __init__(self, script: dict) -> None:
        self.script = script
        self.calls = 0

    def judge(self, *, state: dict, questions: dict) -> dict:
        self.calls += 1
        out = {}
        for qid in questions:
            item = self.script[qid]
            if isinstance(item, Exception):
                raise item
            out[qid] = item
        return out


def test_fake_backend_satisfies_protocol() -> None:
    from arcade_evals.judge import JudgeBackend

    assert isinstance(FakeBackend({}), JudgeBackend)


class TestJudgeChain:
    """Tests for the JudgeCriticBase fallback chain (local double, no network)."""

    def test_explicit_verdict_maps_to_match_and_weighted_score(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _TestCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({
            "t": JudgeVerdict(score=0.9, confidence=0.9, backend="test", model="m")
        })
        result = critic.evaluate("expected text", "paraphrased expected text")
        assert result["match"] is True
        assert result["score"] == pytest.approx(0.9)
        assert result["backend"] == "test"
        assert result["model"] == "m"

    def test_low_score_confidence_escalates_to_deterministic_tier(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _TestCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({
            "t": JudgeVerdict(score=0.5, confidence=0.0, backend="test", model="m")
        })
        result = critic.evaluate("hello world", "hello world")
        assert result["match"] is True
        assert result["backend"] == "deterministic"

    def test_verdict_without_confidence_is_accepted_directly(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _TestCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({
            "t": JudgeVerdict(score=0.55, confidence=None, backend="test", model="m")
        })
        result = critic.evaluate("expected text", "actual text")
        assert result["backend"] == "test"  # None confidence never escalates
        assert result["match"] is False  # 0.55 < default threshold 0.7

    def test_backend_failure_falls_back_without_raising(self) -> None:
        from arcade_evals.judge import JudgeError

        critic = _TestCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({"t": JudgeError("down")})
        result = critic.evaluate("hello world", "hello world")
        assert result["match"] is True
        assert result["score"] == pytest.approx(1.0)

    def test_both_none_returns_full_score_without_judging(self) -> None:
        critic = _TestCritic(critic_field="text", weight=0.5)
        critic.backend = FakeBackend({"t": Exception("must not be called")})
        result = critic.evaluate(None, None)
        assert result["match"] is True
        assert result["score"] == pytest.approx(0.5)
        assert result["backend"] == "none"

    def test_repeated_evaluation_hits_cache(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _TestCritic(critic_field="text", weight=1.0)
        fake = FakeBackend({
            "t": JudgeVerdict(score=0.9, confidence=0.9, backend="test", model="m")
        })
        critic.backend = fake
        critic.evaluate("a", "b")
        critic.evaluate("a", "b")
        assert fake.calls == 1

    def test_no_key_no_llm_uses_deterministic_tier(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        critic = _TestCritic(critic_field="text", weight=1.0)
        result = critic.evaluate("hello world", "hello world")
        assert result["backend"] == "deterministic"
        assert result["match"] is True


class _TestCritic(JudgeCriticBase):
    """Minimal concrete critic used only to exercise the shared chain."""

    question_id = "t"

    def build_state(self, expected: object, actual: object) -> dict:
        return {"expected": expected, "actual": actual}

    def build_questions(self, expected: object, actual: object) -> dict:
        return {"t": {"type": "score", "instructions": "x", "criteria": ["a", "b", "c"]}}


def _similarity() -> object:
    from arcade_evals.critic import SemanticSimilarityCritic

    return SemanticSimilarityCritic(critic_field="text", weight=1.0)


class TestSemanticSimilarityCritic:
    """Tests for semantic equivalence judging (scripted verdicts, no network)."""

    def test_builds_score_question_with_ordered_levels(self) -> None:
        critic = _similarity()
        questions = critic.build_questions("Trees on the west coast", "Western coast trees")
        assert set(questions) == {"similarity"}
        assert questions["similarity"]["type"] == "score"
        assert len(questions["similarity"]["criteria"]) == 3

    def test_low_scripted_similarity_score_fails_threshold(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _similarity()
        critic.backend = FakeBackend({
            "similarity": JudgeVerdict(score=0.05, confidence=0.95, backend="test", model="m")
        })
        result = critic.evaluate("device with GPS", "device without GPS")
        assert result["match"] is False
        assert result["score"] == pytest.approx(0.05)

    def test_high_scripted_similarity_score_passes_threshold(self) -> None:
        from arcade_evals.judge import JudgeVerdict

        critic = _similarity()
        critic.backend = FakeBackend({
            "similarity": JudgeVerdict(score=0.95, confidence=0.9, backend="test", model="m")
        })
        result = critic.evaluate("Trees in the West Coast", "Western coast trees")
        assert result["match"] is True
        assert result["score"] == pytest.approx(0.95)


class TestIntentionCritic:
    """Tests for intent-fulfillment judging (scripted verdicts, no network)."""

    def test_requires_non_empty_intent(self) -> None:
        from arcade_evals.critic import IntentionCritic

        with pytest.raises(ValueError):
            IntentionCritic(critic_field="text", weight=1.0, intent="  ")

    def test_builds_noul_question_against_intent(self) -> None:
        from arcade_evals.critic import IntentionCritic
        from arcade_evals.judge import JudgeVerdict

        critic = IntentionCritic(
            critic_field="subject",
            weight=0.5,
            intent="Professional email subject about spring sale",
        )
        questions = critic.build_questions("Spring Sale!", "SPRING SALE!!!")
        assert questions["intent"]["type"] == "noul"
        assert "spring sale" in questions["intent"]["instructions"].lower()
        critic.backend = FakeBackend({
            "intent": JudgeVerdict(score=0.2, confidence=None, backend="test", model="m")
        })
        result = critic.evaluate("Spring Sale!", "SPRING SALE!!!")
        assert result["match"] is False
        assert result["score"] == pytest.approx(0.1)  # 0.2 * weight 0.5

    def test_deterministic_fallback_is_exact_match(self) -> None:
        from arcade_evals.critic import IntentionCritic
        from arcade_evals.judge import JudgeError

        critic = IntentionCritic(critic_field="text", weight=1.0, intent="Say hello")
        critic.backend = FakeBackend({"intent": JudgeError("down")})
        assert critic.evaluate("hello", "hello")["match"] is True
        # Same topic, different wording: overlap must NOT count as intent.
        assert critic.evaluate("hello there friend", "hello")["match"] is False

    def test_cache_accounts_for_intent(self) -> None:
        from arcade_evals.critic import IntentionCritic
        from arcade_evals.judge import JudgeVerdict

        critic = IntentionCritic(critic_field="text", weight=1.0, intent="Say hello")
        fake = FakeBackend({
            "intent": JudgeVerdict(score=0.9, confidence=None, backend="test", model="m")
        })
        critic.backend = fake
        critic.evaluate("a", "b")
        critic.intent = "Say goodbye"
        critic.evaluate("a", "b")
        assert fake.calls == 2


class TestGroundednessCritic:
    """Tests for factual-grounding judging (scripted verdicts, no network)."""

    def test_builds_score_question(self) -> None:
        from arcade_evals.critic import GroundednessCritic

        critic = GroundednessCritic(critic_field="text", weight=1.0)
        questions = critic.build_questions("GPS included", "GPS plus free car")
        assert set(questions) == {"groundedness"}
        assert questions["groundedness"]["type"] == "score"
        assert len(questions["groundedness"]["criteria"]) == 3

    def test_low_scripted_groundedness_score_fails_threshold(self) -> None:
        from arcade_evals.critic import GroundednessCritic
        from arcade_evals.judge import JudgeVerdict

        critic = GroundednessCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({
            "groundedness": JudgeVerdict(score=0.1, confidence=0.9, backend="test", model="m")
        })
        result = critic.evaluate("GPS included", "GPS plus free car")
        assert result["match"] is False
        assert result["score"] == pytest.approx(0.1)


class TestCompletenessCritic:
    """Tests for requirement-coverage judging (scripted verdicts, no network)."""

    def test_builds_score_question(self) -> None:
        from arcade_evals.critic import CompletenessCritic

        critic = CompletenessCritic(critic_field="text", weight=1.0)
        questions = critic.build_questions("a b c", "a b c plus more")
        assert set(questions) == {"completeness"}
        assert questions["completeness"]["type"] == "score"
        assert len(questions["completeness"]["criteria"]) == 3

    def test_high_scripted_completeness_score_passes_threshold(self) -> None:
        from arcade_evals.critic import CompletenessCritic
        from arcade_evals.judge import JudgeVerdict

        critic = CompletenessCritic(critic_field="text", weight=1.0)
        critic.backend = FakeBackend({
            "completeness": JudgeVerdict(score=0.95, confidence=0.9, backend="test", model="m")
        })
        result = critic.evaluate("a b c", "a b c plus more")
        assert result["match"] is True
        assert result["score"] == pytest.approx(0.95)


def test_public_exports() -> None:
    import arcade_evals

    for name in (
        "SemanticSimilarityCritic",
        "IntentionCritic",
        "GroundednessCritic",
        "CompletenessCritic",
        "JevBackend",
        "LLMFallbackBackend",
        "JudgeBackend",
        "JudgeVerdict",
    ):
        assert name in arcade_evals.__all__
        assert hasattr(arcade_evals, name)
