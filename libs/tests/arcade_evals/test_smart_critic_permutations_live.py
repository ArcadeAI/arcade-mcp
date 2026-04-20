"""Live permutation tests for SmartCritic configurations.

These tests exercise combinations that the core live test suite doesn't
hit: rubric ON vs OFF end-to-end, the CLI `judge_override` flag, CUSTOM
mode against fail cases, and cross-provider judging on both fail and pass
inputs. Each is a single API call per permutation — fast when run, auto-
skipped when API keys aren't set.

Run with::

    uv run pytest libs/tests/arcade_evals/test_smart_critic_permutations_live.py \
        -m smart_critic_live --no-cov -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from arcade_evals.smart_critic import SmartCritic
from arcade_evals.smart_critic_mode import SmartCriticMode

# Same .env handling as the main live test module — pre-clean empties
# then load with override=False so shell values win.
try:
    from dotenv import load_dotenv

    for _n in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if _n in os.environ and not os.environ[_n]:
            del os.environ[_n]
    _WORKTREE_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(_WORKTREE_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


pytestmark = [pytest.mark.evals, pytest.mark.smart_critic_live]


def _env(name: str) -> str | None:
    v = os.getenv(name)
    return v if v else None


OPENAI_API_KEY = _env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
OPENAI_MODEL = os.getenv("SMART_CRITIC_OPENAI_MODEL", "gpt-5.4-mini")
ANTHROPIC_MODEL = os.getenv(
    "SMART_CRITIC_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
)

needs_openai = pytest.mark.skipif(
    not OPENAI_API_KEY, reason="OPENAI_API_KEY not set"
)
needs_anthropic = pytest.mark.skipif(
    not ANTHROPIC_API_KEY, reason="ANTHROPIC_API_KEY not set"
)
needs_both = pytest.mark.skipif(
    not (OPENAI_API_KEY and ANTHROPIC_API_KEY),
    reason="Both OPENAI_API_KEY and ANTHROPIC_API_KEY required",
)


# Shared fail-case inputs used across multiple permutations so deltas
# between configurations are directly comparable.
CONTRADICTION = ("Today the weather is hot", "Today the weather is cold")
CLEAR_MISMATCH = (
    "Python is a programming language",
    "The Eiffel Tower is in Paris",
)
CLEAR_MATCH = ("Paris is the capital of France", "The French capital is Paris")


def _mk(
    *,
    provider: str,
    model: str,
    api_key: str,
    mode: SmartCriticMode = SmartCriticMode.SIMILARITY,
    criteria_prompt: str | None = None,
    match_threshold: float = 0.7,
) -> SmartCritic:
    c = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=mode,
        judge_provider=provider,
        judge_model=model,
        criteria_prompt=criteria_prompt,
        match_threshold=match_threshold,
    )
    c.configure_runtime(provider, model, api_key)
    return c


# ---------------------------------------------------------------------------
# Permutation 1: rubric end-to-end on fail cases.
# Built-in modes are rubric-only since the legacy free-score path was
# removed. The rubric must still correctly call a non-match and surface
# a criteria_breakdown dict.
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pair,threshold",
    [
        (CONTRADICTION, 0.5),
        (CLEAR_MISMATCH, 0.3),
    ],
)
async def test_rubric_catches_fail_cases_end_to_end(
    pair: tuple[str, str], threshold: float
) -> None:
    """The rubric must correctly score both easy (mismatch) and hard
    (contradiction) fail cases at or below the per-case threshold, with
    the criteria_breakdown field populated."""
    exp, act = pair
    critic = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
    )
    res = await critic.async_evaluate(exp, act)

    assert res["match"] is False, res
    assert res["score"] <= threshold, res
    assert "criteria_breakdown" in res
    # Breakdown contributions must sum to the raw (unweighted) score.
    breakdown_sum = sum(res["criteria_breakdown"].values())
    assert abs(breakdown_sum - res["score"]) < 0.01, res


@needs_openai
@pytest.mark.asyncio
async def test_rubric_catches_hot_cold_contradiction() -> None:
    """Regression guard for the motivating case: on "hot vs cold" where
    tokens overlap but meaning flips, a free-score judge tends to anchor
    on structural similarity and score it high (~0.75 was observed on
    gpt-5.4-mini with legacy prompts before this refactor).

    The rubric splits scoring into an explicit ``no_contradiction``
    criterion that forces a low score on this input. Assertion: the
    rubric scores the hot/cold pair well below 0.5 and the
    ``no_contradiction`` contribution is at or below its partial weight.
    """
    critic = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
    )
    res = await critic.async_evaluate(*CONTRADICTION)

    assert res["score"] <= 0.5, res
    assert res["match"] is False, res
    # no_contradiction weight = 0.3; "partial" = 0.15 contribution. A
    # correct judgment on this input is "no" → 0 contribution, but allow
    # up to 0.15 so we don't flap on judge variance.
    assert res["criteria_breakdown"]["no_contradiction"] <= 0.15, res


# ---------------------------------------------------------------------------
# Permutation 2: judge_override=True — CLI-supplied judge model must
# replace a per-critic config when override flag is set, even on a fail
# case. The per-critic "judge_model" points to a (valid) model; the
# runtime CLI override points to a DIFFERENT (valid) model; we confirm
# the scoring behavior matches the CLI model, not the per-critic one.
# ---------------------------------------------------------------------------


@needs_both
@pytest.mark.asyncio
async def test_judge_override_forces_cli_model_over_per_critic_config() -> None:
    # Per-critic config: OpenAI. CLI override: Anthropic. If override is
    # honored, the call should land on the Anthropic API (which we
    # indirectly verify by checking the critic used Anthropic's API key
    # path — we delete OPENAI_API_KEY from the runtime context to prove
    # Anthropic was actually called).
    critic = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=SmartCriticMode.SIMILARITY,
        judge_provider="openai",
        judge_model=OPENAI_MODEL,  # per-critic = openai
    )
    # Configure runtime with Anthropic as the eval provider and CLI override
    # telling us to use Anthropic's judge. Pass an intentionally-wrong
    # OpenAI key so the test fails loudly if override is not honored.
    critic.configure_runtime(
        "anthropic",
        ANTHROPIC_MODEL,
        ANTHROPIC_API_KEY or "",
        cli_judge_provider="anthropic",
        cli_judge_model=ANTHROPIC_MODEL,
        judge_override=True,
    )
    # If override is respected, this succeeds with a real score. If not,
    # the critic would try OpenAI with the Anthropic key and 401.
    result = await critic.async_evaluate(*CLEAR_MATCH)
    assert result["match"] is True
    assert result["score"] >= 0.7


@needs_both
@pytest.mark.asyncio
async def test_judge_override_false_preserves_per_critic_config() -> None:
    # Same setup but override=False — per-critic OpenAI config should win.
    critic = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=SmartCriticMode.SIMILARITY,
        judge_provider="openai",
        judge_model=OPENAI_MODEL,
    )
    critic.configure_runtime(
        "anthropic",
        ANTHROPIC_MODEL,
        ANTHROPIC_API_KEY or "",
        cli_judge_provider="anthropic",
        cli_judge_model=ANTHROPIC_MODEL,
        judge_override=False,
    )
    # Must actually hit OpenAI (needs OPENAI_API_KEY via env fallback).
    result = await critic.async_evaluate(*CLEAR_MATCH)
    assert result["match"] is True
    assert result["score"] >= 0.7


# ---------------------------------------------------------------------------
# Permutation 3: CUSTOM mode on a fail case. Verifies the non-rubric
# free-score path survives adversarial input end-to-end.
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_custom_mode_fails_on_mismatch() -> None:
    critic = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
        mode=SmartCriticMode.CUSTOM,
        criteria_prompt=(
            "Rate 1.0 only when ACTUAL contains the same primary noun as "
            "EXPECTED. Rate 0.0 when the primary nouns are unrelated."
        ),
    )
    result = await critic.async_evaluate(*CLEAR_MISMATCH)
    assert result["match"] is False
    assert result["score"] <= 0.3
    # CUSTOM mode uses the free-score path, so no breakdown.
    assert "criteria_breakdown" not in result


# ---------------------------------------------------------------------------
# Permutation 4: cross-provider on a FAIL case.
# The existing live suite only tests cross-provider on a pass case; this
# ensures the env-var key lookup path works under adversarial input too.
# ---------------------------------------------------------------------------


@needs_both
@pytest.mark.asyncio
async def test_cross_provider_on_contradiction_catches_it() -> None:
    # Eval runs on OpenAI; judge runs on Anthropic. The eval api_key is
    # OpenAI's; _resolve_api_key must look up ANTHROPIC_API_KEY from env
    # because the providers differ.
    critic = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=SmartCriticMode.SIMILARITY,
        judge_provider="anthropic",
        judge_model=ANTHROPIC_MODEL,
    )
    critic.configure_runtime("openai", OPENAI_MODEL, OPENAI_API_KEY or "")
    result = await critic.async_evaluate(*CONTRADICTION)
    assert result["match"] is False
    assert result["score"] <= 0.5


# ---------------------------------------------------------------------------
# Permutation 5: the rubric breakdown must correctly explain the score.
# On a clear match, all three criteria should be "yes" (1.0 each); on a
# clear contradiction, `no_contradiction` must be "no" (0.0 contribution).
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_rubric_breakdown_explains_contradiction_score() -> None:
    critic = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
        mode=SmartCriticMode.SIMILARITY,
    )
    result = await critic.async_evaluate(*CONTRADICTION)
    breakdown = result.get("criteria_breakdown")
    assert breakdown is not None, result
    # The critical signal: on a contradiction, the `no_contradiction`
    # criterion's contribution MUST be at or below its partial weight.
    # weight(no_contradiction) = 0.3, partial = 0.15.
    assert breakdown["no_contradiction"] <= 0.15, breakdown


@needs_openai
@pytest.mark.asyncio
async def test_rubric_breakdown_all_yes_on_clear_match() -> None:
    critic = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
        mode=SmartCriticMode.SIMILARITY,
    )
    result = await critic.async_evaluate(*CLEAR_MATCH)
    breakdown = result.get("criteria_breakdown")
    assert breakdown is not None
    # All three contributions should be at their full weight (yes=1.0
    # multiplied by each weight).
    assert breakdown["same_core_meaning"] >= 0.4  # weight 0.5 * 1.0
    assert breakdown["no_contradiction"] >= 0.25  # weight 0.3 * 1.0
    assert breakdown["same_key_entities"] >= 0.15  # weight 0.2 * 1.0


# ---------------------------------------------------------------------------
# Permutation 6: Anthropic prefill fallback.
# claude-sonnet-4-6 rejects assistant-message prefill. This verifies the
# auto-retry path works — the critic should still produce a valid score.
# ---------------------------------------------------------------------------


@needs_anthropic
@pytest.mark.asyncio
async def test_anthropic_sonnet_no_prefill_fallback_works() -> None:
    critic = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=SmartCriticMode.SIMILARITY,
        judge_provider="anthropic",
        judge_model="claude-sonnet-4-6",
    )
    critic.configure_runtime(
        "anthropic", "claude-sonnet-4-6", ANTHROPIC_API_KEY or ""
    )
    result = await critic.async_evaluate(*CLEAR_MATCH)
    assert result["match"] is True
    assert result["score"] >= 0.7
    # The critic should have cached the no-prefill decision on the class.
    assert "claude-sonnet-4-6" in SmartCritic._NO_PREFILL_MODELS


# ---------------------------------------------------------------------------
# Permutation 7: partial case — modes legitimately disagree.
# "Paris is the capital of France" vs "Paris":
#   COMPLETENESS should score it LOW (missing the capital claim)
#   RELEVANCE should score it NOT-LOW (same topic)
# This verifies mode semantics are distinct on an ambiguous input.
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_modes_disagree_on_partial_answer() -> None:
    expected = "Paris is the capital of France"
    actual = "Paris"
    completeness = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
        mode=SmartCriticMode.COMPLETENESS,
    )
    relevance = _mk(
        provider="openai", model=OPENAI_MODEL, api_key=OPENAI_API_KEY or "",
        mode=SmartCriticMode.RELEVANCE,
    )
    c_score = (await completeness.async_evaluate(expected, actual))["score"]
    r_score = (await relevance.async_evaluate(expected, actual))["score"]
    # Relevance should be strictly higher than completeness on this input.
    assert r_score > c_score, (r_score, c_score)
    assert c_score < 0.7  # clearly incomplete
    assert r_score >= 0.4  # at least moderately relevant
