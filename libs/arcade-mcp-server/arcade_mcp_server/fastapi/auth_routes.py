"""FastAPI routes for MCP Resource Server authorization endpoints.

The routes defined here enable MCP clients to discover authorization servers
associated with this MCP server.
"""

import logging
from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from arcade_mcp_server.resource_server.base import ResourceServerValidator

logger = logging.getLogger(__name__)


def create_auth_router(
    resource_server_validator: ResourceServerValidator,
    canonical_url: str | None,
) -> APIRouter:
    """Create FastAPI router with OAuth discovery endpoints.

    The well-known URI is constructed by inserting the well-known path after the host.
    If the canonical URL has a path component, then it becomes a suffix on the well-known path.

    For example:
    - canonical_url "https://example.com" -> "/.well-known/oauth-protected-resource"
    - canonical_url "https://example.com/mcp" -> "/.well-known/oauth-protected-resource/mcp"

    Args:
        resource_server_validator: The resource server validator instance
        canonical_url: Canonical URL of the MCP server

    Returns:
        APIRouter configured with OAuth discovery endpoints
    """
    router = APIRouter(tags=["MCP Protocol"])

    path_suffix = ""
    if canonical_url:
        parsed = urlparse(canonical_url)
        path_suffix = parsed.path

    well_known_base = "/.well-known/oauth-protected-resource"
    well_known_path = f"{well_known_base}{path_suffix}"

    async def oauth_protected_resource() -> JSONResponse:
        """OAuth 2.0 Protected Resource Metadata (RFC 9728)"""
        if not canonical_url:
            return JSONResponse(
                {"error": "Server canonical URL not configured"},
                status_code=500,
            )

        metadata = resource_server_validator.get_resource_metadata()
        if metadata is None:
            logger.error(
                "Resource metadata unavailable for OAuth discovery endpoint. "
                "This is unexpected - the validator should provide metadata if OAuth discovery is enabled."
            )
            return JSONResponse(
                {"error": "Resource metadata not available"},
                status_code=500,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                },
            )

        return JSONResponse(
            metadata,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    # Register the well-known endpoint at the RFC 9728 compliant path
    router.add_api_route(
        well_known_path,
        oauth_protected_resource,
        methods=["GET"],
        name="oauth_protected_resource",
    )

    # Also register at base path if there's a suffix for extra compatibility
    if path_suffix:
        router.add_api_route(
            well_known_base,
            oauth_protected_resource,
            methods=["GET"],
            include_in_schema=False,
        )

    return router
