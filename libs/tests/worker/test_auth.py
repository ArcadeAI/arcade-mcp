import jwt
import pytest
from arcade_serve.core.auth import (
    SUPPORTED_TOKEN_VER,
    SigningAlgorithm,
    parse_worker_secrets,
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


NEW_SECRET = "new-worker-secret-at-least-32-bytes-long"  # noqa: S105 test secret, not a credential


def test_token_signed_with_an_accepted_secret_accepted():
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER}, secret=NEW_SECRET)
    assert validate_engine_token(WORKER_SECRET, token, (WORKER_SECRET, NEW_SECRET)).valid


def test_worker_secret_accepted_even_when_not_listed():
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER})
    assert validate_engine_token(WORKER_SECRET, token, (NEW_SECRET,)).valid


def test_token_signed_with_no_accepted_secret_rejected():
    token = _mint({"aud": "worker", "ver": SUPPORTED_TOKEN_VER}, secret="someone-elses-secret")  # noqa: S106 test secret
    result = validate_engine_token(WORKER_SECRET, token, (NEW_SECRET,))
    assert not result.valid
    assert result.error == "Signature verification failed"


def test_accepted_secret_still_checks_claims():
    token = _mint({"aud": "not-worker", "ver": SUPPORTED_TOKEN_VER}, secret=NEW_SECRET)
    assert not validate_engine_token(WORKER_SECRET, token, (NEW_SECRET,)).valid

    token = _mint({"aud": "worker", "ver": "999"}, secret=NEW_SECRET)
    result = validate_engine_token(WORKER_SECRET, token, (NEW_SECRET,))
    assert not result.valid
    assert "Unsupported token version" in (result.error or "")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ()),
        ("", ()),
        ("  ", ()),
        ("[]", ()),
        ('["a"]', ("a",)),
        ('["a", "b"]', ("a", "b")),
    ],
)
def test_parse_worker_secrets(raw, expected):
    assert parse_worker_secrets(raw) == expected


@pytest.mark.parametrize("raw", ["a,b", "not json", '"a"', '{"a": 1}', '["a", ""]', '["a", 1]'])
def test_parse_worker_secrets_refuses_anything_but_an_array_of_strings(raw):
    with pytest.raises(ValueError, match="ARCADE_WORKER_SECRETS"):
        parse_worker_secrets(raw)
