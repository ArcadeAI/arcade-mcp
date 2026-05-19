import logging
import time

import jwt
from arcade_serve.core.auth import (
    SUPPORTED_TOKEN_VER,
    SigningAlgorithm,
    validate_engine_token,
)

WORKER_SECRET = "super-secret-worker-key-do-not-leak"  # noqa: S105
WRONG_SECRET = "wrong-key-used-to-sign-the-bad-token"  # noqa: S105


def _sign(secret: str, ver: str = SUPPORTED_TOKEN_VER) -> str:
    return jwt.encode(
        {"aud": "worker", "ver": ver, "iat": int(time.time())},
        secret,
        algorithm=SigningAlgorithm.HS256.value,
    )


def test_valid_token_passes():
    result = validate_engine_token(WORKER_SECRET, _sign(WORKER_SECRET))
    assert result.valid is True
    assert result.error is None


def test_unsupported_version_fails():
    result = validate_engine_token(WORKER_SECRET, _sign(WORKER_SECRET, ver="999"))
    assert result.valid is False
    assert "Unsupported token version" in (result.error or "")


def test_invalid_signature_does_not_log_worker_secret(caplog):
    bad_token = _sign(WRONG_SECRET)

    with caplog.at_level(logging.WARNING, logger="arcade_serve.core.auth"):
        result = validate_engine_token(WORKER_SECRET, bad_token)

    assert result.valid is False
    # The fix: the worker secret must never appear in any log record produced
    # during JWT signature validation. Logs are commonly forwarded to shared
    # sinks; leaking the HMAC key there is a full auth bypass of the worker
    # protocol.
    for record in caplog.records:
        rendered = record.getMessage()
        assert WORKER_SECRET not in rendered
        assert WORKER_SECRET not in str(record.args or "")
