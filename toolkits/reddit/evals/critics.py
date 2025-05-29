from dataclasses import dataclass
from typing import Any

from arcade_evals.critic import Critic


@dataclass
class AnyOfCritic(Critic):
    """
    A critic that checks if the actual value matches any of the expected values.
    In other words, it checks if the actual value is in the expected list.
    """

    def evaluate(self, expected: list[Any], actual: Any) -> dict[str, float | bool]:
        match = actual in expected
        return {"match": match, "score": self.weight if match else 0.0}


@dataclass
class ListCritic(Critic):
    """
    A critic for comparing two lists.
    """

    def __init__(
        self,
        critic_field: str,
        weight: float = 1.0,
        order_matters: bool = True,
        duplicates_matter: bool = True,
    ):
        self.critic_field = critic_field
        self.weight = weight
        self.order_matters = order_matters
        self.duplicates_matter = duplicates_matter

    def evaluate(self, expected: list[Any], actual: list[Any]) -> dict[str, float | bool]:
        match = actual == expected if self.order_matters else set(actual) == set(expected)
        if self.duplicates_matter:
            match = match and len(actual) == len(expected)

        return {"match": match, "score": self.weight if match else 0.0}
