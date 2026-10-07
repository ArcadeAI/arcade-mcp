import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import timedelta
from typing import Any, ClassVar

import pytz
from dateutil import parser

from arcade_evals.errors import JudgeError, WeightError
from arcade_evals.judge import (
    JevBackend,
    JudgeBackend,
    JudgeVerdict,
    LLMFallbackBackend,
    _checked_number,
)
from arcade_evals.weights import FuzzyWeight, Weight, resolve_weight

logger = logging.getLogger(__name__)


@dataclass
class Critic(ABC):
    """
    Base class for all critics.

    Attributes:
        critic_field: The field name this critic evaluates.
        weight: The weight for this critic. Can be a float (0.0-1.0) or FuzzyWeight enum.
                When using FuzzyWeight, weights are auto-normalized to sum to 1.0.
    """

    critic_field: str
    weight: Weight

    def __post_init__(self) -> None:
        if isinstance(self.weight, FuzzyWeight):
            return

        if self.weight < 0:
            raise WeightError(f"Critic weight must be non-negative, got {self.weight}")

    @property
    def resolved_weight(self) -> float:
        """Get the weight as a float value."""
        return resolve_weight(self.weight)

    @abstractmethod
    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        pass


@dataclass
class NoneCritic(Critic):
    """
    A critic that has no effect on the evaluation results and does not actually evaluate.

    If a critic is not found for an evaluation case's field, then
    a NoneCritic is used to indicate that the field was not criticized.
    """

    # Marker attribute to identify placeholder critics without isinstance checks
    # (avoids circular imports in weights.py)
    _is_placeholder: ClassVar[bool] = True

    weight: float = 0.0

    def __post_init__(self) -> None:
        self.weight = 0.0
        super().__post_init__()

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {"match": None, "score": self.weight, "is_criticized": False}


@dataclass
class BinaryCritic(Critic):
    """
    A critic for performing exact equality comparisons between expected and actual values.

    This critic evaluates whether the expected and actual values are exactly equal.
    It's useful for scenarios where only an exact match is acceptable.

    Returns:
        A dict with:
            - "match": True if expected == actual, otherwise False.
            - "score": The full weight if there's a match, otherwise 0.0.
    """

    def cast_actual(self, expected: Any, actual: Any) -> Any:
        """
        Casts the actual value to the type of the expected value.

        Args:
            expected (Any): The expected value whose type will be used for casting.
            actual (Any): The actual value to be cast.

        Returns:
            Any: The actual value cast to the type of the expected value.

        Raises:
            TypeError: If the casting is not possible.
        """
        # In case both are strings.
        if actual == "None":
            actual = None
        if expected == "None":
            expected = None
        if expected is None:
            # No need to cast; return actual as is
            return actual
        if actual is None:
            # No need to cast; return None
            return None
        expected_type = type(expected)
        try:
            return expected_type(actual)
        except (ValueError, TypeError) as e:
            raise TypeError(
                f"Cannot cast actual value '{actual}' to type {expected_type.__name__}: {e}"
            ) from e

    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Evaluates whether the expected and actual values are exactly equal after casting.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        # Cast actual to the type of expected
        try:
            actual_casted = self.cast_actual(expected, actual)
        # TODO log or something better here
        except TypeError:
            actual_casted = actual

        match = expected == actual_casted
        return {"match": match, "score": self.resolved_weight if match else 0.0}


@dataclass
class NumericCritic(Critic):
    """
    A critic for evaluating numeric values within a specified range.

    This critic performs a "fuzzy" comparison of numeric values, where values closer
    to each other (relative to the specified range) result in higher scores. It's
    useful for scenarios where exact matches aren't necessary, but closeness within
    a certain tolerance is rewarded.

    Attributes:
        value_range: The min and max values of the expected range.
        match_threshold: The threshold for considering a match (default 0.8).

    The evaluation process:
    1. Normalizes both expected and actual values to a 0-1 scale based on value_range.
    2. Calculates the absolute difference between these normalized values.
    3. Subtracts this difference from 1 to get a similarity score (closer to 1 is more similar).
    4. Multiplies the similarity by the critic's weight for the final score.

    Returns:
        A dict with:
            - "match": True if the score >= match_threshold, otherwise False.
            - "score": The calculated score (similarity * weight).
    """

    value_range: tuple[float, float]
    match_threshold: float = 0.8

    def __init__(
        self,
        critic_field: str,
        weight: float,
        value_range: tuple[float, float],
        match_threshold: float = 0.8,
    ):
        super().__init__(critic_field, weight)
        if value_range[0] >= value_range[1]:
            raise ValueError("Invalid value_range: minimum must be less than maximum.")
        self.value_range = value_range
        self.match_threshold = match_threshold

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        min_val, max_val = self.value_range
        normalized_expected = float((float(expected) - min_val) / (max_val - min_val))
        normalized_actual = float((float(actual) - min_val) / (max_val - min_val))
        score = float(1 - abs(normalized_expected - normalized_actual))
        return {
            "match": bool(score >= self.match_threshold),
            "score": float(score * self.resolved_weight),
        }


