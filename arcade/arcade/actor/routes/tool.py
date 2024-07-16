from typing import TYPE_CHECKING

from fastapi import APIRouter, Body, Depends, Query
from pydantic import ValidationError

from arcade.actor.common.response import ResponseModel, response_base
from arcade.actor.common.response_code import CustomResponseCode
from arcade.actor.core.depends import get_catalog
from arcade.tool.openai import schema_to_openai_tool

if TYPE_CHECKING:
    from arcade.tool.catalog import ToolCatalog

router = APIRouter()


@router.get(
    "/list",
    summary="List available tools",
)
async def list_tools(catalog: "ToolCatalog" = Depends(get_catalog)) -> ResponseModel:
    """List all available tools"""

    tools = catalog.list_tools()
    return await response_base.success(data=tools)


@router.get("/json", summary="Get the JSON (openai) format of a tool")
async def get_oai_function(
    tool_name: str = Query(..., title="Tool Name", description="The name of the tool"),
    catalog: "ToolCatalog" = Depends(get_catalog),
) -> ResponseModel:
    """Get the OpenAI function format of an tool"""

    try:
        tool = catalog[tool_name]
        json_data = schema_to_openai_tool(tool)

        return await response_base.success(data=json_data)

    except KeyError:
        return await response_base.fail(
            res=CustomResponseCode.HTTP_404,
            data=f"Tool '{tool_name}' not found in the catalog",
        )
    except ValidationError as e:
        return await response_base.fail(res=CustomResponseCode.HTTP_400, data=str(e))
    except Exception as e:
        return await response_base.fail(res=CustomResponseCode.HTTP_500, data=str(e))


@router.post("/execute", summary="Execute a tool")
async def execute_tool(
    tool_name: str = Query(..., title="Tool Name", description="The name of the tool"),
    data: dict[str, str] = Body(
        ..., title="Tool Data", description="The data to execute the tool with"
    ),
    catalog: "ToolCatalog" = Depends(get_catalog),
) -> ResponseModel:
    """Execute a tool"""

    try:
        # TODO use executor and error handling
        tool = catalog.get_tool(tool_name)
    except ValueError:
        return await response_base.fail(
            res=CustomResponseCode.HTTP_404,
            data=f"Tool '{tool_name}' not found in the catalog",
        )

    try:
        result = await tool(**data)  # type: ignore[misc]
        return await response_base.success(data=result)
    except ValidationError as e:
        return await response_base.fail(res=CustomResponseCode.HTTP_400, data=str(e))
    except Exception as e:
        return await response_base.fail(res=CustomResponseCode.HTTP_500, data=str(e))
