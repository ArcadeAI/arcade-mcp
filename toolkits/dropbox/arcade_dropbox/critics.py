from typing import Any

from arcade_evals import BinaryCritic


class DropboxPathCritic(BinaryCritic):
    def evaluate(self, expected: Any, actual: Any) -> dict[str, float | bool]:
        """
        Ignores leading slash in the actual value when comparing to the expected value.

        Note: sometimes the LLM won't start the path with a slash, so this critic ignores it when
        comparing. Dropbox tools will add the slash, when needed, so no worries about API errors.

        Args:
            expected: The expected value.
            actual: The actual value to compare, cast to the type of expected.

        Returns:
            dict: A dictionary containing the match status and score.
        """
        try:
            actual_casted = self.cast_actual(expected, actual)
        # TODO log or something better here
        except TypeError:
            actual_casted = actual

        if isinstance(expected, str):
            expected = expected.lstrip("/")

        if isinstance(actual_casted, str):
            actual_casted = actual_casted.lstrip("/")

        match = expected == actual_casted
        return {"match": match, "score": self.weight if match else 0.0}
