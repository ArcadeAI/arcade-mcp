import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

import jwt

SUPPORTED_TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)

WORKER_SECRETS_ENV = "ARCADE_WORKER_SECRETS"
"""A JSON array of secrets the worker accepts on Engine requests, never used to sign.

The worker secret itself is always accepted too. Listing the old and the new
value lets the worker secret rotate without rejecting calls: append the new
one, switch the Engine to it, then drop the old one.
"""

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    valid: bool
    error: str | None = None


class SigningAlgorithm(str, Enum):
    HS256 = "HS256"


def parse_worker_secrets(raw: str | None) -> tuple[str, ...]:
    """Parse an ``ARCADE_WORKER_SECRETS`` value.

    Unset or empty means none. Anything but a JSON array of non-empty strings
    raises, so a worker with a broken list fails at startup instead of
    rejecting the Engine's calls.
    """
    if raw is None or not raw.strip():
        return ()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"{WORKER_SECRETS_ENV} must be a JSON array of strings") from None
    if not isinstance(decoded, list) or not all(
        isinstance(secret, str) and secret for secret in decoded
    ):
        raise ValueError(f"{WORKER_SECRETS_ENV} must be a JSON array of non-empty strings")
    return tuple(decoded)


def validate_engine_token(
    worker_secret: str,
    token: str,
    accepted_secrets: Iterable[str] = (),
) -> TokenValidationResult:
    signature_error: jwt.InvalidSignatureError | None = None
    secrets = dict.fromkeys((worker_secret, *accepted_secrets))
    for index, secret in enumerate(secrets):
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[SigningAlgorithm.HS256],
                verify=True,
                audience="worker",
            )
        except jwt.InvalidSignatureError as e:
            signature_error = signature_error or e
            continue
        except jwt.InvalidTokenError as e:
            return TokenValidationResult(valid=False, error=str(e))

        if index > 0:
            logger.debug("Worker token verified with a secret from %s", WORKER_SECRETS_ENV)

        token_ver = payload.get("ver")
        if token_ver != SUPPORTED_TOKEN_VER:
            return TokenValidationResult(
                valid=False, error=f"Unsupported token version: {token_ver}"
            )

        return TokenValidationResult(valid=True)

    logger.warning(
        "Invalid worker token signature. The Arcade Engine may be configured "
        "with a different Worker secret than this worker."
    )
    return TokenValidationResult(valid=False, error=str(signature_error))
