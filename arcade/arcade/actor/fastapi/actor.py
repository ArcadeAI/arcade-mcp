import asyncio
from typing import Any, Callable

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcade.actor.base import BaseActor

# TODO get these from .config
creds = {
    "api_key": "123456789",
    "api_secret": "196a8a25-fde8-453a-9f58-ff646a6e034d",
}

TOKEN_VER = "1"  # TODO put this somewhere common

security = HTTPBearer()


# Dependency function to validate JWT and extract API key
async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        # TODO: validate issuer (= engine URL)
        # TODO: validate jti for replay prevention
        payload = jwt.decode(
            token, creds["api_secret"], algorithms=["HS256"], verify=True, audience="actor"
        )
        api_key = payload.get("api_key")
        if not api_key or api_key != creds["api_key"]:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_ver = payload.get("ver")
        if token_ver != TOKEN_VER:
            raise HTTPException(
                status_code=401,
                detail="Invalid token version",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key


class FastAPIActor(BaseActor):
    def __init__(self, app: FastAPI) -> None:
        """
        Initialize the FastAPIActor with a FastAPI app
        instance and an empty ToolCatalog.
        """
        super().__init__()
        self.app = app
        self.router = FastAPIRouter(app)
        self.register_routes(self.router)


class FastAPIRouter:  # TODO create an interface for this
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def add_route(self, path: str, handler: Callable, methods: str) -> None:
        """
        Add a route to the FastAPI application.
        """
        for method in methods:
            if method == "GET":
                self.app.get(path)(self.wrap_handler(handler))
            elif method == "POST":
                self.app.post(path)(self.wrap_handler(handler))
            elif method == "PUT":
                self.app.put(path)(self.wrap_handler(handler))
            elif method == "DELETE":
                self.app.delete(path)(self.wrap_handler(handler))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

    def wrap_handler(self, handler: Callable) -> Callable:
        """
        Wrap the handler to handle FastAPI-specific request and response.
        """

        async def wrapped_handler(request: Request, api_key: str = Depends(get_api_key)) -> Any:
            if asyncio.iscoroutinefunction(handler) or (
                callable(handler) and asyncio.iscoroutinefunction(handler.__call__)  # type: ignore[operator]
            ):
                return await handler(request)
            else:
                return handler(request)

        return wrapped_handler
