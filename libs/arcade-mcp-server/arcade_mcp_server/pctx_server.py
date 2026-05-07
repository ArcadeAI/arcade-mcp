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
from collections.abc import Awaitable
from typing import Any, Callable

import jsonschema
from pctx_client import AsyncTool as _PctxAsyncToolBase
from pctx_client import Pctx
from pctx_client.descriptions import get_tool_description
from pctx_client.models import (
    ExecuteBashInput,
    ExecuteTypescriptInput,
    GetFunctionDetailsInput,
    ToolDisclosure,
    ToolDisclosureName,
    ToolName,
)
from pydantic import BaseModel, Field

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
            )
        )
    return tools


class PctxTool(_PctxAsyncToolBase):
    """
    AsyncTool variant for cases where the input/output contracts are
    already given as JSON Schema dicts rather than Pydantic models.

    The base _PctxAsyncToolBase expects `input_schema` to be a `type[BaseModel]` and
    validates with `model_validate`, and treats `output_schema` as a Python
    type fed to `TypeAdapter`. When the schemas originate from an external
    source (a remote tool registry, an OpenAPI spec, an MCP server, a
    hand-authored JSON Schema, etc.) there is no Python type to attach —
    converting JSON Schema back into a synthetic BaseModel is lossy and
    awkward for `$ref`/`oneOf`/recursive definitions.

    This subclass keeps the dicts as-is and validates them directly with
    `jsonschema`, so the JSON Schema stays the source of truth end-to-end.
    """

    input_schema: dict[str, Any] | None = Field(
        default=None, description="JSON Schema for tool input."
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="JSON Schema for tool output."
    )

    def validate_input(self, obj: Any) -> None:
        if self.input_schema is not None:
            jsonschema.validate(obj, self.input_schema)

    def validate_output(self, obj: Any) -> None:
        if self.output_schema is not None:
            jsonschema.validate(obj, self.output_schema)

    def input_json_schema(self) -> dict[str, Any] | None:
        return self.input_schema

    def output_json_schema(self) -> dict[str, Any] | None:
        return self.output_schema


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

    async def _build_pctx_tools(
        self, req_id: RequestId, session: ServerSession | None
    ) -> list[PctxTool]:
        arcade_tools = await self._tool_manager.list_tools()

        pctx_tools = []
        for t in arcade_tools:
            # Arcade tool names are exposed as `<server_name>_<tool_name>`
            split_name = t.name.split("_", maxsplit=1)
            if len(split_name) == 2:
                namespace, name = split_name
            else:
                namespace, name = "tools", split_name

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

            class _CoroutineTool(PctxTool):
                """Concrete asynchronous tool wrapping a coroutine"""

                _coroutine: Callable[..., Awaitable[Any]] = staticmethod(_invoke_tool)

                async def _ainvoke(self, **kwargs: Any) -> Any:
                    return await self._coroutine(**kwargs)

            pctx_tools.append(
                _CoroutineTool(
                    namespace=namespace,
                    name=name,
                    description=t.description,
                    input_schema=t.inputSchema,
                    output_schema=t.outputSchema,
                )
            )
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
            if tool_name == "list_functions":
                out = (await p.list_functions()).code
            elif tool_name == "get_function_details":
                out = (await p.get_function_details(**args)).code
            elif tool_name == "execute_typescript":
                result = await p.execute_typescript(**args)
                out = result.markdown()
            elif tool_name == "search_functions":
                results = await p.search_functions(**args)
                out = "\n".join(f.model_dump_json() for f in results)
            elif tool_name == "execute_bash":
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
                content=[TextContent(type="text", text=out)], structuredContent=None, isError=False
            ),
        )
