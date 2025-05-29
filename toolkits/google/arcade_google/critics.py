from collections.abc import Collection
from typing import Any

from arcade_evals import DatetimeCritic


class DatetimeOrNoneCritic(DatetimeCritic):
    """
    A critic that evaluates the closeness of datetime values within a specified tolerance or whether
    it's a None value.

    Attributes:
        tolerance: Acceptable timedelta between expected and actual datetimes.
        max_difference: Maximum timedelta for a partial score.
    """

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        if actual is None:
            return {"match": True, "score": self.weight}
        return super().evaluate(expected, actual)


class AnyDatetimeCritic(DatetimeCritic):
    """
    A critic that evaluates the closeness of datetime values within a list of expected values.
    """

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        if not isinstance(expected, Collection):
            expected = [expected]
        for expected_value in expected:
            critic = DatetimeCritic(
                critic_field=self.critic_field,
                weight=self.weight,
                tolerance=self.tolerance,
                max_difference=self.max_difference,
            )
            result = critic.evaluate(expected_value, actual)
            if result["match"]:
                return result
        return {"match": False, "score": 0}