@dataclass
class SimilarityCritic(Critic):
    """
    A critic for evaluating the similarity between two strings.

    This critic uses a specified similarity metric to compare the expected and actual
    string values. Currently, it supports cosine similarity using TF-IDF vectorization.

    Args:
        metric: The similarity metric to use (default is "cosine").
        similarity_threshold: The threshold for considering a match (default 0.8).

    The evaluation process:
    1. Converts both expected and actual values to strings.
    2. Calculates the similarity score using the specified metric.
    3. Determines a match based on the similarity_threshold.
    4. Calculates the final score by multiplying the similarity by the critic's weight.

    Returns:
        A dict with:
            - "match": True if similarity >= similarity_threshold, otherwise False.
            - "score": The calculated score (similarity * weight).

    Raises:
        ImportError: If scikit-learn is not installed (required for cosine similarity).
        ValueError: If an unsupported similarity metric is specified.
    """

    metric: str = "cosine"
    similarity_threshold: float = 0.8

    SUPPORTED_METRICS: ClassVar[list[str]] = ["cosine"]

    def __init__(
        self,
        critic_field: str,
        weight: float,
        similarity_threshold: float = 0.8,
        metric: str = "cosine",
    ):
        super().__init__(critic_field, weight)
        if metric not in self.SUPPORTED_METRICS:
            raise ValueError(f"Unsupported similarity metric: {metric}")
        self.similarity_threshold = similarity_threshold
        self.metric = metric

    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        # IMPORTANT: Convert non-string values to strings before TF-IDF comparison.
        # sklearn's TfidfVectorizer calls .lower() on inputs, which fails on lists/dicts.
        # This commonly occurs when SimilarityCritic is used for tool arguments that are
        # lists (e.g., teams_to_add=["Engineering", "Platform"]) instead of strings.
        # Lists are joined with spaces to create comparable text representations.
        if not isinstance(expected, str):
            expected = (
                " ".join(str(item) for item in expected)
                if isinstance(expected, list)
                else str(expected)
            )
        if not isinstance(actual, str):
            actual = (
                " ".join(str(item) for item in actual) if isinstance(actual, list) else str(actual)
            )

        if self.metric == "cosine":
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
            except ImportError:
                raise ImportError(
                    "Use `pip install 'arcade-evals` to install the required dependencies for similarity metrics."
                )

            # Handle edge case: empty strings or strings with no valid tokens
            # TfidfVectorizer fails with "empty vocabulary" for such inputs
            if not expected.strip() or not actual.strip():
                # Both empty = match, one empty = no match
                is_match = expected.strip() == actual.strip()
                return {
                    "match": is_match,
                    "score": self.resolved_weight if is_match else 0.0,
                }

            try:
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform([expected, actual])
                similarity = float(cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0])
            except ValueError:
                # TfidfVectorizer raises ValueError for empty vocabulary
                # (e.g., only numbers/punctuation which get filtered as stop words)
                # Fall back to exact string match
                is_match = expected == actual
                return {
                    "match": is_match,
                    "score": self.resolved_weight if is_match else 0.0,
                }
        else:
            raise ValueError(f"Unsupported similarity metric: {self.metric}")
        return {
            "match": similarity >= self.similarity_threshold,
            "score": min(similarity * self.resolved_weight, self.resolved_weight),
        }


