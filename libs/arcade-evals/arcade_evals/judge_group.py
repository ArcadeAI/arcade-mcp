"""Explicit batching of several judgments about one tool argument."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from arcade_evals.critic import Critic, JudgeCriticBase
from arcade_evals.errors import JudgeError
from arcade_evals.judge import JudgeBackend, JudgeScope, JudgeVerdict


@dataclass
class JudgeCriticGroup(Critic):
    """One request, independent judgments, and one normal Arcade critic result.

    Members must target this group's argument and must not configure their own
    provider, backend, or fallback. Their weights are relative; the group's weight
    participates in Arcade's existing aggregation. Unavailable, incomplete, or
    low-confidence answers return status="unavailable" or "low_confidence" with zero
    credit; there is no lexical fallback. Like individual judge critics, instances
    are not thread-safe.

    judge_calls_total and judge_latency_ms_total are lifetime counters; each result's
    judge_calls and judge_latency_ms describe only that evaluation.
    """

    critics: list[JudgeCriticBase]
    backend: JudgeBackend
    instructions: str = field(default="", kw_only=True)
    context: Any = field(default=None, kw_only=True)
    judge_calls_total: int = field(default=0, init=False)
    judge_latency_ms_total: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self._weights()

    def _weights(self) -> list[float]:
        if not self.critics:
            raise ValueError("A judge group needs at least one critic.")
        weights = []
        for critic in self.critics:
            if not isinstance(critic, JudgeCriticBase) or critic.critic_field != self.critic_field:
                raise ValueError("Group members must be judge critics targeting the group's field.")
            if (
                critic.backend is not None
                or critic.provider is not None
                or critic.llm_model is not None
            ):
                raise ValueError("Configure the backend on the group, not on its members.")
            if critic.fallback != "none":
                raise ValueError("Group members cannot use fallback; the group fails closed.")
            weight = critic.resolved_weight
            if not math.isfinite(weight) or weight < 0:
                raise ValueError("Group member weights must be finite and non-negative.")
            weights.append(weight)
        total = sum(weights)
        if not math.isfinite(total) or total <= 0:
            raise ValueError("Group member weights must have a finite, positive total.")
        return [weight / total for weight in weights]

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
        return self.evaluate_in_scope(expected, actual)

    def evaluate_in_scope(
        self, expected: Any, actual: Any, scope: JudgeScope | None = None
    ) -> dict[str, Any]:
        weights = self._weights()
        state, questions = self._prepare(expected, actual)
        calls_before = self.judge_calls_total
        latency_before = self.judge_latency_ms_total
        abstained = expected is None and actual is None
        if abstained:
            verdicts: Any = {qid: JudgeVerdict(1.0, None, "none") for qid in questions}
        else:
            if scope is not None:
                state["scope"] = scope.as_state()
            self.judge_calls_total += 1
            started = time.perf_counter()
            try:
                verdicts = self.backend.judge(state=state, questions=questions)
            except Exception:
                verdicts = None
            finally:
                self.judge_latency_ms_total += (time.perf_counter() - started) * 1000.0
        details = []
        withheld = None
        for index, (critic, weight) in enumerate(zip(self.critics, weights)):
            qid = f"check_{index}"
            raw = verdicts.get(qid) if isinstance(verdicts, dict) else None
            status = "missing" if isinstance(verdicts, dict) and qid not in verdicts else "invalid"
            if not isinstance(verdicts, dict):
                status = "unavailable"
            verdict = None
            try:
                verdict = critic._checked_verdict(raw)
                status = (
                    "low_confidence"
                    if verdict.confidence is not None and verdict.confidence < critic.min_confidence
                    else "ok"
                )
            except JudgeError:
                pass
            # Missing/invalid answers take priority over uncertainty.
            if status != "ok" and (
                withheld is None or status in ("unavailable", "missing", "invalid")
            ):
                withheld = "low_confidence" if status == "low_confidence" else "unavailable"
            contribution = weight * self.resolved_weight
            details.append({
                "question_id": qid,
                "critic": type(critic).__name__,
                "status": "abstained" if abstained else status,
                "match": status == "ok"
                and verdict is not None
                and verdict.score is not None
                and verdict.score >= critic.match_threshold,
                "score": verdict.score * contribution
                if status == "ok" and verdict is not None and verdict.score is not None
                else 0.0,
                "weight": contribution,
                "confidence": verdict.confidence if verdict is not None else None,
                "backend": verdict.backend if verdict is not None else "unavailable",
                "model": verdict.model if verdict is not None else "",
                "evidence": dict(raw.raw)
                if isinstance(raw, JudgeVerdict) and isinstance(raw.raw, dict)
                else {},
                "diagnostic_score": verdict.score if verdict is not None else None,
            })
        if withheld is not None:
            # Preserve diagnostic evidence but give no credited contribution.
            for detail in details:
                detail["score"] = 0.0
                detail["match"] = False
            return self._withheld(withheld, calls_before, latency_before, details)
        backends = {item["backend"] for item in details}
        models = {item["model"] for item in details}
        return {
            "status": "abstained" if abstained else "ok",
            "judged": not abstained,
            "match": all(item["match"] for item in details),
            "score": sum(item["score"] for item in details),
            "confidence": None,
            "backend": next(iter(backends)) if len(backends) == 1 else "mixed",
            "model": next(iter(models)) if len(models) == 1 else "mixed",
            "details": details,
            "judge_calls": self.judge_calls_total - calls_before,
            "judge_latency_ms": self.judge_latency_ms_total - latency_before,
        }

    def _withheld(
        self, status: str, calls_before: int, latency_before: float, details: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "status": status,
            "judged": False,
            "match": False,
            "score": 0.0,
            "confidence": None,
            "backend": "withheld",
            "model": "",
            "details": details,
            "judge_calls": self.judge_calls_total - calls_before,
            "judge_latency_ms": self.judge_latency_ms_total - latency_before,
        }
