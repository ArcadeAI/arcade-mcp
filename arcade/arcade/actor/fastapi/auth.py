from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from arcade.actor.core.auth import validate_engine_token


# Dependency function to validate JWT
async def validate_engine_request(
    actor_secret: str,
    credentials: HTTPAuthorizationCredentials,
) -> None:
    jwt: str = credentials.credentials
    validation_result = validate_engine_token(actor_secret, jwt)

    if not validation_result.valid:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token. Error: {validation_result.error}",
            headers={"WWW-Authenticate": "Bearer"},
        )
