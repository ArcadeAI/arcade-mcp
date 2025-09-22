"""
FastAPI OpenAPI Documentation Routes

This module provides FastAPI route definitions solely for generating OpenAPI/Swagger
documentation. These routes describe the HTTP endpoints and their request/response
schemas but do not contain actual implementation logic.

The routes documented here are:
- POST /mcp - Send JSON-RPC messages
- GET /mcp - Establish Server-Sent Events (SSE) stream
- DELETE /mcp - Terminate active session

Note: These are documentation-only routes. The actual protocol implementation
is handled separately through the underlying transport layer.
"""

from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from arcade_mcp_server.transports.http_streamable import MCP_SESSION_ID_HEADER
from arcade_mcp_server.types import JSONRPC_VERSION, LATEST_PROTOCOL_VERSION


# Pydantic models for OpenAPI documentation
class MCPRequest(BaseModel):
    """JSON-RPC request message for MCP protocol."""

    jsonrpc: str = Field(default=JSONRPC_VERSION, description="JSON-RPC version")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[dict[str, Any]] = Field(None, description="Method parameters")
    id: Optional[str | int] = Field(None, description="Request ID for correlating responses")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "jsonrpc": JSONRPC_VERSION,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": LATEST_PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "example-client", "version": "1.0.0"},
                    },
                    "id": 1,
                }
            ]
        }
    }


class MCPResponse(BaseModel):
    """JSON-RPC response message for MCP protocol."""

    jsonrpc: str = Field(default=JSONRPC_VERSION, description="JSON-RPC version")
    result: Optional[dict[str, Any]] = Field(None, description="Successful response data")
    error: Optional[dict[str, Any]] = Field(None, description="Error information if request failed")
    id: str | int = Field(..., description="Request ID this response corresponds to")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "jsonrpc": JSONRPC_VERSION,
                    "result": {
                        "protocolVersion": LATEST_PROTOCOL_VERSION,
                        "capabilities": {},
                        "serverInfo": {"name": "arcade-server", "version": "1.0.0"},
                    },
                    "id": 1,
                }
            ]
        }
    }


class MCPError(BaseModel):
    """Error response for MCP protocol."""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    data: Optional[Any] = Field(None, description="Additional error data")


def get_openapi_routes() -> list[dict]:
    """Get OpenAPI route definitions for MCP endpoints."""
    return [
        {
            "path": "/mcp/",
            "post": {
                "tags": ["MCP Protocol"],
                "summary": "Send MCP message",
                "description": "Send a JSON-RPC message to the MCP server. This endpoint handles:\n"
                "- Method requests (with id) - returns a JSON response\n"
                "- Notifications (without id) - returns 202 Accepted\n\n"
                "For SSE mode, set Accept: text/event-stream header.\n"
                "For JSON mode, set Accept: application/json header.",
                "operationId": "send_mcp_message",
                "parameters": [
                    {
                        "name": "accept",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "content-type",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": MCP_SESSION_ID_HEADER,
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/MCPRequest"}}
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/MCPResponse"}
                            }
                        },
                    },
                    "202": {"description": "Notification accepted (no response expected)"},
                    "400": {"description": "Bad Request - Invalid JSON or missing required fields"},
                    "404": {"description": "Not Found - Invalid or expired session ID"},
                    "406": {
                        "description": "Not Acceptable - Client must accept required content types"
                    },
                    "415": {
                        "description": "Unsupported Media Type - Content-Type must be application/json"
                    },
                    "500": {"description": "Internal Server Error"},
                },
            },
            "get": {
                "tags": ["MCP Protocol"],
                "summary": "Establish SSE stream",
                "description": "Establish a Server-Sent Events (SSE) stream for receiving server-initiated messages.\n\n"
                "Only one SSE stream is allowed per session. The stream will remain open until:\n"
                "- The client closes the connection\n"
                "- The session is terminated\n"
                "- An error occurs\n\n"
                "Requires Accept: text/event-stream header.",
                "operationId": "establish_sse_stream",
                "parameters": [
                    {
                        "name": "accept",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": MCP_SESSION_ID_HEADER,
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "Last-Event-ID",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "SSE stream established",
                        "content": {
                            "text/event-stream": {"example": 'data: {"jsonrpc":"2.0",...}\\n\\n'}
                        },
                    },
                    "409": {"description": "Conflict - Only one SSE stream allowed per session"},
                    "400": {"description": "Bad Request - Invalid JSON or missing required fields"},
                    "404": {"description": "Not Found - Invalid or expired session ID"},
                    "406": {
                        "description": "Not Acceptable - Client must accept required content types"
                    },
                    "500": {"description": "Internal Server Error"},
                },
            },
            "delete": {
                "tags": ["MCP Protocol"],
                "summary": "Terminate session",
                "description": "Terminate the current MCP session. This will:\n"
                "- Close all active streams\n"
                "- Clean up session resources\n"
                "- Return 200 OK on successful termination\n\n"
                "Only available in stateful mode (when session IDs are used).",
                "operationId": "terminate_mcp_session",
                "parameters": [
                    {
                        "name": MCP_SESSION_ID_HEADER,
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {"description": "Session terminated successfully"},
                    "405": {
                        "description": "Method Not Allowed - Session termination not supported in stateless mode"
                    },
                    "400": {"description": "Bad Request - Invalid JSON or missing required fields"},
                    "404": {"description": "Not Found - Invalid or expired session ID"},
                    "500": {"description": "Internal Server Error"},
                },
            },
        }
    ]


