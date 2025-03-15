import pytest


class DummyContext:
    def get_secret(self, key: str) -> str | None:
        if key.lower() == "serp_api_key":
            return "dummy_key"
        return None


@pytest.fixture
def dummy_context():
    return DummyContext()
