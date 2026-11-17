import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

import jwt

SUPPORTED_TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)

ADDITIONAL_SECRETS_ENV = "ARCADE_WORKER_SECRET_ADDITIONAL"
"""Comma-separated secrets accepted alongside the worker secret, never used to sign.

Lets the worker secret rotate without downtime: workers accept both the old and
the new value while the Engine and the workers move to the new one.
"""

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    valid: bool
    error: str | None = None


class SigningAlgorithm(str, Enum):
    HS256 = "HS256"


def additional_worker_secrets(value: str | None = None) -> tuple[str, ...]:
    """Parse the additional accepted secrets, from ``value`` or the environment."""
    raw = os.environ.get(ADDITIONAL_SECRETS_ENV, "") if value is None else value
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def validate_engine_token(
    worker_secret: str,
    token: str,
    additional_secrets: Iterable[str] = (),
) -> TokenValidationResult:
    signature_error: jwt.InvalidSignatureError | None = None
    for index, secret in enumerate((worker_secret, *additional_secrets)):
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
            logger.debug("Worker token verified with an additional worker secret")

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
