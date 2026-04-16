"""Prompt templates and rubric definitions for :class:`SmartCritic`.

This module defines two styles of prompting:

* **Rubric style (default for built-in modes).** The judge LLM answers a
  fixed set of 3 positively-phrased sub-criteria with discrete values
  (``"yes"`` / ``"partial"`` / ``"no"``). The final score is computed
  deterministically in Python as a weighted sum, eliminating the "judge
  picks a number out of thin air" source of variance.

* **Legacy free-score style (for CUSTOM mode and user-overridden prompts).**
  The judge returns a single float in ``[0, 1]``. Less deterministic but
  more flexible — lets the user specify any criteria they want.

Rubric weights for each built-in mode sum to 1.0, so the final score is in
``[0.0, 1.0]`` before being multiplied by the critic's own ``resolved_weight``.
"""

from __future__ import annotations

from dataclasses import dataclass

from arcade_evals.smart_critic_mode import SmartCriticMode

# ---------------------------------------------------------------------------
# System + output-format prompts
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = (
    "You are an impartial evaluator grading tool-call arguments produced by "
    "an AI system. You compare an EXPECTED value (the ground truth the "
    "evaluator wrote) with an ACTUAL value (what the model produced). You "
    "answer with only a single JSON object — nothing outside it, no markdown "
    "fences, no commentary."
)

# Legacy-style output instructions (for CUSTOM mode or user overrides).
OUTPUT_FORMAT_INSTRUCTIONS = (
    "\n\nRespond with ONLY a JSON object in this exact shape:\n"
    '{"score": <float between 0.0 and 1.0>, "reasoning": "<one short sentence>"}\n'
    "Do not include any text before or after the JSON object. Do not wrap it "
    "in markdown code fences."
)

# Rubric-style output instructions — the criteria keys are injected by the
# caller so each mode can specify its own rubric.
RUBRIC_OUTPUT_FORMAT_TEMPLATE = (
    "\n\nFor each criterion below, answer ONLY with one of: "
    '"yes", "partial", or "no".\n\n'
    "{criteria_list}\n\n"
    "Respond with ONLY a JSON object in this exact shape:\n"
    '{{"criteria": {{{criteria_example}}}, "reasoning": "<one short sentence>"}}\n'
    "Do not include any text before or after the JSON object. Do not wrap it "
    "in markdown code fences."
)


# ---------------------------------------------------------------------------
# Rubric definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RubricCriterion:
    """A single sub-criterion the judge answers yes/partial/no on.

    Attributes:
        key: The JSON key the judge uses for this criterion (stable, snake_case).
        weight: Contribution to the final score in ``[0, 1]``. Rubric weights
            for a given mode must sum to 1.0.
        question: The actual question the judge answers. Must be positively
            phrased — "yes" should always mean "good".
    """

    key: str
    weight: float
    question: str


# Value map: yes/partial/no → numeric contribution.
RUBRIC_VALUE_MAP: dict[str, float] = {"yes": 1.0, "partial": 0.5, "no": 0.0}