@dataclass
class DatetimeCritic(Critic):
    """
    A critic that evaluates the closeness of datetime values within a specified tolerance.

    Attributes:
        tolerance: Acceptable timedelta between expected and actual datetimes.
        max_difference: Maximum timedelta for a partial score.
    """

    critic_field: str
    weight: float
    tolerance: timedelta = timedelta(seconds=500)
    max_difference: timedelta = timedelta(hours=2)

    def evaluate(self, expected: str, actual: str) -> dict[str, float | bool]:
        """Evaluates the closeness of datetime values within a specified tolerance."""

        # Attempt to parse expected and actual datetime strings
        try:
            expected_dt = parser.parse(expected)
            actual_dt = parser.parse(actual)
        except (ValueError, TypeError):
            # If parsing fails, return score 0
            return {"match": False, "score": 0.0}

        # Handle cases based on presence of tzinfo
        if expected_dt.tzinfo is None and actual_dt.tzinfo is None:
            # Both datetimes are naive, compare directly
            time_diff_seconds = abs((expected_dt - actual_dt).total_seconds())
        elif expected_dt.tzinfo is not None and actual_dt.tzinfo is not None:
            # Both datetimes have tzinfo, compare in UTC
            expected_utc = expected_dt.astimezone(pytz.utc)
            actual_utc = actual_dt.astimezone(pytz.utc)
            time_diff_seconds = abs((expected_utc - actual_utc).total_seconds())
        else:
            # One datetime has tzinfo and the other doesn't
            # Compare naive datetime with the other's naive equivalent
            if expected_dt.tzinfo is not None:
                expected_naive = expected_dt.replace(tzinfo=None)
                time_diff_seconds = abs((expected_naive - actual_dt).total_seconds())
            else:
                actual_naive = actual_dt.replace(tzinfo=None)
                time_diff_seconds = abs((expected_dt - actual_naive).total_seconds())

        # Convert tolerances to seconds
        tolerance_seconds = self.tolerance.total_seconds()
        max_difference_seconds = self.max_difference.total_seconds()

        if time_diff_seconds <= tolerance_seconds:
            # Full score if within tolerance
            return {"match": True, "score": self.resolved_weight}
        elif time_diff_seconds >= max_difference_seconds:
            # No score if beyond max_difference
            return {"match": False, "score": 0.0}
        else:
            # Partial score based on time difference
            ratio = 1 - (time_diff_seconds / max_difference_seconds)
            # Ensure ratio is not negative
            ratio = max(ratio, 0)
            score = self.resolved_weight * ratio
            return {"match": False, "score": score}


