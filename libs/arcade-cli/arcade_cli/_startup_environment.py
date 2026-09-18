import os

ARCADE_URL_ENV = "ARCADE_URL"
ARCADE_API_KEY_ENV = "ARCADE_API_KEY"

_captured: dict[str, str | None] | None = None


def capture() -> None:
    global _captured
    if _captured is None:
        _captured = {
            ARCADE_URL_ENV: os.environ.get(ARCADE_URL_ENV),
            ARCADE_API_KEY_ENV: os.environ.get(ARCADE_API_KEY_ENV),
        }


def value(name: str) -> str | None:
    if _captured is not None:
        return _captured.get(name)
    return os.environ.get(name)


def forget() -> None:
    global _captured
    _captured = None
