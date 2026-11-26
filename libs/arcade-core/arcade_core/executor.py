import asyncio
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from arcade_core.errors import (
    InputErrorDetail,
    InputErrorReason,
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
)
from arcade_core.mcp_content import (
    MCPContent,
    convert_content_to_structured_content,
    convert_to_mcp_content,
)
from arcade_core.output import output_factory
from arcade_core.schema import (
    ToolCallLog,
    ToolCallOutput,
    ToolContext,
    ToolDefinition,
)
from arcade_core.tool_result import ToolResult

_CONTENT_BLOCKS = TypeAdapter(list[MCPContent])

# Pydantic error type codes mapped onto the closed InputErrorReason set. Codes
# not listed here (or matched by prefix below) report InputErrorReason.INVALID.
_PYDANTIC_REASONS: dict[str, InputErrorReason] = {
    **dict.fromkeys(
        (
            "missing",
            "missing_argument",
            "missing_keyword_only_argument",
            "missing_positional_only_argument",
        ),
        InputErrorReason.MISSING,
    ),
    **dict.fromkeys(
        ("extra_forbidden", "unexpected_keyword_argument", "unexpected_positional_argument"),
        InputErrorReason.UNEXPECTED,
    ),
    **dict.fromkeys(
        ("string_type", "string_sub_type", "string_unicode"), InputErrorReason.EXPECTED_STRING
    ),
    **dict.fromkeys(
        ("int_type", "int_parsing", "int_parsing_size", "int_from_float"),
        InputErrorReason.EXPECTED_INTEGER,
    ),
    **dict.fromkeys(
        ("float_type", "float_parsing", "decimal_type", "decimal_parsing", "finite_number"),
        InputErrorReason.EXPECTED_NUMBER,
    ),
    **dict.fromkeys(("bool_type", "bool_parsing"), InputErrorReason.EXPECTED_BOOLEAN),
    **dict.fromkeys(
        ("list_type", "tuple_type", "set_type", "frozen_set_type", "iterable_type"),
        InputErrorReason.EXPECTED_ARRAY,
    ),
    **dict.fromkeys(
        ("dict_type", "mapping_type", "model_type", "model_attributes_type", "dataclass_type"),
        InputErrorReason.EXPECTED_OBJECT,
    ),
    **dict.fromkeys(("literal_error", "enum"), InputErrorReason.NOT_ALLOWED),
    **dict.fromkeys(("string_too_short", "too_short"), InputErrorReason.TOO_SHORT),
    **dict.fromkeys(("string_too_long", "too_long"), InputErrorReason.TOO_LONG),
    **dict.fromkeys(
        (
            "greater_than",
            "greater_than_equal",
            "less_than",
            "less_than_equal",
            "multiple_of",
            "decimal_max_digits",
            "decimal_max_places",
            "decimal_whole_digits",
        ),
        InputErrorReason.OUT_OF_RANGE,
    ),
    "string_pattern_mismatch": InputErrorReason.PATTERN_MISMATCH,
    **dict.fromkeys(("value_error", "assertion_error"), InputErrorReason.VALIDATOR_FAILED),
}

# Families of format checks (date_parsing, uuid_version, url_scheme, ...).
_FORMAT_PREFIXES = ("date", "time", "uuid", "url", "json")


def _input_error_reason(error_type: str) -> InputErrorReason:
    reason = _PYDANTIC_REASONS.get(error_type)
    if reason is not None:
        return reason
    if error_type.startswith(_FORMAT_PREFIXES):
        return InputErrorReason.INVALID_FORMAT
    return InputErrorReason.INVALID


