"""FastAPI routes for MCP server authorization endpoints.

The routes defined here enable MCP clients to discover authorization servers
associated with this MCP server.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from arcade_mcp_server.server_auth.base import ServerAuthProvider


def create_auth_router(
    server_auth_provider: ServerAuthProvider,
    canonical_url: str | None,
) -> APIRouter:
    """Create FastAPI router with OAuth discovery endpoints.

    Args:
        server_auth_provider: The server auth provider instance
        canonical_url: Canonical URL of the MCP server

    Returns:
        APIRouter configured with OAuth discovery endpoints
    """
    router = APIRouter(tags=["MCP Protocol"])

    @router.get("/.well-known/oauth-protected-resource")
    @router.get("/.well-known/oauth-protected-resource/mcp", include_in_schema=False)
    async def oauth_protected_resource() -> JSONResponse:
        """OAuth 2.0 Protected Resource Metadata (RFC 9728)"""
        if not canonical_url:
            return JSONResponse(
                {"error": "Server canonical URL not configured"},
                status_code=500,
            )

        metadata = server_auth_provider.get_resource_metadata()
        return JSONResponse(
            metadata,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )

    return router
