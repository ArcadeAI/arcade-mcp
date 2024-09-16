import logging
from dataclasses import dataclass
from enum import Enum

import jwt

SUPPORTED_TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    valid: bool
    error: str | None = None


class SigningAlgorithm(str, Enum):
    HS256 = "HS256"


def validate_engine_token(actor_secret: str, token: str) -> TokenValidationResult:
    try:
        payload = jwt.decode(
            token,
            actor_secret,
            algorithms=[SigningAlgorithm.HS256],
            verify=True,
            audience="actor",
        )
    except jwt.InvalidSignatureError as e:
        logger.warning(
            "Invalid signature. Is the Arcade Engine configured with the Actor secret '%s'?",
            actor_secret,
        )
        return TokenValidationResult(valid=False, error=str(e))

    except jwt.InvalidTokenError as e:
        return TokenValidationResult(valid=False, error=str(e))

    token_ver = payload.get("ver")
    if token_ver != SUPPORTED_TOKEN_VER:
        return TokenValidationResult(valid=False, error=f"Unsupported token version: {token_ver}")

    return TokenValidationResult(valid=True)
