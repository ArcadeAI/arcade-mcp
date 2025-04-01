from dataclasses import dataclass
from typing import Any

from arcade.sdk.eval.critic import Critic


@dataclass
class AnyOfCritic(Critic):
    """
    A critic that checks if the actual value matches any of the expected values.
    In other words, it checks if the actual value is in the expected list.
    """

    def evaluate(self, expected: list[Any], actual: Any) -> dict[str, float | bool]:
        match = actual in expected
        return {"match": match, "score": self.weight if match else 0.0}
