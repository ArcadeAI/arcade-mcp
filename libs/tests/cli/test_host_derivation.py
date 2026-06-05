import pytest

from arcade_cli.utils import derive_engine_url_from_coordinator


@pytest.mark.parametrize(
    "coordinator,engine",
    [
        ("https://cloud.arcade.dev", "https://api.arcade.dev"),
        ("https://cloud.example.dev", "https://api.example.dev"),
        ("https://cloud.example.dev:4443", "https://api.example.dev:4443"),
        ("https://cloud.foo.test", "https://api.foo.test"),
        ("http://localhost:8000", "http://localhost:9099"),
        ("http://127.0.0.1:8000", "http://localhost:9099"),
        ("http://0.0.0.0:8000", "http://localhost:9099"),
    ],
)
def test_derives_engine_url(coordinator: str, engine: str) -> None:
    assert derive_engine_url_from_coordinator(coordinator) == engine


def test_returns_none_for_unknown_convention() -> None:
    assert derive_engine_url_from_coordinator("https://otherhost.example") is None


def test_returns_none_for_garbage() -> None:
    assert derive_engine_url_from_coordinator("not-a-url") is None


def test_returns_none_for_empty_string() -> None:
    assert derive_engine_url_from_coordinator("") is None
