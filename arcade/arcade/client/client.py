from typing import Any, Generic, TypeVar

import httpx
from openai import AsyncOpenAI, OpenAI
from openai.resources.chat import AsyncChat, Chat

from arcade.client.base import AsyncArcadeClient, BaseResource, SyncArcadeClient
from arcade.client.errors import (
    APIStatusError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)
from arcade.client.schema import (
    AuthProvider,
    AuthRequest,
    AuthResponse,
    ExecuteToolResponse,
)
from arcade.core.schema import ToolDefinition

T = TypeVar("T")
ClientT = TypeVar("ClientT", SyncArcadeClient, AsyncArcadeClient)

API_VERSION = "v1"
BASE_URL = "https://api.arcade-ai.com"


class AuthResource(BaseResource[ClientT]):
    """Authentication resource."""

    _base_path = f"/{API_VERSION}/auth"

    def authorize(
        self,
        provider: AuthProvider,
        scopes: list[str],
        user_id: str,
        authority: str | None = None,
    ) -> AuthResponse:
        """
        Initiate an authorization request.

        Args:
            provider: The authorization provider.
            scopes: The scopes required for the authorization.
            user_id: The user ID initiating the authorization.
            authority: The authority initiating the authorization.
        """
        auth_provider = provider.value

        body = {
            "auth_requirement": {
                "provider": auth_provider,
                auth_provider: AuthRequest(scope=scopes, authority=authority).model_dump(
                    exclude_none=True
                ),
            },
            "user_id": user_id,
        }

        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._base_path}/authorize",
            json=body,
        )
        return AuthResponse(**data)

    def poll_authorization(self, existing_response: AuthResponse) -> AuthResponse:
        """Poll for the status of an authorization

        Polls using the data returned from the authorize method.

        Example:
            auth_response = client.auth.authorize(...)
            auth_status = client.auth.poll_authorization(auth_response)
        """
        return self.poll_authorization(existing_response.auth_id, existing_response.scopes)

    def poll_authorization(self, auth_id: str, scopes: list[str] | None) -> AuthResponse:
        """Poll for the status of an authorization

        Polls using the authorization ID returned from the authorize method.

        Example:
            auth_status = client.auth.poll_authorization("auth_123", ["scope1", "scope2"])
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._base_path}/status",
            params={"authorizationID": auth_id, "scopes": " ".join(scopes) if scopes else None},
        )
        return AuthResponse(**data)


class ToolResource(BaseResource[ClientT]):
    """Tool resource."""

    _base_path = f"/{API_VERSION}/tool"

    def run(
        self,
        tool_name: str,
        user_id: str,
        tool_version: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> ExecuteToolResponse:
        """
        Send a request to execute a tool and return the response.

        Args:
            tool_name: The name of the tool to execute.
            user_id: The user ID initiating the tool execution.
            tool_version: The version of the tool to execute (if not provided, the latest version will be used).
            inputs: The inputs for the tool.
        """
        request_data = {
            "tool_name": tool_name,
            "user_id": user_id,
            "tool_version": tool_version,
            "inputs": inputs,
        }
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST", f"{self._base_path}/execute", json=request_data
        )
        return ExecuteToolResponse(**data)

    def get(self, director_id: str, tool_id: str) -> ToolDefinition:
        """
        Get the specification for a tool.
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._base_path}/definition",
            params={"director_id": director_id, "tool_id": tool_id},
        )
        return ToolDefinition(**data)


class ArcadeClientMixin(Generic[ClientT]):
    """Mixin for Arcade clients."""

    def __init__(self, base_url: str = BASE_URL, *args: Any, **kwargs: Any):
        super().__init__(base_url, *args, **kwargs)  # type: ignore[call-arg]
        self.auth: AuthResource = AuthResource(self)
        self.tool: ToolResource = ToolResource(self)

    def _handle_http_error(
        self,
        e: httpx.HTTPStatusError,
        error_map: dict[int, type[APIStatusError]],
    ) -> None:
        status_code = e.response.status_code
        error_class = error_map.get(status_code, InternalServerError)
        raise error_class(str(e), response=e.response)

    def _chat_url(self, base_url: str) -> str:
        # TODO (sam): make chat a Resource like others but maintain
        # the ability to call chat directly like the openai clients
        chat_url = str(base_url)
        if not base_url.endswith(API_VERSION):
            chat_url = f"{base_url}/{API_VERSION}"
        return chat_url


class Arcade(ArcadeClientMixin[SyncArcadeClient], SyncArcadeClient):
    """Synchronous Arcade client.

    Example:
        from arcade.client import Arcade

        client = Arcade(api_key="your-api-key")
        client.auth.authorize(...)
        client.tool.run(...)
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        chat_url = self._chat_url(self._base_url)
        self._openai_client = OpenAI(base_url=chat_url, api_key=self._api_key)

    @property
    def chat(self) -> Chat:
        return self._openai_client.chat

    def _execute_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Execute a synchronous request.
        """
        try:
            response = self._request(method, url, **kwargs)
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_http_error(
                e,
                {
                    400: BadRequestError,
                    401: UnauthorizedError,
                    403: PermissionDeniedError,
                    404: NotFoundError,
                    500: InternalServerError,
                },
            )


class AsyncArcade(ArcadeClientMixin[AsyncArcadeClient], AsyncArcadeClient):
    """Asynchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        chat_url = self._chat_url(self._base_url)
        self._openai_client = AsyncOpenAI(base_url=chat_url, api_key=self._api_key)

    @property
    def chat(self) -> AsyncChat:
        return self._openai_client.chat

    async def _execute_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Execute an asynchronous request.
        """
        try:
            response = await self._request(method, url, **kwargs)
            return response.json()
        except httpx.HTTPStatusError as e:
            self._handle_http_error(
                e,
                {
                    400: BadRequestError,
                    401: UnauthorizedError,
                    403: PermissionDeniedError,
                    404: NotFoundError,
                    500: InternalServerError,
                },
            )
