from typing import Any

import httpx

from arcade_core.api_wrapper.errors import WrapperToolExecutionError
from arcade_core.api_wrapper.schema import WrapperToolDefinition
from arcade_core.schema import ToolContext


async def call_wrapper_tool(
    wrapper_tool: WrapperToolDefinition,
    context: ToolContext,
    **tool_inputs,
):
    http_inputs = build_http_inputs(wrapper_tool, tool_inputs, context)
    url, headers, query_strings, body = build_http_params(wrapper_tool, http_inputs)
    return await call_http_endpoint(
        method=wrapper_tool.http_endpoint.http_method,
        url=url,
        headers=headers,
        query_strings=query_strings,
        body=body,
    )


async def call_http_endpoint(
    method: str,
    url: str,
    headers: dict[str, str],
    query_strings: dict[str, str],
    body: dict[str, str],
) -> dict[str, Any]:
    with httpx.Client() as client:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            params=query_strings,
            json=body,
        )
        response.raise_for_status()
        return response.json()


def build_http_inputs(
    wrapper_tool: WrapperToolDefinition,
    tool_inputs: dict[str, Any],
    context: ToolContext,
) -> dict[str, Any]:
    tool_params_by_name = {param.name: param for param in wrapper_tool.input.parameters}

    http_inputs: dict[str, Any] = {}

    for tool_input_name, tool_input_value in tool_inputs.items():
        try:
            tool_param = tool_params_by_name[tool_input_name]
        except KeyError:
            raise WrapperToolExecutionError(
                f"Tool {wrapper_tool.qualified_name} input "
                f"'{tool_input_name}' not found in wrapper tool parameters"
            )

        http_endpoint_input_name = tool_param.http_endpoint_parameter_name

        if http_endpoint_input_name:
            http_inputs[http_endpoint_input_name] = tool_input_value
        else:
            raise WrapperToolExecutionError(
                f"Tool {wrapper_tool.qualified_name} input "
                f"'{tool_input_name}' does not have an HTTP endpoint parameter name"
            )

    auth_token = context.get_auth_token_or_empty()
    if auth_token:
        http_inputs["auth_token"] = auth_token

    for secret in context.secrets:
        http_inputs[secret.key] = secret.value

    return http_inputs


def build_http_params(
    wrapper_tool: WrapperToolDefinition,
    http_inputs: dict[str, str],
) -> tuple[str, dict[str, str]]:
    url = build_endpoint_url(wrapper_tool, http_inputs)
    headers = build_http_headers(wrapper_tool, http_inputs)
    query_strings = build_query_strings(wrapper_tool, http_inputs)
    body = build_http_body(wrapper_tool, http_inputs)
    return url, headers, query_strings, body


def build_endpoint_url(
    wrapper_tool: WrapperToolDefinition,
    http_inputs: dict[str, str],
) -> str:
    url_params: dict[str, str] = {}

    for endpoint_param in wrapper_tool.http_endpoint.parameters:
        if endpoint_param.accepted_as != "path":
            continue

        if endpoint_param.required and endpoint_param.name not in http_inputs:
            raise WrapperToolExecutionError(
                f"Tool {wrapper_tool.qualified_name}'s HTTP endpoint parameter "
                f"'{endpoint_param.name}' is required but not found in HTTP endpoint input values"
            )

        url_params[endpoint_param.name] = http_inputs[endpoint_param.name]

    try:
        return wrapper_tool.http_endpoint.url.format(**url_params)
    except KeyError as e:
        raise WrapperToolExecutionError(
            f"Input values do not include an entry for '{e.args[0]}' which is a "
            f"required f-string parameter for the '{wrapper_tool.http_endpoint.url}' URL "
            f"in {wrapper_tool.qualified_name} tool."
        ) from e


def build_http_headers(
    wrapper_tool: WrapperToolDefinition,
    http_inputs: dict[str, str],
) -> dict[str, str]:
    headers: dict[str, str] = {}
    header_inputs: dict[str, str] = {}

    for endpoint_param in wrapper_tool.http_endpoint.parameters:
        if endpoint_param.accepted_as != "header":
            continue

        if endpoint_param.required and endpoint_param.name not in http_inputs:
            raise WrapperToolExecutionError(
                "Input values do not include an entry for the HTTP header parameter "
                f"'{endpoint_param.name}' in {wrapper_tool.qualified_name} tool."
            )

        header_inputs[endpoint_param.name] = http_inputs[endpoint_param.name]

    for header_key, header_value in wrapper_tool.http_endpoint.headers.items():
        try:
            headers[header_key] = header_value.format(**header_inputs)
        except KeyError as e:
            print(f"\n\n\nHeader inputs: {header_inputs}\n\n\n")
            raise WrapperToolExecutionError(
                f"Input values do not include an entry for '{e.args[0]}' which is a "
                f"required f-string parameter for the '{header_key}' HTTP header in "
                f"{wrapper_tool.qualified_name} tool."
            ) from e

    return headers


def build_query_strings(
    wrapper_tool: WrapperToolDefinition,
    http_inputs: dict[str, str],
) -> dict[str, str]:
    query_strings: dict[str, str] = {}

    for endpoint_param in wrapper_tool.http_endpoint.parameters:
        if endpoint_param.accepted_as != "query":
            continue

        if endpoint_param.required and endpoint_param.name not in http_inputs:
            raise WrapperToolExecutionError(
                f"The '{endpoint_param.name}' HTTP URL query string parameter is required "
                "but does not have a corresponding entry in the input values for the "
                f"{wrapper_tool.qualified_name} tool."
            )

        query_strings[endpoint_param.name] = http_inputs[endpoint_param.name]
    return query_strings


def build_http_body(
    wrapper_tool: WrapperToolDefinition,
    http_inputs: dict[str, str],
) -> dict[str, str]:
    body: dict[str, str] = {}

    for endpoint_param in wrapper_tool.http_endpoint.parameters:
        if endpoint_param.accepted_as != "body":
            continue

        if endpoint_param.required and endpoint_param.name not in http_inputs:
            raise WrapperToolExecutionError(
                f"The '{endpoint_param.name}' HTTP body parameter is required but "
                "does not have a corresponding entry in the input values for the "
                f"{wrapper_tool.qualified_name} tool."
            )

        body[endpoint_param.name] = http_inputs[endpoint_param.name]

    return body
