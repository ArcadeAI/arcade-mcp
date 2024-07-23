import json
import os
from enum import Enum
from typing import Any, Optional

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from typing import Dict, Any, List, Optional, Union
from openai import Client
from openai.resources.chat.completions import ChatCompletion

from arcade.core.catalog import MaterializedTool

PYTHON_TO_JSON_TYPES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

ToolCalls = dict[str, dict[str, Any]]


def python_type_to_json_type(python_type: type[Any]) -> dict[str, Any]:
    """
    Map Python types to JSON Schema types, including handling of
    complex types such as lists and dictionaries.
    """
    if hasattr(python_type, "__origin__"):
        origin = python_type.__origin__

        if origin is list:
            item_type = python_type_to_json_type(python_type.__args__[0])
            return {"type": "array", "items": item_type}
        elif origin is dict:
            value_type = python_type_to_json_type(python_type.__args__[1])
            return {"type": "object", "additionalProperties": value_type}

    elif issubclass(python_type, BaseModel):
        return model_to_json_schema(python_type)

    return PYTHON_TO_JSON_TYPES.get(python_type, "string")


def model_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    Convert a Pydantic model to a JSON schema.
    """
    properties = {}
    required = []
    for field_name, model_field in model.model_fields.items():
        type_json = python_type_to_json_type(model_field.annotation)  # type: ignore[arg-type]
        if isinstance(type_json, dict):
            field_schema = type_json
        else:
            field_schema = {
                "type": type_json,
                "description": model_field.description or "",
            }
        if model_field.default not in [None, PydanticUndefined]:
            if isinstance(model_field.default, Enum):
                field_schema["default"] = model_field.default.value
            else:
                field_schema["default"] = model_field.default
        if model_field.is_required():
            required.append(field_name)
        properties[field_name] = field_schema
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def schema_to_openai_tool(tool: MaterializedTool) -> dict[str, Any]:
    """
    Convert a ToolDefinition object to a JSON schema dictionary in the specified function format.
    """
    input_model_schema = model_to_json_schema(tool.input_model)
    function_schema = {
        "type": "function",
        "function": {
            "name": tool.definition.name,
            "description": tool.definition.description,
            "parameters": input_model_schema,
        },
    }
    return function_schema


class ChatCompletionWrapper:
    def __init__(self, chat_completion: ChatCompletion) -> None:
        self.chat_completion = chat_completion

    def __getattr__(self, name: str) -> Any:
        """
        This method is used to make all the underlying chat_completion methods and attributes available.
        """
        return getattr(self.chat_completion, name)

    def to_request(self) -> dict[str, Any]:
        """
        Converts the chat completion into a request dictionary for openai.Client.chat.completions.create.
        """
        if not self.choices:
            raise ValueError("ChatCompletion object has no choices.")

        # Assuming the first choice's message for simplicity
        first_choice = self.choices[0]
        if not hasattr(first_choice, "message"):
            raise ValueError("Choice object has no 'message' attribute.")

        request_data = {
            "messages": first_choice.message,
            "model": self.model,
            "service_tier": self.service_tier,
            "system_fingerprint": self.chat_completion.system_fingerprint,
            # TODO: Add support for other fields
        }

        # Remove None values
        return {k: v for k, v in request_data.items() if v is not None}

    def called_tool(self) -> bool:
        """
        Returns True if there is a tool_call in the completion object.
        """
        for choice in self.chat_completion.choices:
            if hasattr(choice, "tool_call") and choice.tool_call:
                return True
        return False

    @property
    def tool_args(self) -> ToolCalls:
        """
        Returns the tool arguments from the chat completion object.
        """
        tool_args_list = {}
        message = self.chat_completion.choices[0].message
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_args_list[tool_call.function.name] = json.loads(tool_call.function.arguments)
        return tool_args_list


class EngineClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        api_key = os.environ["OPENAI_API_KEY"] if api_key is None else api_key
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def __getattr__(self, name: str):
        return getattr(self.client, name)

    def call_tool(
        self,
        tools: list[MaterializedTool],
        model: str,
        messages: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = "required",
        parallel_tool_calls: Optional[bool] = False,
        prompt: Optional[str] = "",
        **kwargs: Any,
    ) -> ToolCalls:
        """
        Infer the arguments for a given tool and call the OpenAI API.
        """
        specs = [schema_to_openai_tool(tool) for tool in tools]

        if messages is None and prompt is not None:
            messages = [{"role": "user", "content": prompt}]
        try:
            completion = self.complete(
                model=model,
                messages=messages,
                tools=specs,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                **kwargs,
            )
            if not completion.called_tool:
                raise ValueError("No tool call was made.")

        except (KeyError, IndexError) as e:
            raise ValueError("Invalid response format from OpenAI API.") from e

        return completion.tool_args

    def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ChatCompletionWrapper:
        """
        Call the OpenAI API with the given messages.
        """
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )

        return ChatCompletionWrapper(completion)
