"""Optional quality review of existing eval cases, separate from execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from arcade_evals.errors import JudgeError
from arcade_evals.judge import JudgeBackend, JudgeVerdict, _checked_number
from arcade_evals.judge_group import JudgeCriticGroup

if TYPE_CHECKING:
    from arcade_evals.critic import Critic
    from arcade_evals.eval import EvalCase


def _critic_spec(critic: Critic) -> dict[str, Any]:
    """Only explicit grading configuration; never serialize a backend or its credentials."""
    spec = {"type": type(critic).__name__, "field": critic.critic_field}
    for name in ("instructions", "intent", "context", "match_threshold", "min_confidence"):
        if hasattr(critic, name):
            spec[name] = getattr(critic, name)
    if isinstance(critic, JudgeCriticGroup):
        spec["checks"] = [_critic_spec(member) for member in critic.critics]
    return spec


def build_quality_questions() -> dict[str, Any]:
    """Fresh rubrics; expected calls are labels, never additional model context."""
    return {
        "context": {
            "type": "score",
            "instructions": (
                "Can the expected tool calls be derived from system, user, additional_messages, "
                "and available tool definitions? additional_messages are prior conversation "
                "visible to the evaluated model. Expected calls are reference labels, not facts "
                "available to that model. A missing schema alone is not proof of bad context. "
                "No-call cases may be correct when abstention is required."
            ),
            "criteria": [
                "Essential facts are missing or the expected calls contradict the request",
                "Some required facts or constraints must be guessed",
                "All facts needed for the expected outcome are available",
            ],
        },
        "complexity": {
            "type": "choice",
            "instructions": (
                "Classify the work required. Choose adversarial for conflicting cues or "
                "distractors; otherwise complex for dependent reasoning, simple for light "
                "interpretation, and trivial for direct extraction. Complexity describes "
                "coverage, not quality: simple and adversarial cases can both be useful."
            ),
            "criteria": {
                "trivial": "Direct extraction with no inference",
                "simple": "One clear decision with light interpretation",
                "complex": "Multiple dependent steps or substantive reasoning",
                "adversarial": "Conflicting cues, distractors, or deliberate misleading content",
            },
        },
        "hint": {
            "type": "noul",
            "instructions": (
                "Does the request leak the intended answer or tool invocation, undermining "
                "the skill being tested? Evaluate leakage independently from missing context, "
                "ambiguity, contradictory prior context, template wording, or plausibility. "
                "Inspect only model-visible system, user, and additional_messages for leakage; "
                "expected calls are reference labels. Facts from system, user, or additional "
                "messages, including names, dates, IDs, and literal arguments needed to execute "
                "the request, are normal input rather than leakage. Mark leakage only when "
                "benchmark or answer framing gives away the decision or directs the model to "
                "reproduce an expected invocation."
            ),
            "criteria": {
                "true": "Gives away the decision or expected answer instead of testing it",
                "false": "Supplies legitimate inputs while leaving the intended decision to the model",
            },
        },
        "ambiguity": {
            "type": "score",
            "instructions": (
                "How much does the case permit competing valid outcomes that its expected "
                "calls and listed critics would incorrectly reject? Consider the supplied "
                "critic instructions, intent, and thresholds; paraphrases are not necessarily ambiguity "
                "when the critic accepts them. For a structured document or spreadsheet, expected "
                "fields, formulas, and styles are labels rather than visible facts unless system, user, "
                "additional_messages, tool definitions, or critic guidance makes them required."
            ),
            "criteria": [
                "Clear expected behavior; reasonable alternatives are accepted",
                "Some underspecification could reject a valid outcome",
                "Contradictory or underspecified; substantially different outcomes are equally valid",
            ],
        },
        "human": {
            "type": "noul",
            "instructions": (
                "Does the user request read like a plausible request in this domain? "
                "Technical language, IDs, typos, and short wording can be natural. "
                "Judge realism in context, not grammar or the presence of machine identifiers."
            ),
            "criteria": {
                "true": "Plausible user request for this task and audience",
                "false": "Unfilled placeholders, benchmark boilerplate, or implausible phrasing",
            },
        },
    }


@dataclass
class CaseQualityReport:
    """Quality-gate decision with per-dimension scores, categories, and provenance."""

    passed: bool
    reasons: list[str]
    verdicts: dict[str, JudgeVerdict]


@dataclass
class CaseQualityGrader:
    """Opt-in quality gate; accepts any JudgeBackend and never runs the eval.

    Thresholds are starting policies, not calibrated accuracy guarantees.
    Backend errors or incomplete answers raise JudgeError instead of inventing
    judgments. Complexity is descriptive unless fail_on_trivial is enabled.
    """

    backend: JudgeBackend
    min_context: float = 0.6
    max_hint: float = 0.6
    max_ambiguity: float = 0.4
    min_human: float = 0.5
    fail_on_trivial: bool = False

    def __post_init__(self) -> None:
        for name in ("min_context", "max_hint", "max_ambiguity", "min_human"):
            try:
                setattr(self, name, _checked_number(getattr(self, name), name, 0.0, 1.0))
            except JudgeError:
                raise ValueError(f"{name} must be a finite number between 0.0 and 1.0.") from None

    def grade(
        self, case: EvalCase, *, tools: list[dict[str, Any]] | None = None
    ) -> CaseQualityReport:
        state = {
            "system": case.system_message,
            "user": case.user_message,
            "additional_messages": case.additional_messages,
            "expected": [
                {"name": call.name, "args": call.args} for call in case.expected_tool_calls
            ],
            "tools": tools or [],
            "critics": [_critic_spec(critic) for critic in case.critics or []],
        }
        questions = build_quality_questions()
        try:
            verdicts = self.backend.judge(state=state, questions=questions)
        except JudgeError:
            raise JudgeError("Case quality judge unavailable.") from None
        if not isinstance(verdicts, dict) or any(
            not isinstance(verdicts.get(qid), JudgeVerdict) for qid in questions
        ):
            raise JudgeError("Case quality judge returned incomplete or invalid answers.")
        choice = verdicts["complexity"]
        if (
            choice.score is not None
            or not isinstance(choice.label, str)
            or choice.label not in questions["complexity"]["criteria"]
        ):
            raise JudgeError("Case quality judge returned an invalid complexity category.")

        reasons = []
        checked = {"complexity": choice}
        for qid, minimum, maximum in (
            ("context", self.min_context, 1.0),
            ("hint", 0.0, self.max_hint),
            ("ambiguity", 0.0, self.max_ambiguity),
            ("human", self.min_human, 1.0),
        ):
            verdict = verdicts[qid]
            if verdict.label is not None:
                raise JudgeError("Case quality judge returned a category for a numeric question.")
            score = _checked_number(verdict.score, qid, 0.0, 1.0)
            checked[qid] = replace(verdict, score=score)
            if not minimum <= score <= maximum:
                reasons.append(
                    f"{qid}: {score:.2f} outside allowed range {minimum:.2f}..{maximum:.2f}"
                )
        if self.fail_on_trivial and choice.label == "trivial":
            reasons.append("complexity: trivial cases are excluded by policy")
        return CaseQualityReport(passed=not reasons, reasons=reasons, verdicts=checked)