# Each mode's rubric. Weights must sum to 1.0. All questions are
# positively-phrased so "yes" is always the good answer.
MODE_RUBRICS: dict[SmartCriticMode, tuple[RubricCriterion, ...]] = {
    SmartCriticMode.SIMILARITY: (
        RubricCriterion(
            key="same_core_meaning",
            weight=0.5,
            question=(
                "Does the ACTUAL value convey the same core meaning as the "
                "EXPECTED value? Ignore superficial formatting differences "
                "(case, whitespace, punctuation, word order)."
            ),
        ),
        RubricCriterion(
            key="no_contradiction",
            weight=0.3,
            question=(
                "Is the ACTUAL value free of any claim that contradicts the "
                "EXPECTED value? (For example, flipping a value to its "
                "opposite like hot → cold is a contradiction.)"
            ),
        ),
        RubricCriterion(
            key="same_key_entities",
            weight=0.2,
            question=(
                "Do the ACTUAL and EXPECTED values reference the same key "
                "entities, facts, or quantities?"
            ),
        ),
    ),
    SmartCriticMode.CORRECTNESS: (
        RubricCriterion(
            key="factually_accurate",
            weight=0.5,
            question=(
                "Is every factual claim in the ACTUAL value consistent with "
                "the EXPECTED value taken as ground truth?"
            ),
        ),
        RubricCriterion(
            key="key_claim_preserved",
            weight=0.3,
            question=("Does the ACTUAL value preserve the central claim of the " "EXPECTED value?"),
        ),
        RubricCriterion(
            key="no_fabricated_facts",
            weight=0.2,
            question=(
                "Is the ACTUAL value free of fabricated facts — claims not "
                "present in or derivable from the EXPECTED value?"
            ),
        ),
    ),
    SmartCriticMode.RELEVANCE: (
        RubricCriterion(
            key="same_topic",
            weight=0.5,
            question=(
                "Is the ACTUAL value about the same topic or domain as the " "EXPECTED value?"
            ),
        ),
        RubricCriterion(
            key="addresses_same_intent",
            weight=0.4,
            question=(
                "Does the ACTUAL value address the same user intent / "
                "question as the EXPECTED value?"
            ),
        ),
        RubricCriterion(
            key="free_of_off_topic",
            weight=0.1,
            question=(
                "Is the ACTUAL value free of off-topic content (material "
                "unrelated to the EXPECTED value)?"
            ),
        ),
    ),
    SmartCriticMode.COMPLETENESS: (
        RubricCriterion(
            key="covers_main_point",
            weight=0.5,
            question=("Does the ACTUAL value cover the main point of the EXPECTED " "value?"),
        ),
        RubricCriterion(
            key="covers_supporting_details",
            weight=0.3,
            question=(
                "Does the ACTUAL value cover the important supporting "
                "details present in the EXPECTED value?"
            ),
        ),
        RubricCriterion(
            key="no_critical_omissions",
            weight=0.2,
            question=(
                "Is the ACTUAL value free of critical omissions (no key "
                "piece of information from EXPECTED is missing)?"
            ),
        ),
    ),
    SmartCriticMode.COHERENCE: (
        RubricCriterion(
            key="internally_consistent",
            weight=0.4,
            question=(
                "Is the ACTUAL value internally consistent — no self-"
                "contradictions or conflicting statements within it?"
            ),
        ),
        RubricCriterion(
            key="logically_sound",
            weight=0.4,
            question=(
                "Is the ACTUAL value logically sound given the EXPECTED " "value as context?"
            ),
        ),
        RubricCriterion(
            key="clear_and_unambiguous",
            weight=0.2,
            question=("Is the ACTUAL value clear and unambiguous in its meaning?"),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Legacy free-score criteria (only used by CUSTOM mode now, and as a
# reference for anyone overriding criteria_prompt in a pre-rubric way).
# ---------------------------------------------------------------------------

_LEGACY_SIMILARITY = (
    "Rate how semantically similar the ACTUAL value is to the EXPECTED value. "
    "Use 1.0 for identical meaning, 0.0 for completely unrelated, and "
    "intermediate values for partial matches. Ignore superficial formatting "
    "differences (case, whitespace, punctuation)."
)
_LEGACY_CORRECTNESS = (
    "Rate how factually correct the ACTUAL value is compared to the EXPECTED "
    "ground truth. Use 1.0 for fully correct, 0.0 for completely wrong, and "
    "intermediate values when only part of the value is correct."
)
_LEGACY_RELEVANCE = (
    "Rate how relevant the ACTUAL value is to the EXPECTED topic/intent. Use "
    "1.0 for perfectly on-topic, 0.0 for totally off-topic, and intermediate "
    "values for tangentially related content."
)
_LEGACY_COMPLETENESS = (
    "Rate how completely the ACTUAL value covers the information present in "
    "the EXPECTED value. Use 1.0 when every important aspect is covered, 0.0 "
    "when nothing is covered, and intermediate values for partial coverage."
)
_LEGACY_COHERENCE = (
    "Rate the logical consistency, clarity, and internal coherence of the "
    "ACTUAL value. Use the EXPECTED value as a reference for the required "
    "level of coherence. Use 1.0 for fully coherent, 0.0 for incoherent."
)

# Kept exported for backward compatibility — tests that imported MODE_CRITERIA
# still work, and users who explicitly want the old free-score prompt can pass
# these through ``criteria_prompt=...``.
MODE_CRITERIA: dict[SmartCriticMode, str] = {
    SmartCriticMode.SIMILARITY: _LEGACY_SIMILARITY,
    SmartCriticMode.CORRECTNESS: _LEGACY_CORRECTNESS,
    SmartCriticMode.RELEVANCE: _LEGACY_RELEVANCE,
    SmartCriticMode.COMPLETENESS: _LEGACY_COMPLETENESS,
    SmartCriticMode.COHERENCE: _LEGACY_COHERENCE,
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_user_message(criteria: str, expected: object, actual: object) -> str:
    """Render the judge user message given a criteria block and the values.

    Used by both rubric and legacy prompt paths.
    """
    return f"{criteria}\n\nEXPECTED:\n{expected!r}\n\nACTUAL:\n{actual!r}"


def build_rubric_output_instructions(
    rubric: tuple[RubricCriterion, ...],
) -> str:
    """Render the rubric's output-format contract, inlining the criteria keys.

    The resulting instructions tell the judge exactly which JSON keys to emit
    and what values are allowed, which keeps the response format stable
    across model providers.
    """
    criteria_list = "\n".join(f"- `{c.key}` — {c.question}" for c in rubric)
    example_pairs = ", ".join(f'"{c.key}": "yes"|"partial"|"no"' for c in rubric)
    return RUBRIC_OUTPUT_FORMAT_TEMPLATE.format(
        criteria_list=criteria_list,
        criteria_example=example_pairs,
    )


def score_rubric_response(
    rubric: tuple[RubricCriterion, ...],
    criteria_values: dict[str, str],
) -> tuple[float, dict[str, float]]:
    """Aggregate a rubric response into a final score.

    Args:
        rubric: The rubric criteria (with weights) that the judge answered.
        criteria_values: Mapping from criterion key to one of
            ``"yes"``/``"partial"``/``"no"`` (or a synonym we can coerce).

    Returns:
        ``(final_score, breakdown)`` where ``final_score`` is the weighted
        sum in ``[0, 1]`` and ``breakdown`` is a per-criterion dict of
        numeric contributions. Missing or unparseable criteria are treated
        as ``"no"`` (0.0) — this is the safer default for judge evaluation
        because a missing answer shouldn't silently boost the score.
    """
    breakdown: dict[str, float] = {}
    total = 0.0
    for c in rubric:
        raw = criteria_values.get(c.key, "no")
        value = RUBRIC_VALUE_MAP.get(_normalize_rubric_value(raw), 0.0)
        contribution = value * c.weight
        breakdown[c.key] = contribution
        total += contribution
    # Guard against floating-point drift — weights should sum to 1.0 so
    # total should land in [0, 1].
    return max(0.0, min(1.0, total)), breakdown


def _normalize_rubric_value(raw: object) -> str:
    """Coerce common judge-output variants to our canonical yes/partial/no."""
    if not isinstance(raw, str):
        return "no"
    s = raw.strip().lower()
    # Accept a few common synonyms so one model saying "partially" doesn't
    # silently bucket as "no".
    if s in {"yes", "true", "y", "1"}:
        return "yes"
    if s in {"no", "false", "n", "0"}:
        return "no"
    if s in {"partial", "partially", "somewhat", "half", "maybe"}:
        return "partial"
    return s  # unknown — let caller fall back to "no" via missing-key path
