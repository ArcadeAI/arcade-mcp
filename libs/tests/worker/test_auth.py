import jwt
import pytest
from arcade_serve.core.auth import (
    SUPPORTED_TOKEN_VER,
    SigningAlgorithm,
    validate_engine_token,
)

WORKER_SECRET = "test-worker-secret-at-least-32-bytes-long"  # noqa: S105 test secret, not a credential


def _mint(payload: dict, *, secret: str = WORKER_SECRET, headers: dict | None = None) -> str:
    return jwt.encode(payload, secret, algorithm=SigningAlgorithm.HS256, headers=headers)


def test_valid_token_accepted():
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER})
    assert validate_engine_token(WORKER_SECRET, token).valid


def test_wrong_secret_rejected():
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER})
    result = validate_engine_token("a-different-secret-at-least-32-bytes", token)
    assert not result.valid


def test_wrong_audience_rejected():
    token = _mint({"aud": "not-worker", "ver": SUPPORTED_TOKEN_VER})
    assert not validate_engine_token(WORKER_SECRET, token).valid


def test_unsupported_token_version_rejected():
    token = _mint({"aud": "worker", "ver": "999"})
    result = validate_engine_token(WORKER_SECRET, token)
    assert not result.valid
    assert "Unsupported token version" in (result.error or "")


def test_unrecognized_crit_header_rejected():
    """Guards CVE-2026-32597: PyJWT < 2.12.0 silently accepted tokens carrying
    an unrecognized `crit` header extension instead of rejecting them per
    RFC 7515 §4.1.11. The pyjwt>=2.12.0 floor must keep rejecting them."""
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER}, headers={"crit": ["exp"]})
    result = validate_engine_token(WORKER_SECRET, token)
    assert not result.valid


@pytest.mark.parametrize("garbage", ["", "not-a-jwt", "a.b.c"])
def test_malformed_token_rejected(garbage):
    assert not validate_engine_token(WORKER_SECRET, garbage).valid
