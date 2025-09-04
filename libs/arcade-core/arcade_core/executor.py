import asyncio
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from arcade_core.api_wrapper.schema import WrapperToolDefinition
from arcade_core.errors import (
    RetryableToolError,
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
    ToolSerializationError,
)
from arcade_core.output import output_factory
from arcade_core.schema import (
    ToolCallLog,
    ToolCallOutput,
    ToolContext,
    ToolDefinition,
)


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
                    message=definition.deprecation_message,
                    level="warning",
                    subtype="deprecation",
                )
            )

        try:
            # Get the result from the tool execution
            tool_response = await ToolExecutor._execute_tool(
                definition=definition,
                func=func,
                input_model=input_model,
                context=context,
                **kwargs,
            )

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, tool_response)

            # return the output
            return output_factory.success(data=output, logs=tool_call_logs)

        except RetryableToolError as e:
            return output_factory.fail_retry(
                message=e.message,
                developer_message=e.developer_message,
                additional_prompt_content=e.additional_prompt_content,
                retry_after_ms=e.retry_after_ms,
            )

        except ToolSerializationError as e:
            return output_factory.fail(
                message=e.message, developer_message=e.developer_message
            )

        # should catch all tool exceptions due to the try/except in the tool decorator
        except ToolRuntimeError as e:
            return output_factory.fail(
                message=e.message,
                developer_message=e.developer_message,
                traceback_info=e.traceback_info(),
            )

        # if we get here we're in trouble
        except Exception as e:
            return output_factory.fail(
                message="Error in execution",
                developer_message=str(e),
                traceback_info=traceback.format_exc(),
            )

    @staticmethod
    async def _execute_tool(
        definition: ToolDefinition,
        func,
        input_model,
        context,
        **kwargs,
    ):
        if isinstance(definition, WrapperToolDefinition):
            try:
                return await ToolExecutor._execute_wrapper_tool(
                    definition, func, input_model, context, **kwargs
                )
            except ToolRuntimeError:
                raise
            except Exception as e:
                raise ToolRuntimeError(
                    message=f"Error in execution of {definition.qualified_name}",
                    developer_message=(
                        f"Error in the execution of {definition.qualified_name}: "
                        f"{type(e).__name__} {e!s}",
                    ),
                ) from e
        else:
            return await ToolExecutor._execute_standard_tool(
                definition, func, input_model, context, **kwargs
            )

    @staticmethod
    async def _execute_standard_tool(
        definition: ToolDefinition,
        func,
        input_model,
        context,
        **kwargs,
    ):
        # serialize the input model
        inputs = await ToolExecutor._serialize_input(input_model, **kwargs)

        # prepare the arguments for the function call
        func_args = inputs.model_dump()

        # inject ToolContext, if the target function supports it
        if definition.input.tool_context_parameter_name is not None:
            func_args[definition.input.tool_context_parameter_name] = context

        # execute the tool function
        if asyncio.iscoroutinefunction(func):
            return await func(**func_args)
        else:
            return func(**func_args)

    @staticmethod
    async def _execute_wrapper_tool(
        definition: WrapperToolDefinition,
        func,
        input_model,
        context,
        **kwargs,
    ):
        return await func(wrapper_tool=definition, context=context, **kwargs)

    @staticmethod
    async def _serialize_input(
        input_model: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        """
        Serialize the input to a tool function.
        """
        try:
            # TODO Logging and telemetry

            # build in the input model to the tool function
            inputs = input_model(**kwargs)

        except ValidationError as e:
            raise ToolInputError(
                message="Error in tool input deserialization",
                developer_message=str(e),
            ) from e

        return inputs

    @staticmethod
    async def _serialize_output(
        output_model: type[BaseModel],
        tool_response: dict,
    ) -> BaseModel:
        """
        Serialize the output of a tool function.
        """
        # TODO how to type this the results object?
        # TODO how to ensure `results` contains only safe (serializable) stuff?
        try:
            # TODO Logging and telemetry

            # build the output model
            output = output_model(**{"result": tool_response})

        except ValidationError as e:
            raise ToolOutputError(
                message="Failed to serialize tool output",
                developer_message=f"Validation error occurred while serializing tool output: {e!s}. "
                f"Please ensure the tool's output matches the expected schema.",
            ) from e

        return output
