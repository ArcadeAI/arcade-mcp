from dataclasses import dataclass
from typing import Any

from arcade_evals.critic import Critic


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
        case_sensitive: bool = False,
    ):
        self.critic_field = critic_field
        self.weight = weight
        self.order_matters = order_matters
        self.duplicates_matter = duplicates_matter
        self.case_sensitive = case_sensitive

    def evaluate(self, expected: list[Any], actual: list[Any]) -> dict[str, float | bool]:
        if not self.case_sensitive:
            actual = [item.lower() for item in actual]
            expected = [item.lower() for item in expected]

        match = actual == expected if self.order_matters else set(actual) == set(expected)
        if self.duplicates_matter:
            match = match and len(actual) == len(expected)

        return {"match": match, "score": self.weight if match else 0.0}
