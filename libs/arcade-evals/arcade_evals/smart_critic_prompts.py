"""Prompt templates and rubric definitions for :class:`SmartCritic`.

Two prompt styles, one per mode family:

* **Rubric style (every built-in mode).** The judge answers a fixed set
  of 3 positively-phrased sub-criteria with discrete values
  (``"yes"`` / ``"partial"`` / ``"no"``). The final score is computed
  deterministically in Python as a weighted sum, eliminating the "judge
  picks a number out of thin air" source of variance. Each mode's
  rubric weights sum to 1.0, so the unweighted score lies in
  ``[0.0, 1.0]`` before being scaled by the critic's own weight.

* **Free-score style (CUSTOM mode only).** When the user supplies their
  own criteria via ``criteria_prompt``, the judge returns a single float
  in ``[0, 1]`` because arbitrary user criteria don't map to a fixed
  rubric. Less deterministic than rubric mode, but flexible.
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

# Output instructions for CUSTOM mode — the one remaining free-score path.
CUSTOM_OUTPUT_FORMAT_INSTRUCTIONS = (
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


# No per-mode free-score prompts remain: built-in modes always use the
# rubric. The only free-score path is `CUSTOM` mode, where the user
# supplies the criteria text via ``SmartCritic.criteria_prompt``.


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_user_message(criteria: str, expected: object, actual: object) -> str:
    """Render the judge user message given a criteria block and the values.

    Used by both rubric and CUSTOM-mode prompt paths.
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
    """Coerce common judge-output variants to our canonical yes/partial/no.

    Handles:
    * ``"yes"`` / ``"no"`` / ``"partial"`` (canonical)
    * JSON booleans — some models emit ``true`` / ``false`` despite the
      prompt asking for strings. Without this branch, ``json.loads`` turns
      those into Python ``bool`` and every criterion silently scores 0.
    * Synonyms like ``"partially"``, ``"somewhat"``, ``"maybe"``.
    * Numeric ``1`` / ``0`` (handled via the string-cast branch).
    """
    # bool must be checked BEFORE str, because bool is a subclass of int
    # (so ``True`` is falsy under ``isinstance(x, str)`` but passes any
    # numeric cast). Judges occasionally return `{"key": true}`.
    if isinstance(raw, bool):
        return "yes" if raw else "no"
    if isinstance(raw, (int, float)):
        # 1 → yes, 0 → no, anything else → partial (0 < x < 1) or no.
        if raw >= 1:
            return "yes"
        if raw <= 0:
            return "no"
        return "partial"
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