@dataclass
class JudgeCriticBase(Critic, ABC):
    """
    Shared chain for judge critics: explicit backend, else Jev (key required),
    else LLM (only when llm_model is set), always ending in a local tier.

    Stays synchronous so EvalCase.evaluate() works unchanged. Extra result keys
    (confidence, backend, model) flow into EvaluationResult for auditability.

    Attributes:
        match_threshold: Minimum normalized score (0.0-1.0) for a match.
        min_confidence: Below this real confidence (Jev Score only) the verdict
            escalates to the next tier. None confidence is accepted as judged.
        backend: Explicit JudgeBackend (tests, custom judges). Skips auto tiers.
        judge_model: Jev model alias for the Jev tier.
        llm_model: Enables the LLM tier when set (e.g. "gpt-4o-mini").
        instructions: Application-provided guidance appended to this critic's rubric.
        context: Optional JSON evidence, such as the original document or scenario messages.
    """

    match_threshold: float = 0.7
    min_confidence: float = 0.5
    backend: JudgeBackend | None = None
    judge_model: str = "jev-latest"
    llm_model: str | None = None
    instructions: str = field(default="", kw_only=True)
    context: Any = field(default=None, kw_only=True)

    #: Set by concrete critics; selects their answer from a multi-question response.
    question_id: ClassVar[str]

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("match_threshold", "min_confidence"):
            try:
                setattr(self, name, _checked_number(getattr(self, name), name, 0.0, 1.0))
            except JudgeError:
                raise ValueError(f"{name} must be a finite number between 0.0 and 1.0.") from None
        self._cache: dict[tuple[str, str, str, str], JudgeVerdict] = {}
        self._judge_calls = {"jev": 0, "llm": 0, "explicit": 0}
        self._judge_latency_ms = 0.0
        self.clear_cache()

    def clear_cache(self) -> None:
        """Discard verdicts, e.g. after backend recovery or an in-place backend change.

        Calls are synchronous, so one event loop's concurrent EvalSuite cases
        cannot interleave a lookup and its fill. Instances are not thread-safe.
        """
        self._cache.clear()
        self._cache_backend = self.backend
        self._cache_config = (self.judge_model, self.llm_model, self.min_confidence)

    @abstractmethod
    def build_state(self, expected: Any, actual: Any) -> dict[str, Any]:
        """State sent to the judge (JSON-serializable; values pass through raw)."""

    @abstractmethod
    def build_questions(self, expected: Any, actual: Any) -> dict[str, Any]:
        """Typed judge questions keyed by id (must include self.question_id)."""

    def _prepare(self, expected: Any, actual: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        """Combine the built-in rubric with trusted guidance and untrusted context."""
        state = dict(self.build_state(expected, actual))
        if self.context is not None:
            state["context"] = self.context
        questions = self.build_questions(expected, actual)
        if self.instructions:
            questions = {
                qid: {
                    **question,
                    "instructions": (
                        f"{question.get('instructions', '')}\n\n"
                        f"Additional evaluation requirements:\n{self.instructions}"
                    ),
                }
                for qid, question in questions.items()
            }
        return state, questions

    def _diagnostics(self, cache_hit: bool) -> dict[str, Any]:
        """Snapshot lifetime backend work, including assignment-stage judgments."""
        return {
            "cache_hit": cache_hit,
            "judge_calls": dict(self._judge_calls),
            "judge_latency_ms": self._judge_latency_ms,
        }

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        if expected is None and actual is None:
            return {
                "match": True,
                "score": self.resolved_weight,
                "confidence": None,
                "backend": "none",
                "model": "",
                **self._diagnostics(cache_hit=False),
            }
        config = (self.judge_model, self.llm_model, self.min_confidence)
        if self.backend is not self._cache_backend or config != self._cache_config:
            self.clear_cache()
        state, questions = self._prepare(expected, actual)
        key = (
            type(self).__name__,
            self.critic_field,
            repr(state),
            repr(questions),
        )
        verdict = self._cache.get(key)
        cache_hit = verdict is not None
        if verdict is None:
            verdict = self._run_chain(state, questions)
            self._cache[key] = verdict
        match = verdict.score >= self.match_threshold
        return {
            "match": match,
            "score": min(verdict.score, 1.0) * self.resolved_weight,
            "confidence": verdict.confidence,
            "backend": verdict.backend,
            "model": verdict.model,
            **self._diagnostics(cache_hit),
        }

    def _run_chain(self, state: dict[str, Any], questions: dict[str, Any]) -> JudgeVerdict:
        tiers = self._tiers()
        for index, (name, tier) in enumerate(tiers):
            started = None
            if name in self._judge_calls:
                self._judge_calls[name] += 1
                started = time.perf_counter()
            try:
                verdict = self._ask(tier, state, questions)
            except JudgeError:
                # A custom backend can include credentials in its exception text.
                logger.warning("Judge tier '%s' failed; trying the next tier.", name)
                continue
            finally:
                if started is not None:
                    self._judge_latency_ms += (time.perf_counter() - started) * 1000.0
            if (
                verdict.confidence is not None
                and verdict.confidence < self.min_confidence
                and index < len(tiers) - 1
            ):
                continue
            return verdict
        raise JudgeError("All judge tiers failed.")

    def _tiers(self) -> list[tuple[str, Any]]:
        if self.backend is not None:
            return [("explicit", self.backend), ("deterministic", "deterministic")]
        tiers: list[tuple[str, Any]] = []
        try:
            tiers.append(("jev", JevBackend(model=self.judge_model)))
        except JudgeError:
            logger.debug("Jev unavailable (no API key); skipping Jev tier.")
        if self.llm_model is not None:
            tiers.append(("llm", LLMFallbackBackend(model=self.llm_model)))
        tiers.append(("deterministic", "deterministic"))
        return tiers

    def _deterministic_score(self, expected: Any, actual: Any) -> float:
        """Last-resort local score (0.0-1.0). Default is TF-IDF cosine overlap;
        critics whose semantics it cannot approximate must override."""
        fallback = SimilarityCritic(
            critic_field=self.critic_field,
            weight=1.0,
            similarity_threshold=self.match_threshold,
        )
        return float(fallback.evaluate(expected, actual)["score"])

    def _ask(self, tier: Any, state: dict[str, Any], questions: dict[str, Any]) -> JudgeVerdict:
        if tier == "deterministic":
            score = self._deterministic_score(state.get("expected"), state.get("actual"))
            return JudgeVerdict(
                score=score, confidence=None, backend="deterministic", model="deterministic"
            )
        verdicts = tier.judge(state=state, questions=questions)
        try:
            verdict = verdicts[self.question_id]
        except (KeyError, TypeError):
            raise JudgeError("Judge backend omitted the requested answer.") from None
        return self._checked_verdict(verdict)

    @staticmethod
    def _checked_verdict(verdict: Any) -> JudgeVerdict:
        if not isinstance(verdict, JudgeVerdict):
            raise JudgeError("Judge backend returned an invalid verdict.")
        if verdict.label is not None:
            raise JudgeError("Numeric critic received a categorical verdict.")
        return replace(
            verdict,
            score=_checked_number(verdict.score, "score", 0.0, 1.0),
            confidence=(
                _checked_number(verdict.confidence, "confidence", 0.0, 1.0)
                if verdict.confidence is not None
                else None
            ),
        )


@dataclass
class SemanticSimilarityCritic(JudgeCriticBase):
    """
    Semantic equivalence of expected vs actual (Jev Score).

    Upgrade path for the TF-IDF SimilarityCritic: understands paraphrase and
    penalizes negation and changed facts, which lexical overlap misses.
    """

    question_id: ClassVar[str] = "similarity"
    LEVELS: ClassVar[list[str]] = [
        "Unrelated or contradictory: different meaning, facts, or negated claims",
        "Same topic but different details: missing, added, or altered facts",
        "Same meaning: paraphrase with all key facts preserved",
    ]

    def build_state(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {"expected": expected, "actual": actual}

    def build_questions(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {
            self.question_id: {
                "type": "score",
                "instructions": (
                    "Do `actual` and `expected` express the same meaning with the "
                    "same key facts? Paraphrases match; negations and changed facts do not."
                ),
                "criteria": list(self.LEVELS),
            }
        }


@dataclass
class IntentionCritic(JudgeCriticBase):
    """
    Whether actual fulfills the declared intent (Jev Noul).

    Covers purpose, tone, and style via `intent=` instead of one class per
    dimension. The deterministic tier is exact match only: lexical overlap is
    not a valid intent proxy.
    """

    question_id: ClassVar[str] = "intent"
    intent: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.intent.strip():
            raise ValueError("IntentionCritic requires a non-empty intent.")

    def _deterministic_score(self, expected: Any, actual: Any) -> float:
        # Only identical text can claim intent fulfillment without a judge.
        return float(type(expected) is type(actual) and expected == actual)

    def build_state(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {"expected": expected, "actual": actual, "intent": self.intent}

    def build_questions(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {
            self.question_id: {
                "type": "noul",
                "instructions": (
                    f"Does `actual` fulfill this intent: {self.intent}? "
                    "Use `expected` as the reference for what fulfillment looks like."
                ),
                "criteria": {
                    "true": "Fulfills the intent completely with matching purpose and tone",
                    "false": "Misses the purpose, changes the tone, or ignores the intent",
                },
            }
        }


@dataclass
class GroundednessCritic(JudgeCriticBase):
    """
    How much of actual is supported by expected-as-source (Jev Score).

    Penalizes invented or contradictory claims; paraphrase alone is not
    penalized. Complements similarity (equivalence) and intention (purpose).
    """

    question_id: ClassVar[str] = "groundedness"
    LEVELS: ClassVar[list[str]] = [
        "Contradicted or fabricated: claims contradict the source or invent unsupported facts",
        "Partially supported: some claims supported, others unverifiable from the source",
        "Fully supported: all claims grounded in the source",
    ]

    def build_state(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {"expected": expected, "actual": actual}

    def build_questions(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {
            self.question_id: {
                "type": "score",
                "instructions": (
                    "How much of `actual` is supported by the facts and evidence in "
                    "`expected`? Penalize invented claims, extrapolations, and "
                    "contradictions; do not penalize wording differences."
                ),
                "criteria": list(self.LEVELS),
            }
        }


@dataclass
class CompletenessCritic(JudgeCriticBase):
    """
    How many explicit requirements in expected appear in actual (Jev Score).

    Omissions lower the score even when the remaining text is a good
    paraphrase — the case similarity alone would pass.
    """

    question_id: ClassVar[str] = "completeness"
    LEVELS: ClassVar[list[str]] = [
        "Missing most requirements: only a minority of expected items appear",
        "Partially complete: some required items are missing",
        "Complete: all explicit requirements in expected appear in actual",
    ]

    def build_state(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {"expected": expected, "actual": actual}

    def build_questions(self, expected: Any, actual: Any) -> dict[str, Any]:
        return {
            self.question_id: {
                "type": "score",
                "instructions": (
                    "How many of the explicit requirements in `expected` appear in "
                    "`actual`? Consider every required item; omissions lower the "
                    "score even when the remaining text is semantically similar."
                ),
                "criteria": list(self.LEVELS),
            }
        }
