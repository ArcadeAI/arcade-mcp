"""Explicit batching of several judgments about one tool argument."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from arcade_evals.critic import Critic, JudgeCriticBase
from arcade_evals.errors import JudgeError
from arcade_evals.judge import JudgeBackend, JudgeVerdict


@dataclass
class JudgeCriticGroup(Critic):
    """One request, independent judgments, and one normal Arcade critic result.

    Members must target this group's argument. Their weights are relative;
    the group's weight participates in Arcade's existing aggregation. The
    explicit backend belongs to the group, not its members. Errors, incomplete
    answers, and low confidence return status="unavailable" with zero credit;
    there is no lexical fallback. This preserves the group's weight when
    Arcade aggregates results, without claiming a failed semantic judgment.
    Like individual judge critics, instances are not thread-safe.
    """

    critics: list[JudgeCriticBase]
    backend: JudgeBackend
    instructions: str = field(default="", kw_only=True)
    context: Any = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        super().__post_init__()
        self._weights()
        self._cache: dict[str, dict[str, JudgeVerdict]] = {}
        self._calls = 0
        self._latency_ms = 0.0
        self._cache_backend = self.backend

    def _weights(self) -> list[float]:
        if not self.critics:
            raise ValueError("A judge group needs at least one critic.")
        weights = []
        for critic in self.critics:
            if not isinstance(critic, JudgeCriticBase) or critic.critic_field != self.critic_field:
                raise ValueError("Group members must be judge critics targeting the group's field.")
            if critic.backend is not None or critic.llm_model is not None:
                raise ValueError("Configure the backend on the group, not on its members.")
            weight = critic.resolved_weight
            if not math.isfinite(weight) or weight < 0:
                raise ValueError("Group member weights must be finite and non-negative.")
            weights.append(weight)
        total = sum(weights)
        if not math.isfinite(total) or total <= 0:
            raise ValueError("Group member weights must have a finite, positive total.")
        return [weight / total for weight in weights]

    def clear_cache(self) -> None:
        """Clear batch verdicts after backend recovery or an in-place backend change."""
        self._cache.clear()
        self._cache_backend = self.backend

    def _prepare(self, expected: Any, actual: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        checks = {}
        questions = {}
        shared = {"expected": expected, "actual": actual}
        for index, critic in enumerate(self.critics):
            qid = f"check_{index}"
            state, member_questions = critic._prepare(expected, actual)
            if set(member_questions) != {critic.question_id}:
                raise ValueError("Each group member must define exactly one question.")
            # Large expected/actual payloads are sent once, shared by all checks.
            checks[qid] = {
                key: value
                for key, value in state.items()
                if key not in shared or value is not shared[key]
            }
            question = member_questions[critic.question_id]
            instructions = (
                f"For `expected` and `actual`, use the field in `checks.{qid}` if present, "
                "otherwise the shared field. Use the shared `context` "
                f"and `checks.{qid}` for this question's additional evidence. "
                "Do not use other checks' evidence.\n\n"
                f"{question.get('instructions', '')}"
            )
            if self.instructions:
                instructions += f"\n\nGroup requirements:\n{self.instructions}"
            questions[qid] = {**question, "instructions": instructions}
        return {
            "expected": expected,
            "actual": actual,
            "context": self.context,
            "checks": checks,
        }, questions

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        try:
            return self._evaluate(expected, actual)
        except JudgeError:
            # Arcade drops the failed critic's weight when it catches an
            # exception. Return an explicit unavailable result to retain it.
            return self._unavailable()

    def _unavailable(self, *, cache_hit: bool = False) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "match": False,
            "score": 0.0,
            "confidence": None,
            "backend": "unavailable",
            "model": "",
            "details": [],
            "error": "Judge group unavailable, incomplete, or below required confidence.",
            "cache_hit": cache_hit,
            "judge_calls": {"jev": 0, "llm": 0, "explicit": self._calls},
            "judge_latency_ms": self._latency_ms,
        }

    def _evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        weights = self._weights()
        if self.backend is not self._cache_backend:
            self.clear_cache()
        state, questions = self._prepare(expected, actual)
        key = repr((state, questions))
        verdicts = self._cache.get(key)
        cache_hit = verdicts is not None
        if expected is None and actual is None:
            verdicts = {qid: JudgeVerdict(1.0, None, "none") for qid in questions}
        elif verdicts is None:
            self._calls += 1
            started = time.perf_counter()
            try:
                verdicts = self.backend.judge(state=state, questions=questions)
            except JudgeError:
                raise JudgeError("Judge group unavailable.") from None
            finally:
                self._latency_ms += (time.perf_counter() - started) * 1000.0

        if not isinstance(verdicts, dict):
            raise JudgeError("Judge group returned invalid answers.")
        checked = {
            f"check_{index}": critic._checked_verdict(verdicts.get(f"check_{index}"))
            for index, critic in enumerate(self.critics)
        }
        # Cache valid evidence before applying policy. Repeating an uncertain
        # judgment during assignment/final scoring adds cost, not confidence.
        if expected is not None or actual is not None:
            self._cache[key] = checked
        if any(
            checked[f"check_{index}"].confidence is not None
            and checked[f"check_{index}"].confidence < critic.min_confidence
            for index, critic in enumerate(self.critics)
        ):
            return self._unavailable(cache_hit=cache_hit)
        details = []
        for index, (critic, weight) in enumerate(zip(self.critics, weights)):
            qid = f"check_{index}"
            verdict = checked[qid]
            contribution = weight * self.resolved_weight
            details.append({
                "question_id": qid,
                "critic": type(critic).__name__,
                "match": verdict.score >= critic.match_threshold,
                "score": verdict.score * contribution,
                "weight": contribution,
                "confidence": verdict.confidence,
                "backend": verdict.backend,
                "model": verdict.model,
            })
        backends = {item["backend"] for item in details}
        models = {item["model"] for item in details}
        return {
            "status": "ok",
            "match": all(item["match"] for item in details),
            "score": sum(item["score"] for item in details),
            "confidence": None,  # No fabricated confidence for a composite judgment.
            "backend": next(iter(backends)) if len(backends) == 1 else "mixed",
            "model": next(iter(models)) if len(models) == 1 else "mixed",
            "details": details,
            "cache_hit": cache_hit,
            "judge_calls": {"jev": 0, "llm": 0, "explicit": self._calls},
            "judge_latency_ms": self._latency_ms,
        }
