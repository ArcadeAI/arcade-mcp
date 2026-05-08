"""
PctxMCPServer

Variant of :class:`MCPServer` that exposes pctx Code Mode tools
(``execute_typescript``, ``list_functions``, ``get_function_details``,
``search_functions``) via ``tools/list`` instead of the underlying tool
catalog. Tool execution still flows through the base ``MCPServer``
implementation; that override will be added in a follow-up.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pctx_client import AsyncTool, Pctx
from pctx_client import tool as pctx_tool
from pctx_client.descriptions import get_tool_description
from pctx_client.models import (
    ExecuteBashInput,
    ExecuteTypescriptInput,
    GetFunctionDetailsInput,
    SearchFunctionsInput,
    ToolDisclosure,
    ToolDisclosureName,
    ToolName,
)

from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.session import ServerSession
from arcade_mcp_server.types import (
    CallToolParams,
    CallToolRequest,
    CallToolResult,
    JSONRPCError,
    JSONRPCResponse,
    ListToolsRequest,
    ListToolsResult,
    MCPTool,
    RequestId,
    TextContent,
)

logger = logging.getLogger("arcade.mcp.pctx")


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
        self._pctx_code_mode_tools: list[MCPTool] = self._build_code_mode_tools()
        logger.info(
            "PctxMCPServer enabled (url=%s, disclosure=%s, tools=%s)",
            self._pctx_url,
            self._pctx_disclosure.value,
            [t.name for t in self._pctx_code_mode_tools],
        )

    def _build_code_mode_tools(self) -> list[MCPTool]:
        """Build the MCPTool DTOs that should be exposed in code-mode."""
        # retain arcade <server_name>_ToolName pattern
        candidates: list[tuple[ToolName, str, dict[str, Any]]] = [
            ("list_functions", f"{self.name}_ListFunctions", {"type": "object", "properties": {}}),
            (
                "get_function_details",
                f"{self.name}_GetFunctionDetails",
                GetFunctionDetailsInput.model_json_schema(),
            ),
            (
                "execute_typescript",
                f"{self.name}_ExecuteTypescript",
                ExecuteTypescriptInput.model_json_schema(),
            ),
            (
                "search_functions",
                f"{self.name}_SearchFunctions",
                SearchFunctionsInput.model_json_schema(),
            ),
            ("execute_bash", f"{self.name}_ExecuteBash", ExecuteBashInput.model_json_schema()),
        ]

        tools: list[MCPTool] = []
        for pctx_name, arcade_name, input_schema in candidates:
            if not self._pctx_disclosure.contains_tool(pctx_name):
                continue
            tools.append(
                MCPTool(
                    name=arcade_name,
                    description=get_tool_description(pctx_name, disclosure=self._pctx_disclosure),
                    inputSchema=input_schema,
                )
            )
        return tools

    async def _build_pctx_tools(
        self, req_id: RequestId, session: ServerSession | None
    ) -> list[AsyncTool]:
        """Wrap each Arcade catalog tool as a pctx ``AsyncTool``.

        Each returned tool, when invoked by the pctx runtime, dispatches back
        through ``MCPServer._handle_call_tool`` so execution still flows
        through the base server's catalog/middleware. Results are unwrapped
        into Python values: ``structuredContent`` is preferred, otherwise the
        first ``TextContent`` is JSON-parsed (falling back to the raw string),
        otherwise the full content list is returned as plain dicts.

        Arcade tool names of the form ``<server>_<tool>`` are split into a
        pctx ``namespace``/``name`` pair; names without an underscore fall
        back to the ``tools`` namespace.
        """
        arcade_tools = await self._tool_manager.list_tools()

        pctx_tools: list[AsyncTool] = []
        for t in arcade_tools:
            # Arcade tool names are exposed as `<server_name>_<tool_name>`
            split_name = t.name.split("_", maxsplit=1)
            if len(split_name) == 2:
                namespace, name = split_name
            else:
                namespace, name = "tools", split_name[0]

            @pctx_tool(
                name=name,
                namespace=namespace,
                description=t.description,
                input_schema=t.inputSchema,
                output_schema=t.outputSchema,
            )
            async def _invoke_tool(_internal_arcade_tool_name: str = t.name, **kwargs: Any) -> Any:
                request = CallToolRequest(
                    id=req_id,
                    params=CallToolParams(
                        name=_internal_arcade_tool_name, arguments=kwargs or None
                    ),
                )
                response = await MCPServer._handle_call_tool(self, request, session)
                if isinstance(response, JSONRPCError):
                    raise RuntimeError(  # noqa: TRY004
                        f"Tool call {_internal_arcade_tool_name!r} failed: {response.error}"
                    )

                result = response.result
                if result.isError:
                    raise RuntimeError(f"Tool call {_internal_arcade_tool_name!r} failed: {result}")

                # Prefer structuredContent; otherwise try to JSON-parse the first
                # text content (string fallback); otherwise return the raw content list.
                if result.structuredContent is not None:
                    return result.structuredContent
                first = result.content[0] if result.content else None
                if isinstance(first, TextContent):
                    try:
                        return json.loads(first.text)
                    except json.JSONDecodeError:
                        return first.text
                return [c.model_dump(mode="json") for c in result.content]

            pctx_tools.append(_invoke_tool)
        return pctx_tools

    async def _handle_list_tools(
        self,
        message: ListToolsRequest,
        session: ServerSession | None = None,
    ) -> JSONRPCResponse[ListToolsResult] | JSONRPCError:
        return JSONRPCResponse(
            id=message.id,
            result=ListToolsResult(tools=self._pctx_code_mode_tools),
        )

    async def _handle_call_tool(
        self, message: CallToolRequest, session: ServerSession | None = None
    ) -> JSONRPCResponse[CallToolResult] | JSONRPCError:
        args = message.params.arguments or {}

        async with Pctx(
            url=self._pctx_url, tools=await self._build_pctx_tools(message.id, session=session)
        ) as p:
            tool_name = message.params.name
            meta: dict[str, Any] | None = None
            if tool_name == f"{self.name}_ListFunctions":
                out = (await p.list_functions()).code
            elif tool_name == f"{self.name}_GetFunctionDetails":
                out = (await p.get_function_details(**args)).code
            elif tool_name == f"{self.name}_ExecuteTypescript":
                result = await p.execute_typescript(**args, disclosure=self._pctx_disclosure)
                out = result.markdown()
                meta = result.trace.model_dump().get("events")
            elif tool_name == f"{self.name}_SearchFunctions":
                results = await p.search_functions(**args)
                out = "\n".join(f.model_dump_json() for f in results)
            elif tool_name == f"{self.name}_ExecuteBash":
                result = await p.execute_bash(**args)
                out = result.markdown()
            else:
                return JSONRPCError(
                    id=message.id,
                    error={"code": -32602, "message": f"Unknown pctx tool: {tool_name}"},
                )

        return JSONRPCResponse(
            id=message.id,
            result=CallToolResult(
                content=[TextContent(type="text", text=out, meta=meta)],
                structuredContent=None,
                isError=False,
            ),
        )
