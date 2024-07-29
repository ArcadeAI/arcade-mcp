from typing import Callable, cast

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcade.actor.base_auth import TokenValidationResult

security = HTTPBearer()  # Authorization: Bearer <xxx>


# Dependency function to validate JWT and extract API key
# The validator function is provided by the BaseActor class
async def get_api_key(
    validator: Callable[[str], TokenValidationResult],
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    jwt = credentials.credentials
    validation_result = validator(jwt)

    if not validation_result.valid:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token. Error: {validation_result.error}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return cast(str, validation_result.api_key)
