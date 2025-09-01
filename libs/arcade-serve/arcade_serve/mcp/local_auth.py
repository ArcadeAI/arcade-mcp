"""
Local authentication mock for development.

This module provides a mock implementation of the Arcade auth client
that uses local configuration instead of calling the real Arcade API.
"""

import logging
from typing import Any, Literal

from arcadepy.types.auth_authorize_params import AuthRequirement
from arcadepy.types.shared import (
    AuthorizationContext,
    AuthorizationResponse,
)

logger = logging.getLogger("arcade.mcp")


AuthorizationStatus = Literal["not_started", "pending", "completed", "failed"]


class MockAuthClient:
    """Mock auth client for local development."""

    def __init__(
        self,
        auth_providers: list[dict[str, Any]] | None = None,
        host: str = "localhost",
        port: int = 8002,
    ):
        """
        Initialize the mock auth client.

        Args:
            auth_providers: List of auth provider configurations from worker.toml
        """
        self.host = host
        self.port = port
        self.providers = {}
        if auth_providers:
            for provider in auth_providers:
                provider_id = provider.get("provider_id")
                if provider_id:
                    self.providers[provider_id] = provider

    async def authorize(
        self,
        auth_requirement: AuthRequirement,
        user_id: str,
    ) -> AuthorizationResponse:
        """
        Mock authorization that returns tokens from local configuration.

        Args:
            auth_requirement: The auth requirement from the tool
            user_id: The user ID to authorize

        Returns:
            A mock authorization response
        """
        provider_id = auth_requirement.provider_id
        provider = self.providers.get(provider_id)

        if not provider:
            logger.warning(
                f"No local auth provider configured for '{provider_id}'. "
                f"Add it to worker.toml under [[worker.config.local_auth_providers]]"
            )
            return AuthorizationResponse(
                status=AuthorizationStatus.PENDING,
                url=f"http://{self.host}:{self.port}/mock-auth/{provider_id}",
                context=None,
            )

        # Check if we have a mock token for this user
        mock_tokens = provider.get("mock_tokens", {})
        token = mock_tokens.get(user_id)

        if not token:
            # Try environment variable fallback
            import os

            env_key = f"ARCADE_{provider_id.upper()}_TOKEN"
            token = os.environ.get(env_key)

            if not token:
                logger.warning(
                    f"No mock token found for user '{user_id}' with provider '{provider_id}'. "
                    f"Add it to worker.toml under mock_tokens or set {env_key}"
                )
                return AuthorizationResponse(
                    status=AuthorizationStatus.PENDING,
                    url=f"http://{self.host}:{self.port}/mock-auth/{provider_id}/{user_id}",
                    context=None,
                )

        # Return successful authorization with mock token
        logger.info(f"Returning mock token for user '{user_id}' with provider '{provider_id}'")
        return AuthorizationResponse(
            status=AuthorizationStatus.COMPLETED,
            url="",
            context=AuthorizationContext(
                token=token,
                # Include any additional context from the provider config
                user_id=user_id,
                provider_id=provider_id,
                scopes=provider.get("scopes", []),
            ),
        )


class MockArcadeClient:
    """Mock Arcade client for local development."""

    def __init__(
        self,
        auth_providers: list[dict[str, Any]] | None = None,
        host: str = "localhost",
        port: int = 8002,
    ):
        """
        Initialize the mock Arcade client.

        Args:
            auth_providers: List of auth provider configurations
        """
        self.auth = MockAuthClient(auth_providers)
