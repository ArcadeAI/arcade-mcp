import asyncio
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from arcade.core.errors import (
    RetryableToolError,
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
)
from arcade.core.output import output_factory
from arcade.core.schema import ToolCallOutput, ToolContext, ToolDefinition


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
        try:
            # serialize the input model
            inputs = await ToolExecutor._serialize_input(input_model, **kwargs)

            # prepare the arguments for the function call
            func_args = inputs.model_dump()

            # inject ToolContext, if the target function supports it
            if definition.inputs.tool_context_parameter_name is not None:
                func_args[definition.inputs.tool_context_parameter_name] = context

            # execute the tool function
            if asyncio.iscoroutinefunction(func):
                results = await func(**func_args)
            else:
                results = func(**func_args)

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, results)

            # return the output
            return output_factory.success(data=output)

        except RetryableToolError as e:
            return output_factory.fail_retry(
                message=e.message,
                developer_message=e.developer_message,
                additional_prompt_content=e.additional_prompt_content,
                retry_after_ms=e.retry_after_ms,
            )

        except ToolInputError as e:
            return output_factory.fail(message=e.message, developer_message=e.developer_message)

        except ToolOutputError as e:
            return output_factory.fail(message=e.message, developer_message=e.developer_message)

        except ToolRuntimeError as e:  # Catch any remaining tool-related errors
            return output_factory.fail(
                message=f"Error in execution: {e.message}", developer_message=e.developer_message
            )

        # if we get here we're in trouble
        except Exception as e:
            return output_factory.fail(message="Error in execution", developer_message=str(e))

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
            raise ToolInputError(message="Error in input", developer_message=str(e)) from e

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
            raise ToolOutputError(message="Error in output", developer_message=str(e)) from e

        return output
