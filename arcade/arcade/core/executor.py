import asyncio
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from arcade.core.errors import (
    ToolExecutionError,
    ToolInputError,
    ToolOutputError,
    ToolSerializationError,
)
from arcade.core.response import ToolResponse, tool_response


class ToolExecutor:
    @staticmethod
    async def run(
        func: Callable,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        *args: Any,
        **kwargs: Any,
    ) -> ToolResponse:
        """
        Execute a callable function with validated inputs and outputs via Pydantic models.
        """
        try:
            # serialize the input model
            inputs = await ToolExecutor._serialize_input(input_model, **kwargs)

            # execute the tool function
            if asyncio.iscoroutinefunction(func):
                results = await func(**inputs.model_dump())
            else:
                results = func(**inputs.model_dump())

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, results)

            # return the output
            return tool_response.success(data=output)

        except ToolSerializationError as e:
            return tool_response.fail(msg=str(e))

        except ToolExecutionError as e:
            return tool_response.fail(msg=str(e))

        # if we get here we're in trouble
        # TODO: Debate if this is necessary
        except Exception as e:
            return tool_response.fail(msg=str(e))

    @staticmethod
    async def _serialize_input(input_model: type[BaseModel], **kwargs: Any) -> BaseModel:
        """
        Serialize the input to a tool function.
        """
        try:
            # TODO Logging and telemetry

            # build in the input model to the tool function
            inputs = input_model(**kwargs)

        except ValidationError as e:
            raise ToolInputError from e

        return inputs

    @staticmethod
    async def _serialize_output(output_model: type[BaseModel], results: dict) -> BaseModel:
        """
        Serialize the output of a tool function.
        """
        # TODO how to type this the results object?
        try:
            # TODO Logging and telemetry

            # build the output model
            output = output_model(**{"result": results})

        except ValidationError as e:
            raise ToolOutputError from e

        return output
