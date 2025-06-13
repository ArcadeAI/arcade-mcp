from typing import Any

from arcade_evals import BinaryCritic


class ValueInListCritic(BinaryCritic):
    def evaluate(self, expected: list[Any], actual: Any) -> dict[str, float | bool]:
        match = actual in expected
        return {"match": match, "score": self.weight if match else 0.0}
