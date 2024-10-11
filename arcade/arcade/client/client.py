import json
from typing import Any, TypeVar, Union

from httpx import Timeout

from arcade.client.base import (
    AsyncArcadeClient,
    BaseResource,
    SyncArcadeClient,
)
from arcade.client.errors import APIStatusError, EngineNotHealthyError, EngineOfflineError
from arcade.client.schema import (
    AuthProvider,
    AuthProviderType,
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

    _path = "/auth"

    def authorize(
        self,
        user_id: str,
        provider: AuthProvider | str,
        provider_type: AuthProviderType = AuthProviderType.oauth2,
        scopes: list[str] | None = None,
    ) -> AuthResponse:
        """
        Initiate an authorization request.

        Args:
            provider: The authorization provider.
            scopes: The scopes required for the authorization.
            user_id: The user ID initiating the authorization.
        """
        auth_provider_type = provider_type.value

        body = {
            "auth_requirement": {
                "provider_id": provider.value if isinstance(provider, AuthProvider) else provider,
                "provider_type": auth_provider_type,
                auth_provider_type: AuthRequest(scopes=scopes or []).model_dump(exclude_none=True),
            },
            "user_id": user_id,
        }

        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._resource_path}/authorize",
            json=body,
        )
        return AuthResponse(**data)

    def status(
        self,
        auth_id_or_response: Union[str, AuthResponse],
        scopes: list[str] | None = None,
        wait: int | None = None,
    ) -> AuthResponse:
        """
        Poll for the status of an authorization

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

        # Calculate the new timeout based on the wait parameter
        new_timeout = self._client._timeout
        if wait is not None:
            if isinstance(self._client._timeout, Timeout):
                new_timeout = Timeout(
                    connect=self._client._timeout.connect,
                    read=(self._client._timeout.read or 0) + wait,
                    write=self._client._timeout.write,
                    pool=self._client._timeout.pool,
                )
            else:
                new_timeout = self._client._timeout + wait

        data = self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/status",
            params={
                "authorizationId": auth_id,
                "scopes": " ".join(scopes) if scopes else None,
                "wait": wait,
            },
            timeout=new_timeout,
        )
        return AuthResponse(**data)


class ToolResource(BaseResource[ClientT]):
    """Tool resource."""

    _path = "/tools"

    def run(
        self,
        tool_name: str,
        user_id: str,
        tool_version: str | None = None,
        inputs: dict[str, Any] | str | None = None,
    ) -> ExecuteToolResponse:
        """
        Send a request to execute a tool and return the response.

        Args:
            tool_name: The name of the tool to execute.
            user_id: The user ID initiating the tool execution.
            tool_version: The version of the tool to execute (if not provided, the latest version will be used).
            inputs: The inputs for the tool.
        """
        if not isinstance(inputs, str):
            try:
                inputs = json.dumps(inputs)
            except Exception:
                raise ValueError("Inputs must be a valid JSON object or serializable dictionary")

        request_data = {
            "tool_name": tool_name,
            "user_id": user_id,
            "tool_version": tool_version,
            "inputs": inputs,
        }
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST", f"{self._resource_path}/execute", json=request_data
        )
        return ExecuteToolResponse(**data)

    def get(self, director_id: str, tool_id: str) -> ToolDefinition:
        """
        Get the specification for a tool.
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/definition",
            params={"directorId": director_id, "toolId": tool_id},
        )
        return ToolDefinition(**data)

    def authorize(
        self, tool_name: str, user_id: str, tool_version: str | None = None
    ) -> AuthResponse:
        """
        Get the authorization status for a tool.
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._resource_path}/authorize",
            json={"tool_name": tool_name, "tool_version": tool_version, "user_id": user_id},
        )
        return AuthResponse(**data)

    def list_tools(self, toolkit: str | None = None) -> list[ToolDefinition]:
        """
        List the tools available for a given toolkit and provider.
        """
        data = self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/list",
            params={"toolkit": toolkit},
        )
        return [ToolDefinition(**tool) for tool in data]


class HealthResource(BaseResource[ClientT]):
    """Health check resource."""

    _path = "/health"

    def check(self) -> None:
        """
        Check the health of the Arcade Engine.
        Raises an error if the health check fails.
        """

        try:
            data = self._client._execute_request(  # type: ignore[attr-defined]
                "GET",
                f"{self._resource_path}",
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

    _path = "/auth"

    async def authorize(
        self,
        user_id: str,
        provider: AuthProvider | str,
        provider_type: AuthProviderType = AuthProviderType.oauth2,
        scopes: list[str] | None = None,
    ) -> AuthResponse:
        """
        Initiate an asynchronous authorization request.
        """
        auth_provider_type = provider_type.value

        body = {
            "auth_requirement": {
                "provider_id": provider.value if isinstance(provider, AuthProvider) else provider,
                "provider_type": auth_provider_type,
                auth_provider_type: AuthRequest(scopes=scopes or []).model_dump(exclude_none=True),
            },
            "user_id": user_id,
        }

        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._resource_path}/authorize",
            json=body,
        )
        return AuthResponse(**data)

    async def status(
        self,
        auth_id_or_response: Union[str, AuthResponse],
        scopes: list[str] | None = None,
        wait: int | None = None,
    ) -> AuthResponse:
        """
        Poll for the status of an authorization asynchronously

        Polls using either the authorization ID or the data returned from the authorize method.

        Example:
            auth_response = await client.auth.authorize(...)
            auth_status = await client.auth.poll_authorization(auth_response)
            auth_status = await client.auth.poll_authorization("auth_123", ["scope1", "scope2"])
        """
        if isinstance(auth_id_or_response, AuthResponse):
            auth_id = auth_id_or_response.auth_id
            scopes = auth_id_or_response.scopes
        else:
            auth_id = auth_id_or_response

        # Calculate the new timeout based on the wait parameter
        new_timeout = self._client._timeout
        if wait is not None:
            if isinstance(self._client._timeout, Timeout):
                new_timeout = Timeout(
                    connect=self._client._timeout.connect,
                    read=(self._client._timeout.read or 0) + wait,
                    write=self._client._timeout.write,
                    pool=self._client._timeout.pool,
                )
            else:
                new_timeout = self._client._timeout + wait

        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/status",
            params={"authorizationId": auth_id, "scopes": " ".join(scopes) if scopes else None},
            timeout=new_timeout,
        )
        return AuthResponse(**data)


class AsyncToolResource(BaseResource[AsyncArcadeClient]):
    """Asynchronous Tool resource."""

    _path = "/tools"

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
            "POST", f"{self._resource_path}/execute", json=request_data
        )
        return ExecuteToolResponse(**data)

    async def get(self, director_id: str, tool_id: str) -> ToolDefinition:
        """
        Get the specification for a tool asynchronously.
        """
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/definition",
            params={"directorId": director_id, "toolId": tool_id},
        )
        return ToolDefinition(**data)

    async def authorize(
        self, tool_name: str, user_id: str, tool_version: str | None = None
    ) -> AuthResponse:
        """
        Get the authorization status for a tool.
        """
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "POST",
            f"{self._resource_path}/authorize",
            json={"tool_name": tool_name, "tool_version": tool_version, "user_id": user_id},
        )
        return AuthResponse(**data)

    async def list_tools(self, toolkit: str | None = None) -> list[ToolDefinition]:
        """
        List the tools available for a given toolkit and provider.
        """
        data = await self._client._execute_request(  # type: ignore[attr-defined]
            "GET",
            f"{self._resource_path}/list",
            params={"toolkit": toolkit},
        )
        return [ToolDefinition(**tool) for tool in data]


class AsyncHealthResource(BaseResource[AsyncArcadeClient]):
    """Asynchronous Health check resource."""

    _path = "/health"

    async def check(self) -> None:
        """
        Check the health of the Arcade Engine.
        Raises an error if the health check fails.
        """

        try:
            data = await self._client._execute_request(  # type: ignore[attr-defined]
                "GET",
                f"{self._resource_path}",
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
        self.tools: ToolResource = ToolResource(self)
        self.health: HealthResource = HealthResource(self)

    def _execute_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Execute a synchronous request.
        """
        response = self._request(method, url, **kwargs)
        return response.json()


class AsyncArcade(AsyncArcadeClient):
    """Asynchronous Arcade client."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.auth: AsyncAuthResource = AsyncAuthResource(self)
        self.tools: AsyncToolResource = AsyncToolResource(self)
        self.health: AsyncHealthResource = AsyncHealthResource(self)

    async def _execute_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Execute an asynchronous request.
        """
        response = await self._request(method, url, **kwargs)
        return response.json()
