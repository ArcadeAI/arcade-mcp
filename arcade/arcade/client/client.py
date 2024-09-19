from typing import Any, TypeVar, Union

import httpx
from openai import AsyncOpenAI, OpenAI
from openai.resources.chat import AsyncChat, Chat

from arcade.client.base import (
    API_VERSION,
    AsyncArcadeClient,
    BaseResource,
    SyncArcadeClient,
)
from arcade.client.errors import APIStatusError, EngineNotHealthyError, EngineOfflineError
from arcade.client.schema import (
    AuthProvider,
    AuthRequest,
    AuthResponse,
    ExecuteToolResponse,
    HealthCheckResponse,
)
from arcade.core.schema import ToolDefinition

T = TypeVar("T")
ClientT = TypeVar("ClientT", SyncArcadeClient, AsyncArcadeClient)


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
                auth_provider: AuthRequest(scopes=scopes, authority=authority).model_dump(
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

    def status(
        self, auth_id_or_response: Union[str, AuthResponse], scopes: list[str] | None = None
    ) -> AuthResponse:
        """Poll for the status of an authorization

        Polls using either the authorization ID or the data returned from the authorize method.

        Example:
            auth_response = client.auth.authorize(...)
            auth_status = client.auth.poll_authorization(auth_response)
            auth_status = client.auth.poll_authorization("auth_123", ["scope1", "scope2"])
        """
        if isinstance(auth_id_or_response, AuthResponse):
            auth_id = auth_id_or_response.auth_id
            scopes = auth_id_or_response.scopes
        else:
            auth_id = auth_id_or_response

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

    def authorize(self, tool_name: str, user_id: str) -> AuthResponse:
        """
        Get the authorization status for a tool.
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._base_path}/authorize",
            json={"tool_name": tool_name, "user_id": user_id},
        )
        return AuthResponse(**data)


class HealthResource(BaseResource[ClientT]):
    """Health check resource."""

    def check(self) -> None:
        """
        Check the health of the Arcade Engine.
        Raises an error if the health check fails.
        """

        try:
            data = self._client._execute_request(  # type: ignore[attr-defined]
                "GET",
                f"/{API_VERSION}/health",
                timeout=5,
            )

        except APIStatusError as e:
            raise EngineNotHealthyError(
                "Arcade Engine health check returned an unhealthy status code",
                status_code=e.status_code,
            )
        except Exception as e:
            # Catches everything else including httpx.ConnectError (most common)
            raise EngineOfflineError(f"Arcade Engine was unreachable: {e}")

        health_check_response = HealthCheckResponse(**data)

        # Raise an error if the health payload is not `healthy: true`
        if health_check_response.healthy is not True:
            raise EngineNotHealthyError(
                "Arcade Engine health check was not healthy",
                status_code=200,
            )


class AsyncAuthResource(BaseResource[AsyncArcadeClient]):
    """Asynchronous Authentication resource."""

    _base_path = f"/{API_VERSION}/auth"

    async def authorize(
        self,
        provider: AuthProvider,
        scopes: list[str],
        user_id: str,
        authority: str | None = None,
    ) -> AuthResponse:
        """
        Initiate an asynchronous authorization request.
        """
        auth_provider = provider.value

        body = {
            "auth_requirement": {
                "provider": auth_provider,
                auth_provider: AuthRequest(scopes=scopes, authority=authority).model_dump(
                    exclude_none=True
                ),
            },
            "user_id": user_id,
        }

        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._base_path}/authorize",
            json=body,
        )
        return AuthResponse(**data)

    async def status(self, auth_id: str) -> AuthResponse:
        """Poll for the status of an authorization asynchronously"""
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "GET", f"{self._base_path}/status", params={"authorizationID": auth_id}
        )
        return AuthResponse(**data)


class AsyncToolResource(BaseResource[AsyncArcadeClient]):
    """Asynchronous Tool resource."""

    _base_path = f"/{API_VERSION}/tools"

    async def run(
        self,
        tool_name: str,
        user_id: str,
        tool_version: str | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> ExecuteToolResponse:
        """
        Send an asynchronous request to execute a tool and return the response.
        """
        request_data = {
            "tool_name": tool_name,
            "user_id": user_id,
            "tool_version": tool_version,
            "inputs": inputs,
        }
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "POST", f"{self._base_path}/execute", json=request_data
        )
        return ExecuteToolResponse(**data)

    async def get(self, director_id: str, tool_id: str) -> ToolDefinition:
        """
        Get the specification for a tool asynchronously.
        """
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._base_path}/definition",
            params={"director_id": director_id, "tool_id": tool_id},
        )
        return ToolDefinition(**data)

    async def authorize(self, tool_name: str, user_id: str) -> AuthResponse:
        """
        Get the authorization status for a tool.
        """
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._base_path}/authorize",
            json={"tool_name": tool_name, "user_id": user_id},
        )
        return AuthResponse(**data)


class AsyncHealthResource(BaseResource[AsyncArcadeClient]):
    """Asynchronous Health check resource."""

    async def check(self) -> None:
        """
        Check the health of the Arcade Engine.
        Raises an error if the health check fails.
        """

        try:
            data = await self._client._execute_request(  # type: ignore[attr-defined]
                "GET",
                f"/{API_VERSION}/health",
                timeout=5,
            )

        except APIStatusError as e:
            raise EngineNotHealthyError(
                "Arcade Engine health check returned an unhealthy status code",
                status_code=e.status_code,
            )
        except Exception as e:
            # Catches everything else including httpx.ConnectError (most common)
            raise EngineOfflineError(f"Arcade Engine was unreachable: {e}")

        health_check_response = HealthCheckResponse(**data)

        # Raise an error if the health payload is not `healthy: true`
        if health_check_response.healthy is not True:
            raise EngineNotHealthyError(
                "Arcade Engine health check was not healthy",
                status_code=200,
            )


class Arcade(SyncArcadeClient):
    """Synchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth: AuthResource = AuthResource(self)
        self.tool: ToolResource = ToolResource(self)
        self.health: HealthResource = HealthResource(self)
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
            self._handle_http_error(e)


class AsyncArcade(AsyncArcadeClient):
    """Asynchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth: AsyncAuthResource = AsyncAuthResource(self)
        self.tool: AsyncToolResource = AsyncToolResource(self)
        self.health: AsyncHealthResource = AsyncHealthResource(self)
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
            self._handle_http_error(e)
