from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcade.actor.core.auth import validate_engine_token

security = HTTPBearer()  # Authorization: Bearer <xxx>


# Dependency function to validate JWT
async def validate_engine_request(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> None:
    jwt: str = credentials.credentials
    validation_result = validate_engine_token(jwt)

    if not validation_result.valid:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token. Error: {validation_result.error}",
            headers={"WWW-Authenticate": "Bearer"},
        )
