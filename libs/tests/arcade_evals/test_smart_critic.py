"""Tests for the LLM-based SmartCritic.

These tests mock the LLM call boundary so no real API calls are made. Each
test pins down a single behavior of the critic so failures point directly at
the broken piece.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from arcade_evals.errors import WeightError
from arcade_evals.smart_critic import SmartCritic, SmartCriticMode
from arcade_evals.smart_critic_prompts import (
    CUSTOM_OUTPUT_FORMAT_INSTRUCTIONS,
    DEFAULT_SYSTEM_PROMPT,
    MODE_RUBRICS,
)
from arcade_evals.weights import FuzzyWeight

pytestmark = pytest.mark.evals


# ---------------------------------------------------------------------------
# SmartCriticMode enum
# ---------------------------------------------------------------------------


class TestSmartCriticMode:
    """The enum drives prompt selection — if a mode is missing a criteria
    prompt, construction should fail loudly."""

    def test_all_expected_modes_are_defined(self) -> None:
        expected = {
            "SIMILARITY",
            "CORRECTNESS",
            "RELEVANCE",
            "COMPLETENESS",
            "COHERENCE",
            "CUSTOM",
        }
        assert expected == {m.name for m in SmartCriticMode}

    def test_non_custom_modes_have_rubrics(self) -> None:
        """Every non-CUSTOM mode must have a defined rubric. CUSTOM is the
        only free-score path remaining."""
        for mode in SmartCriticMode:
            if mode is SmartCriticMode.CUSTOM:
                continue
            assert mode in MODE_RUBRICS
            rubric = MODE_RUBRICS[mode]
            assert len(rubric) > 0, f"{mode} has no rubric criteria"
            # Rubric weights must sum to 1.0 so the unweighted score is
            # always in [0, 1] before the critic's own weight is applied.
            assert abs(sum(c.weight for c in rubric) - 1.0) < 1e-9, (
                f"{mode} rubric weights do not sum to 1.0"
            )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestSmartCriticConstruction:
    def test_default_construction(self) -> None:
        critic = SmartCritic(critic_field="query", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        assert critic.critic_field == "query"
        assert critic.weight == 1.0
        assert critic.mode is SmartCriticMode.SIMILARITY
        assert critic.match_threshold == 0.7
        assert critic.judge_provider is None
        assert critic.judge_model is None
        assert critic.system_prompt is None
        assert critic.criteria_prompt is None

    def test_custom_mode_without_criteria_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="CUSTOM mode requires"):
            SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.CUSTOM)

    def test_custom_mode_with_criteria_prompt_ok(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.CUSTOM,
            criteria_prompt="Rate the poetic quality.",
        )
        assert critic.mode is SmartCriticMode.CUSTOM
        assert critic.criteria_prompt == "Rate the poetic quality."

    def test_has_smart_critic_marker(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        assert getattr(critic, "_is_smart_critic", False) is True

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(WeightError):
            SmartCritic(
                critic_field="x", weight=-0.1, mode=SmartCriticMode.SIMILARITY
            )

    def test_fuzzy_weight_accepted(self) -> None:
        critic = SmartCritic(
            critic_field="x", weight=FuzzyWeight.HIGH, mode=SmartCriticMode.SIMILARITY
        )
        assert critic.weight is FuzzyWeight.HIGH


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------


class TestPromptBuilding:
    def test_default_system_prompt_used_when_not_overridden(self) -> None:
        # Built-in modes (like SIMILARITY) always use rubric-style prompts.
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        system, user = critic._build_prompt("expected_value", "actual_value")
        assert DEFAULT_SYSTEM_PROMPT in system
        # Rubric prompt advertises the allowed yes/partial/no values and the
        # specific criterion keys for this mode.
        assert '"yes"' in system and '"partial"' in system and '"no"' in system
        assert "same_core_meaning" in system
        # User message carries the values.
        assert "expected_value" in user
        assert "actual_value" in user

    def test_system_prompt_override_preserves_rubric_contract(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.SIMILARITY,
            system_prompt="You are a strict judge.",
        )
        system, _ = critic._build_prompt("e", "a")
        assert "You are a strict judge." in system
        # Rubric output instructions must still be appended so parsing works.
        assert '"yes"' in system and "same_core_meaning" in system

    def test_rubric_used_for_every_builtin_mode(self) -> None:
        """Each built-in mode should emit its own set of criterion keys."""
        from arcade_evals.smart_critic_prompts import MODE_RUBRICS

        for mode in SmartCriticMode:
            if mode is SmartCriticMode.CUSTOM:
                continue
            critic = SmartCritic(critic_field="x", weight=1.0, mode=mode)
            system, user = critic._build_prompt("expected_val", "actual_val")
            # Expected & actual always carried in the user message.
            assert "expected_val" in user
            assert "actual_val" in user
            # All rubric criterion keys for this mode must appear in system.
            for criterion in MODE_RUBRICS[mode]:
                assert criterion.key in system

    def test_criteria_prompt_rejected_for_builtin_modes(self) -> None:
        """Built-in modes use their fixed rubric; allowing criteria_prompt
        here would silently bypass the rubric's determinism. We force the
        user to pick CUSTOM mode if they want free-form criteria."""
        with pytest.raises(ValueError, match="CUSTOM"):
            SmartCritic(
                critic_field="x",
                weight=1.0,
                mode=SmartCriticMode.CORRECTNESS,
                criteria_prompt="Focus only on numeric precision.",
            )

    def test_custom_mode_uses_free_score_prompt(self) -> None:
        """CUSTOM mode is the one remaining free-score path — it inlines
        the user's criteria and asks for a single float score."""
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.CUSTOM,
            criteria_prompt="Focus only on numeric precision.",
        )
        system, user = critic._build_prompt("e", "a")
        assert "Focus only on numeric precision." in user
        assert CUSTOM_OUTPUT_FORMAT_INSTRUCTIONS in system
        # Rubric keys must NOT leak into CUSTOM prompts. "factually_accurate"
        # is a CORRECTNESS-rubric criterion; CUSTOM mode doesn't have it.
        assert "factually_accurate" not in system
        # (Already asserted above via the rubric-key leak check.)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Rubric-mode parsing (the default for built-in modes)."""

    def _critic(self, **kw: Any) -> SmartCritic:
        # SIMILARITY rubric: same_core_meaning (0.5), no_contradiction (0.3),
        # same_key_entities (0.2). All "yes" → 1.0.
        return SmartCritic(
            critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY, **kw
        )

    def test_valid_rubric_json_all_yes(self) -> None:
        raw = (
            '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
            '"yes", "same_key_entities": "yes"}, "reasoning": "great"}'
        )
        score, reasoning, breakdown = self._critic()._parse_response(raw)
        assert score == pytest.approx(1.0)
        assert reasoning == "great"
        assert breakdown is not None
        assert sum(breakdown.values()) == pytest.approx(1.0)

    def test_rubric_partial_maps_to_half(self) -> None:
        raw = (
            '{"criteria": {"same_core_meaning": "partial", "no_contradiction": '
            '"yes", "same_key_entities": "no"}, "reasoning": "mixed"}'
        )
        score, _, breakdown = self._critic()._parse_response(raw)
        # 0.5*0.5 + 1.0*0.3 + 0.0*0.2 = 0.25 + 0.3 + 0.0 = 0.55
        assert score == pytest.approx(0.55)
        assert breakdown == pytest.approx({
            "same_core_meaning": 0.25,
            "no_contradiction": 0.30,
            "same_key_entities": 0.0,
        })

    def test_rubric_accepts_flat_keys(self) -> None:
        """Some judges forget to nest under "criteria" — accept that too."""
        raw = (
            '{"same_core_meaning": "yes", "no_contradiction": "yes", '
            '"same_key_entities": "yes", "reasoning": "great"}'
        )
        score, _, _ = self._critic()._parse_response(raw)
        assert score == pytest.approx(1.0)

    def test_rubric_missing_criterion_treated_as_no(self) -> None:
        """A missing answer must not silently boost the score."""
        raw = (
            '{"criteria": {"same_core_meaning": "yes"}, "reasoning": "partial"}'
        )
        score, _, breakdown = self._critic()._parse_response(raw)
        # Only same_core_meaning scored (0.5 * 1.0); others default to "no".
        assert score == pytest.approx(0.5)
        assert breakdown is not None
        assert breakdown["no_contradiction"] == 0.0
        assert breakdown["same_key_entities"] == 0.0

    def test_rubric_accepts_synonyms(self) -> None:
        raw = (
            '{"criteria": {"same_core_meaning": "true", "no_contradiction": '
            '"partially", "same_key_entities": "false"}, "reasoning": "."}'
        )
        score, _, _ = self._critic()._parse_response(raw)
        # true→1.0, partially→0.5, false→0.0
        assert score == pytest.approx(0.5 + 0.15)

    def test_rubric_accepts_json_booleans(self) -> None:
        """Regression: some judges emit JSON true/false instead of the
        requested strings. json.loads turns those into Python bools, and
        without a bool-aware normalizer every criterion silently scores 0."""
        raw = (
            '{"criteria": {"same_core_meaning": true, "no_contradiction": '
            'true, "same_key_entities": false}, "reasoning": "."}'
        )
        score, _, breakdown = self._critic()._parse_response(raw)
        # true * 0.5 + true * 0.3 + false * 0.2 = 0.80
        assert score == pytest.approx(0.8)
        assert breakdown == pytest.approx({
            "same_core_meaning": 0.5,
            "no_contradiction": 0.3,
            "same_key_entities": 0.0,
        })

    def test_rubric_accepts_numeric_scores(self) -> None:
        """Numeric rubric answers (0 / 0.5 / 1) should also be tolerated."""
        raw = (
            '{"criteria": {"same_core_meaning": 1, "no_contradiction": 0.5, '
            '"same_key_entities": 0}, "reasoning": "."}'
        )
        score, _, _ = self._critic()._parse_response(raw)
        # 1*0.5 + 0.5*0.3 + 0*0.2 = 0.65
        assert score == pytest.approx(0.65)

    def test_rubric_in_markdown_code_block(self) -> None:
        raw = (
            'Here:\n```json\n{"criteria": {"same_core_meaning": "yes", '
            '"no_contradiction": "yes", "same_key_entities": "yes"}, '
            '"reasoning": "great"}\n```'
        )
        score, _, _ = self._critic()._parse_response(raw)
        assert score == pytest.approx(1.0)

    def test_rubric_malformed_response_falls_back_to_zero(self) -> None:
        score, reasoning, breakdown = self._critic()._parse_response(
            "I think this is good."
        )
        assert score == 0.0
        assert "parse" in reasoning.lower() or "unable" in reasoning.lower()
        assert breakdown is None

    def test_custom_mode_uses_free_score_parsing(self) -> None:
        """CUSTOM mode has no rubric, so it parses a single score float."""
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.CUSTOM,
            criteria_prompt="Rate however you want.",
        )
        score, reasoning, breakdown = critic._parse_response(
            '{"score": 0.42, "reasoning": "ok"}'
        )
        assert score == 0.42
        assert reasoning == "ok"
        assert breakdown is None

    def test_custom_mode_score_is_clamped(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.CUSTOM,
            criteria_prompt="Rate.",
        )
        score_low, _, _ = critic._parse_response('{"score": -0.5}')
        score_high, _, _ = critic._parse_response('{"score": 1.5}')
        assert score_low == 0.0
        assert score_high == 1.0


# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------


class TestConfigureRuntime:
    def test_configure_runtime_stores_eval_context(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        assert critic._runtime_eval_provider == "openai"
        assert critic._runtime_eval_model == "gpt-4o"
        assert critic._runtime_eval_api_key == "sk-eval"

    def test_per_critic_config_wins_when_no_override(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.SIMILARITY,
            judge_provider="anthropic",
            judge_model="claude-sonnet",
        )
        critic.configure_runtime(
            "openai",
            "gpt-4o",
            "sk-eval",
            cli_judge_provider="openai",
            cli_judge_model="gpt-5",
            judge_override=False,
        )
        provider, model = critic._resolve_judge()
        assert provider == "anthropic"
        assert model == "claude-sonnet"

    def test_override_replaces_per_critic_config(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.SIMILARITY,
            judge_provider="anthropic",
            judge_model="claude-sonnet",
        )
        critic.configure_runtime(
            "openai",
            "gpt-4o",
            "sk-eval",
            cli_judge_provider="openai",
            cli_judge_model="gpt-5",
            judge_override=True,
        )
        provider, model = critic._resolve_judge()
        assert provider == "openai"
        assert model == "gpt-5"

    def test_cli_judge_used_as_fallback_when_critic_unset(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime(
            "openai",
            "gpt-4o",
            "sk-eval",
            cli_judge_provider="anthropic",
            cli_judge_model="claude-sonnet",
            judge_override=False,
        )
        provider, model = critic._resolve_judge()
        assert provider == "anthropic"
        assert model == "claude-sonnet"

    def test_eval_model_used_as_ultimate_fallback(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        provider, model = critic._resolve_judge()
        assert provider == "openai"
        assert model == "gpt-4o"


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------


class TestApiKeyResolution:
    def test_same_provider_uses_eval_key(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        assert critic._resolve_api_key("openai") == "sk-eval"

    def test_different_provider_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
        assert critic._resolve_api_key("anthropic") == "sk-ant-env"

    def test_different_provider_missing_env_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="API key"):
            critic._resolve_api_key("anthropic")

    def test_unknown_provider_gives_actionable_error(self) -> None:
        """When the judge provider isn't in our env-var map, the error must
        name the supported providers — never interpolate None into the text."""
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")
        with pytest.raises(RuntimeError) as exc:
            critic._resolve_api_key("unknownprovider")
        msg = str(exc.value)
        assert "None" not in msg
        assert "unknownprovider" in msg
        assert "openai" in msg and "anthropic" in msg


# ---------------------------------------------------------------------------
# Async evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAsyncEvaluate:
    async def test_sync_evaluate_raises_helpful_error(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        with pytest.raises(RuntimeError, match="async"):
            critic.evaluate("e", "a")

    async def test_async_evaluate_calls_llm_and_scores(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        # SIMILARITY always uses the rubric; the mock must match that shape.
        mocked = AsyncMock(return_value=(
            '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
            '"yes", "same_key_entities": "partial"}, "reasoning": "close match"}'
        ))
        with patch.object(critic, "_call_llm", mocked):
            result = await critic.async_evaluate("hello world", "hello there")

        # 1.0*0.5 + 1.0*0.3 + 0.5*0.2 = 0.9
        assert result["score"] == pytest.approx(0.9)
        assert result["match"] is True
        assert result["comment"] == "close match"
        assert "criteria_breakdown" in result
        mocked.assert_awaited_once()

    async def test_async_evaluate_respects_match_threshold(self) -> None:
        critic = SmartCritic(
            critic_field="x",
            weight=1.0,
            mode=SmartCriticMode.SIMILARITY,
            match_threshold=0.95,
        )
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        # Score = 1.0*0.5 + 1.0*0.3 + 0.5*0.2 = 0.9 → below 0.95 threshold.
        mocked = AsyncMock(return_value=(
            '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
            '"yes", "same_key_entities": "partial"}, "reasoning": "close"}'
        ))
        with patch.object(critic, "_call_llm", mocked):
            result = await critic.async_evaluate("e", "a")

        assert result["match"] is False
        assert result["score"] == pytest.approx(0.9)

    async def test_async_evaluate_scales_by_weight(self) -> None:
        critic = SmartCritic(critic_field="x", weight=0.5, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        # All-yes rubric = 1.0 raw; weighted by 0.5 critic weight = 0.5.
        mocked = AsyncMock(return_value=(
            '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
            '"yes", "same_key_entities": "yes"}, "reasoning": "perfect"}'
        ))
        with patch.object(critic, "_call_llm", mocked):
            result = await critic.async_evaluate("e", "a")

        assert result["score"] == pytest.approx(0.5)

    async def test_async_evaluate_with_malformed_llm_response(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        mocked = AsyncMock(return_value="not JSON at all")
        with patch.object(critic, "_call_llm", mocked):
            result = await critic.async_evaluate("e", "a")

        assert result["score"] == 0.0
        assert result["match"] is False

    async def test_async_evaluate_without_runtime_raises(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        # No configure_runtime + no per-critic judge model
        with pytest.raises(RuntimeError, match="judge"):
            await critic.async_evaluate("e", "a")

    async def test_async_evaluate_passes_expected_and_actual_to_prompt(self) -> None:
        critic = SmartCritic(critic_field="x", weight=1.0, mode=SmartCriticMode.SIMILARITY)
        critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        captured: dict[str, Any] = {}

        async def fake_call(system: str, user: str, **kwargs: Any) -> str:
            captured["system"] = system
            captured["user"] = user
            captured["kwargs"] = kwargs
            return (
                '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
                '"yes", "same_key_entities": "yes"}, "reasoning": "ok"}'
            )

        with patch.object(critic, "_call_llm", fake_call):
            await critic.async_evaluate("expected-v1", "actual-v2")

        assert "expected-v1" in captured["user"]
        assert "actual-v2" in captured["user"]
        # Judge resolution should surface the effective provider/model.
        assert captured["kwargs"]["provider"] == "openai"
        assert captured["kwargs"]["model"] == "gpt-4o"


# ---------------------------------------------------------------------------
# Integration with EvalCase.evaluate_async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSmartCriticInEvalCase:
    """SmartCritic must plug into the existing scoring pipeline via
    EvalCase.evaluate_async (mixed with sync critics)."""

    async def test_mixed_sync_and_smart_critics(self) -> None:
        from arcade_evals._evalsuite._types import EvalRubric, NamedExpectedToolCall
        from arcade_evals.critic import BinaryCritic
        from arcade_evals.eval import EvalCase

        sync_critic = BinaryCritic(critic_field="a", weight=1.0)
        smart_critic = SmartCritic(
            critic_field="b", weight=1.0, mode=SmartCriticMode.SIMILARITY
        )
        smart_critic.configure_runtime("openai", "gpt-4o", "sk-eval")

        case = EvalCase(
            name="mixed",
            system_message="sys",
            user_message="user",
            expected_tool_calls=[
                NamedExpectedToolCall(name="Tool.Foo", args={"a": 1, "b": "expected"})
            ],
            critics=[sync_critic, smart_critic],
            rubric=EvalRubric(),
            additional_messages=[],
        )

        mocked = AsyncMock(return_value=(
            '{"criteria": {"same_core_meaning": "yes", "no_contradiction": '
            '"yes", "same_key_entities": "yes"}, "reasoning": "identical"}'
        ))
        with patch.object(smart_critic, "_call_llm", mocked):
            result = await case.evaluate_async(
                [("Tool.Foo", {"a": 1, "b": "actual"})]
            )

        # Both critics + tool_selection should score full marks.
        assert result.score == pytest.approx(1.0)
        assert result.passed is True
        # The SmartCritic comment must be preserved in results.
        smart_entry = next(r for r in result.results if r["field"] == "b")
        assert smart_entry.get("comment") == "identical"
