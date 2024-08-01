from typing import cast

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcade.actor.core.auth import validate_token

security = HTTPBearer()  # Authorization: Bearer <xxx>


# Dependency function to validate JWT and extract API key
# The validator function is provided by the BaseActor class
async def get_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    jwt: str = credentials.credentials
    validation_result = validate_token(jwt)

    if not validation_result.valid:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token. Error: {validation_result.error}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return cast(str, validation_result.api_key)
