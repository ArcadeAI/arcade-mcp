import traceback
from typing import Callable

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel, ValidationError

from arcade.actor.core.conf import settings
from arcade.tool.catalog import MaterializedTool
from arcade.tool.executor import ToolExecutor
from arcade.tool.response import ToolResponse, tool_response


def create_endpoint_function(
    name: str,
    description: str,
    func: Callable,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
) -> Callable[..., ToolResponse]:
    """
    Factory function to create endpoint functions with 'frozen' schema and input_model values.
    """

    # dummy function to signal the parameters should be in the
    # body of the request
    def get_input_model(inputs: BaseModel = Body(...)) -> BaseModel:
        return inputs

    async def run(request: Request, inputs: BaseModel = Depends(get_input_model)) -> ToolResponse:
        """
        The function that will be executed when a user sends a POST request
        to a tool endpoint
        """
        try:
            # get the body of the request without parsing and validating it
            # as the executor will do that
            body = await request.json()
            response = await ToolExecutor.run(func, input_model, output_model, **body)

        # TODO: Does this catch validation errors on output?
        except ValidationError as e:
            return await tool_response.fail(msg=str(e))

        except Exception as e:
            return await tool_response.fail(
                msg=str(e),
                data=traceback.format_exc(),
            )
        return response

    run.__name__ = name
    run.__doc__ = description

    # TODO investigate this
    return run  # type: ignore[return-value]


def generate_endpoint(schemas: list[MaterializedTool]) -> APIRouter:
    """
    Generate a HTTP endpoint for each tool definition passed.
    """
    routers = []
    top_level_router = APIRouter(prefix=settings.API_ACTION_STR)

    for schema in schemas:
        router = APIRouter(prefix="/" + schema.meta.module)

        define = schema.definition

        # Create the endpoint function
        run = create_endpoint_function(
            name=define.name,
            description=define.description,
            func=schema.tool,
            input_model=schema.input_model,
            output_model=schema.output_model,
        )

        # Add the endpoint to the FastAPI app
        router.post(
            f"/{define.name}",  # Note: Names from the ToolCatalog are already in PascalCase
            name=define.name,
            summary=define.description,
            tags=[schema.meta.module],
            # TODO investigate this
            response_model=ToolResponse[schema.output_model],  # type: ignore[name-defined]
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
        )(run)

        routers.append(router)
    for router in routers:
        top_level_router.include_router(router)
    return top_level_router
