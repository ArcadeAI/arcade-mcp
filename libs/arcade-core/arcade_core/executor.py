import asyncio
import traceback
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from arcade_core.errors import (
    RetryableToolError,
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
    ToolSerializationError,
)
from arcade_core.output import output_factory
from arcade_core.schema import (
    HttpEndpointDefinition,
    ToolCallLog,
    ToolCallOutput,
    ToolContext,
    ToolDefinition,
)


async def call_http_tool(
    definition: ToolDefinition,
    context: ToolContext,
    **tool_inputs: Any,
) -> dict:
    """
    Execute an HTTP-backed tool given by ToolDefinition.http_endpoint.
    """
    if not definition.http_endpoint:
        raise ToolRuntimeError(
            message=f"Tool {definition.fully_qualified_name} is not HTTP-backed",
            developer_message="call_http_tool invoked without an http_endpoint definition",
        )

    http_inputs = _build_http_inputs(definition, tool_inputs, context)
    url, headers, query_strings, body = _build_http_params(
        definition.http_endpoint, http_inputs
    )
    return await _call_http_endpoint(
        method=definition.http_endpoint.http_method,
        url=url,
        headers=headers,
        query_strings=query_strings,
        body=body,
    )


async def _call_http_endpoint(
    method: str,
    url: str,
    headers: dict[str, str],
    query_strings: dict[str, str],
    body: dict[str, Any],
) -> dict:
    async with httpx.AsyncClient() as client:
        request_args: dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": query_strings,
        }

        if headers.get("Content-Type") == "application/json":
            request_args["json"] = body
        else:
            request_args["data"] = body

        response = await client.request(**request_args)
        response.raise_for_status()
        return response.json()


def _build_http_inputs(
    definition: ToolDefinition,
    tool_inputs: dict[str, Any],
    context: ToolContext,
) -> dict[str, Any]:
    tool_params_by_name = {param.name: param for param in definition.input.parameters}

    http_inputs: dict[str, Any] = {}

    for tool_input_name, tool_input_value in tool_inputs.items():
        try:
            tool_param = tool_params_by_name[tool_input_name]
        except KeyError:
            raise ToolRuntimeError(
                message=(
                    f"Tool {definition.fully_qualified_name} input '{tool_input_name}' "
                    "not found in tool parameters"
                ),
                developer_message="Input parameter mismatch with tool definition",
            )

        http_endpoint_input_name = tool_param.http_endpoint_parameter_name

        if http_endpoint_input_name:
            http_inputs[http_endpoint_input_name] = tool_input_value
        else:
            raise ToolRuntimeError(
                message=(
                    f"Tool {definition.fully_qualified_name} input '{tool_input_name}' "
                    "does not have an HTTP endpoint parameter name"
                ),
                developer_message="Missing http_endpoint_parameter_name mapping on input parameter",
            )

    auth_token = context.get_auth_token_or_empty()
    if auth_token:
        http_inputs["auth_token"] = auth_token

    if context.secrets:
        for secret in context.secrets:
            http_inputs[secret.key.lower()] = secret.value

    return http_inputs


def _build_http_params(
    http_endpoint: HttpEndpointDefinition,
    http_inputs: dict[str, str],
) -> tuple[str, dict[str, str], dict[str, str], dict[str, Any]]:
    url = _build_endpoint_url(http_endpoint, http_inputs)
    headers = _build_http_headers(http_endpoint, http_inputs)
    query_strings = _build_query_strings(http_endpoint, http_inputs)
    body = _build_http_body(http_endpoint, http_inputs)
    return url, headers, query_strings, body


def _build_endpoint_url(
    http_endpoint: HttpEndpointDefinition,
    http_inputs: dict[str, str],
) -> str:
    url_params: dict[str, str] = {}

    for endpoint_param in http_endpoint.parameters:
        if endpoint_param.accepted_as != "path":
            continue

        if endpoint_param.required and endpoint_param.name not in http_inputs:
            raise ToolRuntimeError(
                message=(
                    f"HTTP endpoint parameter '{endpoint_param.name}' is required "
                    "but not found in HTTP endpoint input values"
                ),
                developer_message="Missing required path parameter for endpoint URL",
            )

        url_params[endpoint_param.name] = http_inputs[endpoint_param.name]

    try:
        return http_endpoint.url.format(**url_params)
    except KeyError as e:
        raise ToolRuntimeError(
            message=(
                f"Input values do not include an entry for '{e.args[0]}' which is a required "
                f"f-string parameter for the '{http_endpoint.url}' URL"
            ),
            developer_message="URL template expansion failed due to missing parameter",
        ) from e


def _build_http_headers(
    http_endpoint: HttpEndpointDefinition,
    http_inputs: dict[str, str],
) -> dict[str, str]:
    headers: dict[str, str] = {}
    header_inputs: dict[str, str] = {}

    for endpoint_param in http_endpoint.parameters:
        if endpoint_param.accepted_as != "header":
            continue

        if endpoint_param.name not in http_inputs:
            if endpoint_param.required:
                raise ToolRuntimeError(
                    message=(
                        f"Input values do not include an entry for the HTTP header parameter "
                        f"'{endpoint_param.name}'."
                    ),
                    developer_message="Missing required header parameter",
                )
            else:
                continue

        header_inputs[endpoint_param.name] = http_inputs[endpoint_param.name]

    for header_key, header_value in (http_endpoint.headers or {}).items():
        try:
            headers[header_key] = header_value.format(**header_inputs)
        except KeyError as e:
            raise ToolRuntimeError(
                message=(
                    f"Input values do not include an entry for '{e.args[0]}' which is a required "
                    f"f-string parameter for the '{header_key}' HTTP header."
                ),
                developer_message="Header template expansion failed due to missing parameter",
            ) from e

    return headers


def _build_query_strings(
    http_endpoint: HttpEndpointDefinition,
    http_inputs: dict[str, str],
) -> dict[str, str]:
    query_strings: dict[str, str] = {}

    for endpoint_param in http_endpoint.parameters:
        if endpoint_param.accepted_as != "query":
            continue

        if endpoint_param.name not in http_inputs:
            if endpoint_param.required:
                raise ToolRuntimeError(
                    message=(
                        f"The '{endpoint_param.name}' HTTP URL query string parameter is required "
                        "but does not have a corresponding entry in the input values."
                    ),
                    developer_message="Missing required query string parameter",
                )
            else:
                continue

        query_strings[endpoint_param.name] = http_inputs[endpoint_param.name]
    return query_strings


def _build_http_body(
    http_endpoint: HttpEndpointDefinition,
    http_inputs: dict[str, str],
) -> dict[str, Any]:
    body: dict[str, Any] = {}

    for endpoint_param in http_endpoint.parameters:
        if endpoint_param.accepted_as != "body":
            continue

        if endpoint_param.name not in http_inputs:
            if endpoint_param.required:
                raise ToolRuntimeError(
                    message=(
                        f"The '{endpoint_param.name}' HTTP body parameter is required but does not have "
                        "a corresponding entry in the input values."
                    ),
                    developer_message="Missing required body parameter",
                )
            else:
                continue

        body[endpoint_param.name] = http_inputs[endpoint_param.name]

    return body


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
        if definition.http_endpoint is not None:
            return await ToolExecutor._execute_http_tool(
                definition, func, input_model, context, **kwargs
            )
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
    async def _execute_http_tool(
        definition: ToolDefinition,
        func,
        input_model,
        context,
        **kwargs,
    ):
        # func is expected to be call_http_tool
        return await func(definition=definition, context=context, **kwargs)

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
