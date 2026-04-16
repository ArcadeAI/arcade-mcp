"""
Example: LLM-as-judge evaluations using SmartCritic.

SmartCritic asks an LLM to score a tool argument qualitatively. It supports
several evaluation modes (SIMILARITY, CORRECTNESS, RELEVANCE, COMPLETENESS,
COHERENCE, CUSTOM) and returns a numeric score plus a short reasoning
comment, so scores aggregate into the same pipeline as deterministic critics.

Prerequisites:
    * Install with evals extras: ``uv tool install 'arcade-mcp[evals]'``
    * Set ``OPENAI_API_KEY`` (or ``ANTHROPIC_API_KEY``) in your environment.

Run with the standard evals CLI:
    arcade evals examples/mcp_servers/server_with_evaluations/evals
    # Optionally pick a dedicated judge model:
    arcade evals ... --judge-model anthropic:claude-sonnet-4-5-20250929
    # Force the CLI judge onto every SmartCritic:
    arcade evals ... --judge-model openai:gpt-4o --judge-override
"""

from arcade_core import ToolCatalog
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SmartCritic,
    SmartCriticMode,
    tool_eval,
)

import server_with_evaluations
from server_with_evaluations.tools import create_email_subject, write_product_description

# Tight rubric so we only pass when the LLM judge is genuinely confident.
rubric = EvalRubric(
    fail_threshold=0.80,
    warn_threshold=0.90,
)

catalog = ToolCatalog()
catalog.add_module(server_with_evaluations)


@tool_eval()
def server_with_evaluations_smart_critic_eval_suite() -> EvalSuite:
    """Evaluate text-heavy tools with an LLM judge.

    SmartCritic is especially useful when the model is expected to paraphrase
    the user's request into a tool argument — the exact wording varies, but
    a human (or LLM judge) can tell whether the meaning is preserved.
    """
    suite = EvalSuite(
        name="SmartCritic Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant for text analysis and content generation.",
        rubric=rubric,
    )

    # 1. Default mode (CORRECTNESS) — judge decides if the actual arg is
    # factually right compared to the expected ground truth. No per-critic
    # judge set, so it falls back to the eval's running model.
    suite.add_case(
        name="Email subject captures user intent (CORRECTNESS)",
        user_message=(
            "Draft an email subject line about trees in the west coast, "
            "keeping the tone professional."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_email_subject,
                args={
                    "email_content": "Trees in the West Coast",
                    "tone": "professional",
                },
            )
        ],
        critics=[
            SmartCritic(
                critic_field="email_content",
                weight=0.7,
                mode=SmartCriticMode.CORRECTNESS,
            ),
            SmartCritic(
                critic_field="tone",
                weight=0.3,
                mode=SmartCriticMode.SIMILARITY,
            ),
        ],
    )

    # 2. Similarity + per-critic judge override — useful for paraphrased
    # feature lists where you want a cheap-and-fast judge.
    suite.add_case(
        name="Product description preserves meaning (SIMILARITY)",
        user_message=(
            "Write a product description for a fitness tracker. Features: "
            "heart rate monitoring and GPS tracking. Target: outdoor enthusiasts."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=write_product_description,
                args={
                    "main_features": "heart rate monitoring and GPS tracking",
                    "target_audience": "outdoor enthusiasts",
                },
            )
        ],
        critics=[
            SmartCritic(
                critic_field="main_features",
                weight=0.6,
                mode=SmartCriticMode.SIMILARITY,
                # Per-critic judge model — uses a specific OpenAI model for
                # this particular field.
                judge_provider="openai",
                judge_model="gpt-4o-mini",
                match_threshold=0.75,
            ),
            SmartCritic(
                critic_field="target_audience",
                weight=0.4,
                mode=SmartCriticMode.RELEVANCE,
            ),
        ],
    )

    # 3. CUSTOM mode — you provide the criteria prompt yourself. Handy for
    # domain-specific checks that don't fit any of the built-in modes.
    suite.add_case(
        name="Email subject is concise and engaging (CUSTOM)",
        user_message="Create an email subject about our new product launch.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_email_subject,
                args={
                    "email_content": "New product launch",
                    "tone": "excited",
                },
            )
        ],
        critics=[
            SmartCritic(
                critic_field="email_content",
                weight=1.0,
                mode=SmartCriticMode.CUSTOM,
                criteria_prompt=(
                    "Rate whether the ACTUAL email_content value would make an "
                    "engaging, concise email subject line (under 8 words) "
                    "about roughly the same topic as the EXPECTED value. "
                    "Reward brevity and punchiness, penalize verbosity."
                ),
                match_threshold=0.7,
            ),
        ],
    )

    return suite
