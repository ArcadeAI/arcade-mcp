import pytest

from arcade_cli.event import LocalDestinationError, resolve_local_target


@pytest.mark.parametrize(
    ("url", "connect_url", "host_header"),
    [
        ("http://127.0.0.1:8000/hook", "http://127.0.0.1:8000/hook", "127.0.0.1:8000"),
        ("http://[::1]:8000/hook", "http://[::1]:8000/hook", "[::1]:8000"),
    ],
)
def test_resolve_local_target_accepts_explicit_numeric_loopback(
    url: str, connect_url: str, host_header: str
) -> None:
    target = resolve_local_target(url)
    assert target.connect_url == connect_url
    assert target.host_header == host_header


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000/hook",
        "http://127.0.0.1/hook",
        "http://[::1]/hook",
        "http://0.0.0.0:8000/hook",
        "http://127.0.0.2:8000/hook",
        "http://example.com:8000/hook",
        "http://user@127.0.0.1:8000/hook",
    ],
)
def test_resolve_local_target_rejects_every_non_explicit_loopback_form(url: str) -> None:
    with pytest.raises(LocalDestinationError):
        resolve_local_target(url)
