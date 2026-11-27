import asyncio
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from arcade_core.errors import (
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
            ) from None  # the chained error would repeat the rejected content
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
            # str(e) and the chained error repeat the rejected value, so report
            # only where validation failed and why.
            raise ToolOutputError(
                message="Failed to serialize tool output",
                developer_message="Validation error occurred while serializing tool output: "
                f"{_error_locations(e, output_model)}. "
                f"Please ensure the tool's output matches the expected schema.",
            ) from None

        except ToolRuntimeError:
            # A validator raising a tool error carries the author's guidance,
            # the same as when it is raised from the tool body.
            raise

        except Exception as e:
            # A validator that raises anything other than ValueError or
            # AssertionError escapes Pydantic unwrapped. Its message (a KeyError's
            # is the key) and traceback may hold the output value, so surface
            # only its type, as the input side does.
            raise ToolOutputError(
                message="Failed to serialize tool output",
                developer_message=f"Output validator raised {type(e).__name__}",
            ) from None

        return output


def _error_locations(error: ValidationError, model: type[BaseModel]) -> str:
    """Summarize a validation error as ``location[type]`` entries, without values.

    Pydantic's message, ``input`` and ``ctx`` can repeat the rejected value, so
    they are left out. The location can hold data too: a dict key (or int key)
    from the validated value lands in it. So a location part is shown only when
    it is a field name or alias declared in ``model``'s schema, which is already
    public in the tool definition. Anything else, list indexes included, is
    shown as ``*``. Repeated entries are shown once.

    This runs while the ValidationError is being handled, so an exception here
    would carry it (and the rejected value) as its context. Any failure gives a
    fixed placeholder instead.
    """
    try:
        declared = _declared_names(model)
        entries = [
            (
                ".".join(p if isinstance(p, str) and p in declared else "*" for p in err["loc"])
                or "<root>"
            )
            + f"[{err['type']}]"
            for err in error.errors()
        ]
        return "; ".join(dict.fromkeys(entries))
    except Exception:
        return "<unavailable>"


def _declared_names(model: type[BaseModel]) -> set[str]:
    """Collect every field name and string alias declared anywhere in ``model``."""
    names: set[str] = set()
    seen: set[int] = set()
    nodes: list[Any] = [getattr(model, "__pydantic_core_schema__", None)]
    while nodes:
        node = nodes.pop()
        if isinstance(node, (dict, list, tuple)):
            if id(node) in seen:
                continue
            seen.add(id(node))
        if isinstance(node, dict):
            kind, fields = node.get("type"), node.get("fields")
            if not isinstance(kind, str):
                kind = None
            if kind in ("model-fields", "typed-dict") and isinstance(fields, dict):
                field_items = list(fields.items())
            elif kind == "dataclass-args" and isinstance(fields, list):
                field_items = [(f.get("name"), f) for f in fields if isinstance(f, dict)]
            else:
                field_items = []
            for name, field in field_items:
                names.update(_strings(name))
                if isinstance(field, dict):
                    # A str alias, or AliasChoices/AliasPath as lists of str and int.
                    names.update(_strings(field.get("validation_alias")))
            nodes.extend(node.values())
        elif isinstance(node, (list, tuple)):
            nodes.extend(node)
    return names


def _strings(value: Any) -> list[str]:
    """The str in ``value``, or in a (nested) list of them; ints are list indexes."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []
