from arcade_evals import BinaryCritic


class BinaryListCaseInsensitiveCritic(BinaryCritic):
    """A critic that checks if the list of items is similar to the expected list of items."""

    def evaluate(self, expected: list[str], actual: list[str]) -> dict[str, float | bool]:
        if len(expected) != len(actual):
            return {"match": False, "score": 0.0}
        for i, item in enumerate(expected):
            if item.casefold() != actual[i].casefold():
                return {"match": False, "score": 0.0}
        return {"match": True, "score": self.weight}
