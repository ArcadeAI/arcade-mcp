"""Live integration tests for SmartCritic that hit the real OpenAI and
Anthropic APIs.

These tests are gated behind the ``smart_critic_live`` pytest marker and
auto-skip when the corresponding API keys are not present in the environment.

To run locally:

1. Put your keys in ``<worktree-root>/.env`` (already git-ignored)::

       OPENAI_API_KEY=sk-...
       ANTHROPIC_API_KEY=sk-ant-...

   (Optionally override the judge models used here)::

       SMART_CRITIC_OPENAI_MODEL=gpt-4o-mini
       SMART_CRITIC_ANTHROPIC_MODEL=claude-haiku-4-5-20251001

2. Run only these tests::

       uv run pytest libs/tests/arcade_evals/test_smart_critic_live.py \
           -m smart_critic_live --no-cov -v

Assertions are conservative — we rely on the judge consistently distinguishing
clearly-matching from clearly-mismatching pairs, not on precise numeric
values. This keeps the tests stable across model updates.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from arcade_evals.smart_critic import SmartCritic
from arcade_evals.smart_critic_mode import SmartCriticMode

# Load .env from the worktree root so local runs pick up API keys without
# requiring the user to export them.
#
# Subtlety: some dev shells (and `uv run`) propagate *empty-string* env vars
# for API keys. We pre-clean those empties, then call load_dotenv with
# override=False so any legit shell-set key wins. override=True would leak
# .env values into the global pytest env and break tests in other modules
# that expect OPENAI_API_KEY/ANTHROPIC_API_KEY to be unset.
try:
    from dotenv import load_dotenv

    for _name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if _name in os.environ and not os.environ[_name]:
            del os.environ[_name]

    _WORKTREE_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(_WORKTREE_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover - dotenv is a dev dep
    pass


def _env_nonempty(name: str) -> str | None:
    """Return env var value if set AND non-empty, else None."""
    value = os.getenv(name)
    return value if value else None


pytestmark = [
    pytest.mark.evals,
    pytest.mark.smart_critic_live,
]


OPENAI_API_KEY = _env_nonempty("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _env_nonempty("ANTHROPIC_API_KEY")

# Cheap + fast judge models by default; override via env for different tiers.
# Defaults track the latest mini/haiku tiers available at time of writing
# (Apr 2026) — small enough to run 10+ tests quickly, smart enough to return
# valid JSON scores reliably.
OPENAI_JUDGE_MODEL = os.getenv("SMART_CRITIC_OPENAI_MODEL", "gpt-5.4-mini")
ANTHROPIC_JUDGE_MODEL = os.getenv(
    "SMART_CRITIC_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"
)


needs_openai = pytest.mark.skipif(
    not OPENAI_API_KEY,
    reason="OPENAI_API_KEY not set (add it to <worktree>/.env)",
)
needs_anthropic = pytest.mark.skipif(
    not ANTHROPIC_API_KEY,
    reason="ANTHROPIC_API_KEY not set (add it to <worktree>/.env)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _openai_critic(
    mode: SmartCriticMode = SmartCriticMode.SIMILARITY,
    *,
    match_threshold: float = 0.7,
    weight: float = 1.0,
    criteria_prompt: str | None = None,
) -> SmartCritic:
    critic = SmartCritic(
        critic_field="value",
        weight=weight,
        mode=mode,
        judge_provider="openai",
        judge_model=OPENAI_JUDGE_MODEL,
        match_threshold=match_threshold,
        criteria_prompt=criteria_prompt,
    )
    # Provide runtime context even when a per-critic judge is set so the
    # API-key resolver can reuse it (and we verify the full resolution path).
    critic.configure_runtime("openai", OPENAI_JUDGE_MODEL, OPENAI_API_KEY)
    return critic


def _anthropic_critic(
    mode: SmartCriticMode = SmartCriticMode.SIMILARITY,
    *,
    match_threshold: float = 0.7,
    weight: float = 1.0,
    criteria_prompt: str | None = None,
) -> SmartCritic:
    critic = SmartCritic(
        critic_field="value",
        weight=weight,
        mode=mode,
        judge_provider="anthropic",
        judge_model=ANTHROPIC_JUDGE_MODEL,
        match_threshold=match_threshold,
        criteria_prompt=criteria_prompt,
    )
    critic.configure_runtime("anthropic", ANTHROPIC_JUDGE_MODEL, ANTHROPIC_API_KEY)
    return critic


# ---------------------------------------------------------------------------
# High-confidence end-to-end cases (one per provider, each direction)
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_openai_judge_scores_near_identical_values_high() -> None:
    critic = _openai_critic(SmartCriticMode.SIMILARITY)
    result = await critic.async_evaluate(
        "The meeting is at 3pm on Tuesday.",
        "The meeting happens on Tuesday at 3 p.m.",
    )
    assert result["match"] is True
    assert result["score"] >= 0.7
    assert isinstance(result["comment"], str) and result["comment"].strip()


@needs_openai
@pytest.mark.asyncio
async def test_openai_judge_scores_unrelated_values_low() -> None:
    critic = _openai_critic(SmartCriticMode.SIMILARITY, match_threshold=0.5)
    result = await critic.async_evaluate(
        "The quarterly revenue was $4.2M.",
        "My dog's favorite color is blue.",
    )
    assert result["match"] is False
    assert result["score"] <= 0.3


@needs_anthropic
@pytest.mark.asyncio
async def test_anthropic_judge_scores_near_identical_values_high() -> None:
    critic = _anthropic_critic(SmartCriticMode.SIMILARITY)
    result = await critic.async_evaluate(
        "Send the report to the engineering team.",
        "Forward this report over to the engineers.",
    )
    assert result["match"] is True
    assert result["score"] >= 0.7
    assert isinstance(result["comment"], str) and result["comment"].strip()


@needs_anthropic
@pytest.mark.asyncio
async def test_anthropic_judge_scores_unrelated_values_low() -> None:
    critic = _anthropic_critic(SmartCriticMode.SIMILARITY, match_threshold=0.5)
    result = await critic.async_evaluate(
        "Python is a programming language.",
        "The Eiffel Tower is in Paris.",
    )
    assert result["match"] is False
    assert result["score"] <= 0.3


# ---------------------------------------------------------------------------
# Every built-in mode should produce a sensible score on a clearly-good pair
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode",
    [
        SmartCriticMode.SIMILARITY,
        SmartCriticMode.CORRECTNESS,
        SmartCriticMode.RELEVANCE,
        SmartCriticMode.COMPLETENESS,
        SmartCriticMode.COHERENCE,
    ],
)
async def test_openai_every_builtin_mode_scores_well_on_a_good_pair(
    mode: SmartCriticMode,
) -> None:
    critic = _openai_critic(mode)
    result = await critic.async_evaluate(
        "The capital of France is Paris.",
        "Paris is the capital city of France.",
    )
    assert 0.0 <= result["score"] <= 1.0
    # A clearly-good pair should clear the default threshold under any
    # reasonable evaluation lens. If this fails we almost certainly have a
    # prompt/parsing regression, not a model regression.
    assert result["score"] >= 0.7, (
        f"Mode {mode.value} scored only {result['score']} on a clearly "
        f"matching pair. Comment: {result['comment']}"
    )


# ---------------------------------------------------------------------------
# CUSTOM mode with a user-supplied criteria prompt
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_openai_custom_mode_follows_user_criteria() -> None:
    """Verify CUSTOM-mode criteria ordering: concise subject must score
    strictly higher than a verbose subject covering the same topic.

    Absolute thresholds are unreliable on small judge models for CUSTOM
    mode (no rubric guardrails), so we assert the ORDERING instead — that
    is the contract users actually rely on.
    """
    critic = _openai_critic(
        SmartCriticMode.CUSTOM,
        criteria_prompt=(
            "You are scoring an email subject line. A GOOD subject line is "
            "CONCISE (under 8 words) and ON-TOPIC relative to the EXPECTED "
            "value. A BAD subject line is verbose/rambly. "
            "Score 1.0 for an ideal concise on-topic subject. "
            "Score 0.0 for a verbose rambly subject. Use intermediate values "
            "for partial matches."
        ),
        match_threshold=0.7,
    )

    # Concise, on-topic
    good = await critic.async_evaluate(
        "Q3 product launch announcement",
        "Announcing our Q3 product launch",
    )
    # Verbose, rambly
    verbose = await critic.async_evaluate(
        "Q3 product launch announcement",
        (
            "Dear valued customers, we are absolutely thrilled to finally "
            "announce our much-awaited third-quarter product launch extravaganza"
        ),
    )

    # Ordering is the contract; it must be strictly concise > verbose.
    assert good["score"] > verbose["score"], (good, verbose)
    # And the verbose one should be clearly below threshold.
    assert verbose["score"] < 0.6, verbose


# ---------------------------------------------------------------------------
# Cross-provider: eval runs on OpenAI, judge on Anthropic (env-var path)
# ---------------------------------------------------------------------------


@needs_openai
@needs_anthropic
@pytest.mark.asyncio
async def test_cross_provider_judge_uses_env_var_for_foreign_provider() -> None:
    critic = SmartCritic(
        critic_field="value",
        weight=1.0,
        mode=SmartCriticMode.SIMILARITY,
        judge_provider="anthropic",
        judge_model=ANTHROPIC_JUDGE_MODEL,
    )
    # Eval "runs" on OpenAI — but the judge is Anthropic. Since the
    # providers differ, _resolve_api_key must look up ANTHROPIC_API_KEY
    # from the environment rather than reuse the OpenAI eval key.
    critic.configure_runtime("openai", "gpt-4o", OPENAI_API_KEY)

    result = await critic.async_evaluate("yes", "yes")
    assert result["match"] is True
    assert result["score"] >= 0.8


# ---------------------------------------------------------------------------
# Weight scaling & EvalCase integration
# ---------------------------------------------------------------------------


@needs_openai
@pytest.mark.asyncio
async def test_score_scales_by_weight() -> None:
    critic_full = _openai_critic(SmartCriticMode.SIMILARITY, weight=1.0)
    critic_half = _openai_critic(SmartCriticMode.SIMILARITY, weight=0.5)

    args = ("Paris is the capital of France.", "The capital of France is Paris.")
    full = await critic_full.async_evaluate(*args)
    half = await critic_half.async_evaluate(*args)

    # Both should score well, and the weighted score should reflect the
    # weight (allow a tolerance since the judge may give different raw
    # scores across calls).
    assert full["score"] >= 0.7
    assert half["score"] >= 0.35
    # Half-weighted must be strictly lower than full-weighted for the same
    # pair (scores are weighted; any non-zero judgment is scaled).
    assert half["score"] < full["score"]


@needs_openai
@pytest.mark.asyncio
async def test_evalcase_evaluate_async_pipeline_with_smart_critic() -> None:
    """End-to-end: plug SmartCritic into EvalCase and verify scoring."""
    from arcade_evals._evalsuite._types import EvalRubric, NamedExpectedToolCall
    from arcade_evals.critic import BinaryCritic
    from arcade_evals.eval import EvalCase

    smart = _openai_critic(SmartCriticMode.SIMILARITY, weight=1.0)
    # Rename the field to match what we'll put in the tool call args below.
    smart.critic_field = "summary"

    case = EvalCase(
        name="pipeline",
        system_message="sys",
        user_message="user",
        expected_tool_calls=[
            NamedExpectedToolCall(
                name="Tool.Summarize",
                args={"doc_id": 42, "summary": "The meeting is at 3pm Tuesday."},
            )
        ],
        critics=[
            BinaryCritic(critic_field="doc_id", weight=1.0),
            smart,
        ],
        rubric=EvalRubric(),
        additional_messages=[],
    )

    actual = [("Tool.Summarize", {"doc_id": 42, "summary": "Tuesday at 3pm we meet."})]
    result = await case.evaluate_async(actual)

    assert result.passed is True
    assert result.score >= 0.8
    # The smart critic's reasoning must survive the pipeline.
    smart_entry = next(r for r in result.results if r["field"] == "summary")
    assert smart_entry.get("comment"), (
        "SmartCritic reasoning was not preserved through evaluate_async"
    )
