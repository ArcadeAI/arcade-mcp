import asyncio
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from arcade.core.errors import (
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
)
from arcade.core.output import ToolOutputFactory
from arcade.core.schema import ToolCallLog, ToolCallOutput, ToolContext, ToolDefinition


class ToolExecutor:
    @staticmethod
    async def run(
        func: Callable,
        definition: ToolDefinition,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        context: ToolContext,
        *args: Any,
        **kwargs: Any,
    ) -> ToolCallOutput:
        """
        Execute a callable function with validated inputs and outputs via Pydantic models.
        """
        # only gathering deprecation log for now
        tool_call_logs = []
        if definition.deprecation_message is not None:
            tool_call_logs.append(
                ToolCallLog(
                    message=definition.deprecation_message, level="warning", subtype="deprecation"
                )
            )

        try:
            # serialize the input model
            inputs = await ToolExecutor._serialize_input(input_model, **kwargs)

            # prepare the arguments for the function call
            func_args = inputs.model_dump()

            # inject ToolContext, if the target function supports it
            if definition.input.tool_context_parameter_name is not None:
                func_args[definition.input.tool_context_parameter_name] = context

            # execute the tool function
            if asyncio.iscoroutinefunction(func):
                results = await func(**func_args)
            else:
                results = func(**func_args)

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, results)

            # return the output
            return ToolOutputFactory.success(data=output, logs=tool_call_logs)

        # should catch all tool exceptions due to the try/except in the tool decorator
        except ToolRuntimeError as e:
            return ToolOutputFactory.fail(error=e, logs=tool_call_logs)

        # if we get here we're in trouble
        except Exception as e:
            error = ToolRuntimeError(
                message="Unexpected error occurred during tool execution",
                developer_message=str(e),
            )
            error.__cause__ = e
            return ToolOutputFactory.fail(error=error, logs=tool_call_logs)

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
            raise ToolInputError(
                message="Error in tool input deserialization", developer_message=str(e)
            ) from e

        return inputs

    @staticmethod
    async def _serialize_output(output_model: type[BaseModel], results: dict) -> BaseModel:
        """
        Serialize the output of a tool function.
        """
        # TODO how to type this the results object?
        # TODO how to ensure `results` contains only safe (serializable) stuff?
        try:
            # TODO Logging and telemetry

            # build the output model
            output = output_model(**{"result": results})

        except ValidationError as e:
            raise ToolOutputError(
                message="Failed to serialize tool output",
                developer_message=f"Validation error occurred while serializing tool output: {e!s}. "
                f"Please ensure the tool's output matches the expected schema.",
            ) from e

        return output
