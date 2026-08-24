import asyncio
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from arcade_core.errors import (
    ToolInputError,
    ToolOutputError,
    ToolRuntimeError,
)
from arcade_core.output import output_factory
from arcade_core.schema import (
    ToolCallLog,
    ToolCallOutput,
    ToolContext,
    ToolDefinition,
)


def _render_declared_type(value_schema: Any) -> str:
    """Render a parameter's declared type, e.g. ``string`` or ``array[string]``."""
    val_type = str(value_schema.val_type)
    inner = getattr(value_schema, "inner_val_type", None)
    if val_type == "array" and inner:
        return f"array[{inner}]"
    return val_type


def _expected_shape_guidance(
    definition: ToolDefinition | None,
    rejected_fields: list[str],
) -> str:
    """Describe the declared shape of the parameters that were rejected.

    Built strictly from the tool's own ``ToolDefinition`` -- never from the
    submitted values, which may contain secrets or PII (see the note in
    ``_serialize_input``). Only the rejected parameters are described: the
    caller already received the full schema from ``tools/list``, so echoing all
    of it on every failure is noise that buries the actionable part.

    Returns an empty string when there is nothing useful to add, so callers can
    append unconditionally.
    """
    if definition is None or not rejected_fields:
        return ""

    try:
        parameters = {param.name: param for param in definition.input.parameters}
    except AttributeError:
        return ""

    lines: list[str] = []
    for name in rejected_fields:
        param = parameters.get(name)
        if param is None:
            # A rejected key with no declared parameter (e.g. an unexpected
            # extra argument) has no shape to describe.
            continue
        qualifier = "required" if param.required else "optional"
        line = f"  - {param.name} ({_render_declared_type(param.value_schema)}, {qualifier})"
        if param.description:
            line += f": {param.description}"
        enum_values = getattr(param.value_schema, "enum", None)
        if enum_values:
            line += f" [allowed values: {', '.join(str(v) for v in enum_values)}]"
        lines.append(line)

    if not lines:
        return ""

    rendered = "\n".join(lines)
    return f"Expected:\n{rendered}\n\nFix these arguments and call the tool again."


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
            inputs = await ToolExecutor._serialize_input(input_model, definition, **kwargs)

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

            # serialize the output model
            output = await ToolExecutor._serialize_output(output_model, results)

            # return the output
            return output_factory.success(data=output, logs=tool_call_logs)

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
            )

        # if we get here we're in trouble
        except Exception as e:
            return output_factory.fail(
                message=f"Error in execution of '{func.__name__}'",
                developer_message=str(e),
                stacktrace=traceback.format_exc(),
            )

    @staticmethod
    async def _serialize_input(
        input_model: type[BaseModel],
        definition: ToolDefinition | None = None,
        /,
        **kwargs: Any,
    ) -> BaseModel:
        """
        Serialize the input to a tool function.

        ``input_model`` and ``definition`` are positional-only: ``**kwargs`` holds
        the caller-supplied tool arguments, and a tool is free to declare a
        parameter named ``definition`` (or ``input_model``). Positional-only
        placement keeps such an argument in ``kwargs`` instead of colliding with
        these parameters.

        ``definition`` is optional enrichment used to describe the expected shape
        of rejected parameters; validation works without it.
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
            summary = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc']) or '<root>'}: {err['msg']}"
                for err in e.errors()
            )
            developer_summary = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc']) or '<root>'}[{err['type']}]"
                for err in e.errors()
            )
            # Field paths of the rejected arguments, de-duplicated in the order
            # Pydantic reported them. Only the top-level name is used, since that
            # is what maps onto a declared tool parameter.
            rejected_fields: list[str] = []
            for err in e.errors():
                if not err["loc"]:
                    continue
                field = str(err["loc"][0])
                if field not in rejected_fields:
                    rejected_fields.append(field)

            message = f"Invalid input: {summary}"
            guidance = _expected_shape_guidance(definition, rejected_fields)
            if guidance:
                message = f"{message}\n\n{guidance}"

            raise ToolInputError(
                message=message,
                developer_message=f"Pydantic validation failed: {developer_summary}",
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
