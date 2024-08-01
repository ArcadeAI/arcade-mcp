from dataclasses import dataclass
from enum import Enum

import jwt

from arcade.core.config import config

TOKEN_VER = "1"  # noqa: S105 Possible hardcoded password assigned (false positive)


@dataclass
class TokenValidationResult:
    valid: bool
    api_key: str | None = None
    error: str | None = None


class SigningAlgorithm(str, Enum):
    HS256 = "HS256"


def validate_token(token: str) -> TokenValidationResult:
    try:
        payload = jwt.decode(
            token,
            config.api.secret,
            algorithms=[SigningAlgorithm.HS256],
            verify=True,
            issuer=config.engine_url,
            audience="actor",
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return TokenValidationResult(valid=False, error=str(e))

    api_key = payload.get("api_key")
    if api_key != config.api.key:
        return TokenValidationResult(valid=False, error="Invalid API key")

    token_ver = payload.get("ver")
    if token_ver != TOKEN_VER:
        return TokenValidationResult(valid=False, error=f"Unknown token version: {token_ver}")

    return TokenValidationResult(valid=True, api_key=api_key)