def create_mcp_router() -> APIRouter:
    """Create FastAPI router with MCP endpoint documentation."""
    router = APIRouter(
        prefix="",
        tags=["MCP Protocol"],
        responses={
            400: {"description": "Bad Request - Invalid JSON or missing required fields"},
            404: {"description": "Not Found - Invalid or expired session ID"},
            406: {"description": "Not Acceptable - Client must accept required content types"},
            415: {"description": "Unsupported Media Type - Content-Type must be application/json"},
            500: {"description": "Internal Server Error"},
        },
    )

    @router.post(
        "/",
        response_model=MCPResponse,
        summary="Send MCP message",
        description="""
        Send a JSON-RPC message to the MCP server. This endpoint handles:
        - Method requests (with id) - returns a JSON response
        - Notifications (without id) - returns 202 Accepted

        For SSE mode, set Accept: text/event-stream header.
        For JSON mode, set Accept: application/json header.
        """,
        responses={
            200: {"description": "Successful response", "model": MCPResponse},
            202: {"description": "Notification accepted (no response expected)"},
        },
    )
    async def send_message(
        request: Request,
        body: MCPRequest,
        accept: str = Header(None),
        content_type: str = Header(None),
        mcp_session_id: Optional[str] = Header(None, alias=MCP_SESSION_ID_HEADER),
    ) -> None:
        """
        Documentation-only endpoint definition.
        """
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Documentation endpoint only",
        )

    @router.get(
        "/",
        summary="Establish SSE stream",
        description="""
        Establish a Server-Sent Events (SSE) stream for receiving server-initiated messages.

        Only one SSE stream is allowed per session. The stream will remain open until:
        - The client closes the connection
        - The session is terminated
        - An error occurs

        Requires Accept: text/event-stream header.
        """,
        responses={
            200: {
                "description": "SSE stream established",
                "content": {"text/event-stream": {"example": 'data: {"jsonrpc":"2.0",...}\\n\\n'}},
            },
            409: {"description": "Conflict - Only one SSE stream allowed per session"},
        },
    )
    async def establish_sse(
        request: Request,
        accept: str = Header(None),
        mcp_session_id: Optional[str] = Header(None, alias=MCP_SESSION_ID_HEADER),
        last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    ) -> None:
        """
        Documentation-only endpoint definition.
        """
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Documentation endpoint only",
        )

    @router.delete(
        "/",
        summary="Terminate session",
        description="""
        Terminate the current MCP session. This will:
        - Close all active streams
        - Clean up session resources
        - Return 200 OK on successful termination

        Only available in stateful mode (when session IDs are used).
        """,
        responses={
            200: {"description": "Session terminated successfully"},
            405: {
                "description": "Method Not Allowed - Session termination not supported in stateless mode"
            },
        },
    )
    async def terminate_session(
        request: Request,
        mcp_session_id: Optional[str] = Header(None, alias=MCP_SESSION_ID_HEADER),
    ) -> None:
        """
        Documentation-only endpoint definition.
        """
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Documentation endpoint only",
        )

    return router
