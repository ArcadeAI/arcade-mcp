from typing import Any

from arcade_evals import BinaryCritic


class RelativeTimeBinaryCritic(BinaryCritic):
    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Evaluates whether the expected and actual relative time strings are equivalent after
        casting.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        try:
            actual_casted = self.cast_actual(expected, actual)
        except TypeError:
            actual_casted = actual

        expected_parts = tuple(map(int, expected.split(":")))
        actual_parts = tuple(map(int, actual_casted.split(":")))

        if len(expected_parts) != 3 or len(actual_parts) != 3:
            return {"match": False, "score": 0.0}

        exp_days, exp_hours, exp_minutes = expected_parts
        act_days, act_hours, act_minutes = actual_parts

        match = exp_days == act_days and exp_hours == act_hours and exp_minutes == act_minutes
        return {"match": match, "score": self.weight if match else 0.0}