def _input_error_details(
    error: ValidationError, input_model: type[BaseModel]
) -> list[InputErrorDetail]:
    """Report each rejected input as a declared parameter and a reason code.

    Only declared parameter names are reported: an undeclared key comes from the
    caller and may itself hold user data, so it is reported without a parameter.
    Nested locations (list indexes, dict keys) are reduced to ``nested=True`` for
    the same reason. Duplicates collapse, so a long list with many bad items
    yields one entry per parameter and reason.
    """
    declared = set(input_model.model_fields)
    details: dict[InputErrorDetail, None] = {}
    for err in error.errors():
        loc = err["loc"]
        head = loc[0] if loc else None
        parameter = head if isinstance(head, str) and head in declared else None
        detail = InputErrorDetail(
            parameter=parameter,
            reason=_input_error_reason(err["type"]),
            nested=parameter is not None and len(loc) > 1,
        )
        details.setdefault(detail, None)
    return list(details)


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
                results = await asyncio.to_thread(func, **func_args)

            content = None
            if isinstance(results, ToolResult):
                content = results.content
                results = results.value

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, results)

            # return the output
            return ToolExecutor._success(output, content, tool_call_logs)

        except ToolRuntimeError as e:
            e.with_context(func.__name__)
            return output_factory.fail(
                message=e.message,
                developer_message=e.developer_message,
                stacktrace=e.stacktrace(),
                additional_prompt_content=getattr(e, "additional_prompt_content", None),
                retry_after_ms=getattr(e, "retry_after_ms", None),
                kind=e.kind,
                can_retry=e.can_retry,
                status_code=e.status_code,
                extra=e.extra,
                input_errors=getattr(e, "input_errors", None),
            )

        # if we get here we're in trouble
        except Exception as e:
            return output_factory.fail(
                message=f"Error in execution of '{func.__name__}'",
                developer_message=str(e),
                stacktrace=traceback.format_exc(),
            )

    @staticmethod
    def _success(
        output: BaseModel, content: list[Any] | None, logs: list[ToolCallLog]
    ) -> ToolCallOutput:
        """
        Build the success output; a ToolResult's content adds the MCP result as `external`.
        """
        tool_output = output_factory.success(data=output, logs=logs)
        if content:
            tool_output.external = ToolExecutor._mcp_result(content, tool_output.value)
        return tool_output

    @staticmethod
    def _mcp_result(content: list[Any], value: Any) -> dict[str, Any]:
        """
        Build the MCP tool result for a ToolResult: its blocks, then the value as JSON text.
        """
        try:
            blocks = _CONTENT_BLOCKS.validate_python(content)
        except ValidationError as e:
            raise ToolOutputError(
                message="Failed to serialize tool output",
                developer_message="ToolResult content must be MCP content blocks: "
                f"{[error['loc'] for error in e.errors()]}",
            ) from e
        result = {
            "content": [
                block.model_dump(mode="json", by_alias=True, exclude_none=True)
                for block in [*blocks, *convert_to_mcp_content(value)]
            ],
            "isError": False,
        }
        structured = convert_content_to_structured_content(value)
        if structured is not None:
            result["structuredContent"] = structured
        return result

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
            # IMPORTANT: do NOT include err["input"] or str(e) anywhere in the
            # surfaced message/developer_message. Pydantic's ``str(e)`` and
            # ``err["input"]`` echo the offending input value verbatim — which
            # may contain user secrets (passwords, tokens, PII). Both fields
            # below intentionally carry only field path + reason + Pydantic
            # error type code, never the rejected value itself.
            #
            # The exception is a tool author's own validator: the ValueError or
            # AssertionError message it raises becomes ``err["msg"]`` and is
            # surfaced as written, so the agent gets the author's hint ("Count
            # must be odd"). Authors must not put the input value in it.
            summary = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc']) or '<root>'}: {err['msg']}"
                for err in e.errors()
            )
            developer_summary = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc']) or '<root>'}[{err['type']}]"
                for err in e.errors()
            )
            raise ToolInputError(
                message=f"Invalid input: {summary}",
                developer_message=f"Pydantic validation failed: {developer_summary}",
                input_errors=_input_error_details(e, input_model),
            ) from None

        except ToolRuntimeError:
            # A validator raising a tool error carries the author's guidance,
            # the same as when it is raised from the tool body.
            raise

        except Exception as e:
            # A declared validator that raises anything other than ValueError
            # or AssertionError escapes Pydantic unwrapped. Its message and
            # traceback may hold the input value, so surface only its type.
            raise ToolInputError(
                message="Invalid input: an input validator failed",
                developer_message=f"Input validator raised {type(e).__name__}",
                input_errors=[InputErrorDetail(reason=InputErrorReason.VALIDATOR_FAILED)],
            ) from None

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
