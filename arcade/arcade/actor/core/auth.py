from dataclasses import dataclass
from enum import Enum

import jwt

from arcade.core.config import config

SUPPORTED_TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)


@dataclass
class TokenValidationResult:
    valid: bool
    error: str | None = None


class SigningAlgorithm(str, Enum):
    HS256 = "HS256"


def validate_engine_token(token: str) -> TokenValidationResult:
    try:
        payload = jwt.decode(
            token,
            config.api.key,
            algorithms=[SigningAlgorithm.HS256],
            verify=True,
            audience="actor",
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return TokenValidationResult(valid=False, error=str(e))

    token_ver = payload.get("ver")
    if token_ver != SUPPORTED_TOKEN_VER:
        return TokenValidationResult(valid=False, error=f"Unsupported token version: {token_ver}")

    return TokenValidationResult(valid=True)
