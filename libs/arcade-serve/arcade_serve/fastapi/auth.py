from collections.abc import Iterable

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from arcade_serve.core.auth import validate_engine_token


# Dependency function to validate JWT
async def validate_engine_request(
    worker_secret: str,
    credentials: HTTPAuthorizationCredentials,
    accepted_secrets: Iterable[str] = (),
) -> None:
    jwt: str = credentials.credentials
    validation_result = validate_engine_token(worker_secret, jwt, accepted_secrets)

    if not validation_result.valid:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token. Error: {validation_result.error}",
            headers={"WWW-Authenticate": "Bearer"},
        )
