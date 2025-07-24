from typing import Any, ClassVar

from arcade_evals.critic import Critic


class BoardIdsCritic(Critic):
    """Custom critic for board IDs that accepts either name or ID as equivalent."""

    # Mapping of board names to IDs from test context
    BOARD_MAPPING: ClassVar[dict[str, str]] = {
        "Development Team": "123",
        "Marketing Board": "456",
        "QA Testing": "789",
        "Product Roadmap": "999",
    }

    def evaluate(self, expected: list[str], actual: list[str]) -> dict[str, Any]:
        """Evaluate board IDs, accepting either name or ID as valid."""
        if not expected or not actual:
            match = expected == actual
            return {"match": match, "score": self.weight if match else 0.0}

        # Normalize both expected and actual to sets of IDs
        expected_ids = set()
        for board in expected:
            if board in self.BOARD_MAPPING:
                expected_ids.add(self.BOARD_MAPPING[board])
            else:
                expected_ids.add(board)  # Already an ID

        actual_ids = set()
        for board in actual:
            if board in self.BOARD_MAPPING:
                actual_ids.add(self.BOARD_MAPPING[board])
            else:
                actual_ids.add(board)  # Already an ID

        match = expected_ids == actual_ids
        return {"match": match, "score": self.weight if match else 0.0}


class StateListCritic(Critic):
    """Custom critic for state lists that ignores order."""

    def evaluate(self, expected: list[str] | None, actual: list[str] | None) -> dict[str, Any]:
        """Evaluate state lists, ignoring order."""
        if expected is None and actual is None:
            return {"match": True, "score": self.weight}

        if expected is None or actual is None:
            match = expected == actual
            return {"match": match, "score": self.weight if match else 0.0}

        # Compare as sets to ignore order
        expected_set = set(expected)
        actual_set = set(actual)
        match = expected_set == actual_set
        return {"match": match, "score": self.weight if match else 0.0}


class BoardIdentifiersCritic(Critic):
    """Custom critic for board identifiers that accepts either name or ID as equivalent
    and ignores order."""

    # Mapping of board names to IDs from test context
    BOARD_MAPPING: ClassVar[dict[str, str]] = {
        "Development Team": "123",
        "Marketing Board": "456",
        "QA Testing": "789",
        "Product Roadmap": "999",
    }

    def evaluate(self, expected: list[str] | None, actual: list[str] | None) -> dict[str, Any]:
        """Evaluate board identifiers, accepting either name or ID as valid."""
        if expected is None and actual is None:
            return {"match": True, "score": self.weight}

        if expected is None or actual is None:
            match = expected == actual
            return {"match": match, "score": self.weight if match else 0.0}

        # Normalize both expected and actual to sets of IDs
        expected_ids = set()
        for board in expected:
            if board in self.BOARD_MAPPING:
                expected_ids.add(self.BOARD_MAPPING[board])
            else:
                expected_ids.add(board)  # Already an ID

        actual_ids = set()
        for board in actual:
            if board in self.BOARD_MAPPING:
                actual_ids.add(self.BOARD_MAPPING[board])
            else:
                actual_ids.add(board)  # Already an ID

        match = expected_ids == actual_ids
        return {"match": match, "score": self.weight if match else 0.0}
