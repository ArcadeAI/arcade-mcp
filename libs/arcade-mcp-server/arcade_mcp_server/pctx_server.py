"""
PctxMCPServer

Variant of :class:`MCPServer` that exposes pctx Code Mode tools
(``execute_typescript``, ``list_functions``, ``get_function_details``,
``search_functions``) via ``tools/list`` instead of the underlying tool
catalog. Tool execution still flows through the base ``MCPServer``
implementation; that override will be added in a follow-up.
"""

from __future__ import annotations

import logging
from typing import Any

from pctx_client.descriptions import get_tool_description
from pctx_client.models import (
    ExecuteBashInput,
    ExecuteTypescriptInput,
    GetFunctionDetailsInput,
    ToolDisclosure,
    ToolDisclosureName,
    ToolName,
)
from pydantic import BaseModel

from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import (
    JSONRPCError,
    JSONRPCResponse,
    ListToolsRequest,
    ListToolsResult,
    MCPTool,
)

logger = logging.getLogger("arcade.mcp.pctx")


class _SearchFunctionsInput(BaseModel):
    query: str
    k: int = 10


def _empty_object_schema() -> dict[str, Any]:
    return {"type": "object", "properties": {}}


def _build_code_mode_tools(disclosure: ToolDisclosure) -> list[MCPTool]:
    """Build the MCPTool DTOs that should be exposed in code-mode."""
    candidates: list[tuple[ToolName, dict[str, Any]]] = [
        ("list_functions", _empty_object_schema()),
        ("get_function_details", GetFunctionDetailsInput.model_json_schema()),
        ("execute_typescript", ExecuteTypescriptInput.model_json_schema()),
        ("search_functions", _SearchFunctionsInput.model_json_schema()),
        ("execute_bash", ExecuteBashInput.model_json_schema()),
    ]

    tools: list[MCPTool] = []
    for name, input_schema in candidates:
        if not disclosure.contains_tool(name):
            continue
        tools.append(
            MCPTool(
                name=name,
                description=get_tool_description(name, disclosure=disclosure),
                inputSchema=input_schema,
                outputSchema={"type": "string"},
            )
        )
    return tools


class PctxMCPServer(MCPServer):
    """MCPServer variant that surfaces pctx Code Mode tools to clients.

    ``tools/list`` returns the pctx Code Mode tool set (``execute_typescript``
    and friends) instead of the underlying tool catalog. ``tools/call`` is
    untouched for now and will fail for these synthetic tool names; that
    routing will be added next.
    """

    def __init__(
        self,
        *args: Any,
        pctx_url: str,
        pctx_disclosure: ToolDisclosure | ToolDisclosureName = ToolDisclosure.CATALOG,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._pctx_url = pctx_url
        self._pctx_disclosure = ToolDisclosure(pctx_disclosure)
        self._pctx_code_mode_tools: list[MCPTool] = _build_code_mode_tools(self._pctx_disclosure)
        logger.info(
            "PctxMCPServer enabled (url=%s, disclosure=%s, tools=%s)",
            self._pctx_url,
            self._pctx_disclosure.value,
            [t.name for t in self._pctx_code_mode_tools],
        )

    async def _handle_list_tools(
        self,
        message: ListToolsRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListToolsResult] | JSONRPCError:
        return JSONRPCResponse(
            id=message.id,
            result=ListToolsResult(tools=list(self._pctx_code_mode_tools)),
        )

    async def _handle_call_tool(self, message, session=None):
        raise NotImplementedError("todo")
