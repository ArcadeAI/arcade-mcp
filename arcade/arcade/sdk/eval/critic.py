from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, ClassVar

import pytz
from dateutil import parser

from arcade.sdk.errors import WeightError


@dataclass
class Critic(ABC):
    critic_field: str
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0 or self.weight > 1:
            raise WeightError(f"Critic weight must be between 0 and 1, got {self.weight}")

    @abstractmethod
    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        pass


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
        return {"match": match, "score": self.weight if match else 0.0}


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
        return {"match": bool(score >= self.match_threshold), "score": float(score * self.weight)}


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

    def evaluate(self, expected: str, actual: str) -> dict[str, float | bool]:
        if self.metric == "cosine":
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
            except ImportError:
                raise ImportError(
                    "Use `pip install arcade[evals]` to install the required dependencies for similarity metrics."
                )
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([expected, actual])
            similarity = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1])[0][0]
        else:
            raise ValueError(f"Unsupported similarity metric: {self.metric}")
        return {
            "match": similarity >= self.similarity_threshold,
            "score": min(similarity * self.weight, self.weight),
        }


@dataclass
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
            return {"match": True, "score": self.weight}
        elif time_diff_seconds >= max_difference_seconds:
            # No score if beyond max_difference
            return {"match": False, "score": 0.0}
        else:
            # Partial score based on time difference
            ratio = 1 - (time_diff_seconds / max_difference_seconds)
            # Ensure ratio is not negative
            ratio = max(ratio, 0)
            score = self.weight * ratio
            return {"match": False, "score": score}
