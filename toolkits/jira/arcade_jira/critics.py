from dataclasses import dataclass
from typing import Any

from arcade_evals.critic import BinaryCritic


@dataclass
class HasSubstringCritic(BinaryCritic):
    """A critic for checking whether the argument value contains a substring."""

    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Evaluates whether the actual value contains the expected value.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        if not isinstance(actual, str) or not isinstance(expected, str):
            return {"match": False, "score": 0.0}

        try:
            actual_casted = self.cast_actual(expected, actual)
        except TypeError:
            actual_casted = actual

        match = expected in actual_casted
        return {"match": match, "score": self.weight if match else 0.0}


@dataclass
class CaseInsensitiveBinaryCritic(BinaryCritic):
    """A critic for checking whether actual and expected values are the same, case insensitive."""

    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Evaluates whether the actual value is the same as the expected value, case insensitive.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        if not isinstance(actual, str) or not isinstance(expected, str):
            return {"match": False, "score": 0.0}

        try:
            actual_casted = self.cast_actual(expected, actual)
        except TypeError:
            actual_casted = actual

        match = expected.casefold() in actual_casted.casefold()
        return {"match": match, "score": self.weight if match else 0.0}


@dataclass
class CaseInsensitiveListOfStringsBinaryCritic(BinaryCritic):
    """Checks that all strings match in Actual and Expected list of strings, case insensitive"""

    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Checks that all strings match in Actual and Expected list of strings, case insensitive

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        if not isinstance(actual, list) or not isinstance(expected, list):
            return {"match": False, "score": 0.0}

        all_actual_str = all(isinstance(item, str) for item in actual)
        all_expected_str = all(isinstance(item, str) for item in expected)

        if not all_actual_str or not all_expected_str:
            return {"match": False, "score": 0.0}

        actual_folded = [item.casefold() for item in actual]
        expected_folded = [item.casefold() for item in expected]

        match = len(actual) == len(expected) and all(
            item in actual_folded for item in expected_folded
        )
        return {"match": match, "score": self.weight if match else 0.0}
