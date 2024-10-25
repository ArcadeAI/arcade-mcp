from typing import Any, Callable

from arcadepy import NOT_GIVEN, Arcade
from arcadepy.types.shared import ToolDefinition
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

# Check if LangGraph is enabled
LANGGRAPH_ENABLED = True
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    LANGGRAPH_ENABLED = False

# Mapping of Arcade value types to Python types
TYPE_MAPPING = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "array": list,
    "json": dict,
}


def get_python_type(val_type: str) -> Any:
    """Map Arcade value types to Python types.

    Args:
        val_type: The value type as a string.

    Returns:
        Corresponding Python type.
    """
    _type = TYPE_MAPPING.get(val_type)
    if _type is None:
        raise ValueError(f"Invalid value type: {val_type}")
    return _type


def tool_definition_to_pydantic_model(tool_def: ToolDefinition) -> type[BaseModel]:
    """Convert a ToolDefinition's inputs into a Pydantic BaseModel.

    Args:
        tool_def: The ToolDefinition object to convert.

    Returns:
        A Pydantic BaseModel class representing the tool's input schema.
    """
    try:
        fields: dict[str, Any] = {}
        for param in tool_def.inputs.parameters or []:
            param_type = get_python_type(param.value_schema.val_type)
            if param_type == list and param.value_schema.inner_val_type:  # noqa: E721
                inner_type: type[Any] = get_python_type(param.value_schema.inner_val_type)
                param_type = list[inner_type]  # type: ignore[valid-type]
            param_description = param.description or "No description provided."
            default = ... if param.required else None
            fields[param.name] = (
                param_type,
                Field(default=default, description=param_description),
            )
        return create_model(f"{tool_def.name}Args", **fields)
    except ValueError as e:
        raise ValueError(
            f"Error converting {tool_def.name} parameters into pydantic model for langchain: {e}"
        )


def create_tool_function(
    client: Arcade,
    tool_name: str,
    tool_def: ToolDefinition,
    args_schema: type[BaseModel],
    langgraph: bool = False,
) -> Callable:
    """Create a callable function to execute an Arcade tool.

    Args:
        client: The Arcade client instance.
        tool_name: The name of the tool to wrap.
        tool_def: The ToolDefinition of the tool to wrap.
        args_schema: The Pydantic model representing the tool's arguments.
        langgraph: Whether to enable LangGraph-specific behavior.

    Returns:
        A callable function that executes the tool.
    """
    if langgraph and not LANGGRAPH_ENABLED:
        raise ImportError("LangGraph is not installed. Please install it to use this feature.")

    requires_authorization = (
        tool_def.requirements is not None and tool_def.requirements.authorization is not None
    )

    def tool_function(config: RunnableConfig, **kwargs: Any) -> Any:
        """Execute the Arcade tool with the given parameters.

        Args:
            config: RunnableConfig containing execution context.
            **kwargs: Tool input arguments.

        Returns:
            The output from the tool execution.
        """
        user_id = config.get("configurable", {}).get("user_id") if config else None

        if requires_authorization:
            if user_id is None:
                error_message = f"user_id is required to run {tool_name}"
                if langgraph:
                    raise NodeInterrupt(error_message)
                return {"error": error_message}

            # Authorize the user for the tool
            auth_response = client.tools.authorize(tool_name=tool_name, user_id=user_id)
            if auth_response.status != "completed":
                auth_message = (
                    "Please use the following link to authorize: "
                    f"{auth_response.authorization_url}"
                )
                if langgraph:
                    raise NodeInterrupt(auth_message)
                return {"error": auth_message}

        # Execute the tool with provided inputs
        execute_response = client.tools.execute(
            tool_name=tool_name,
            inputs=kwargs,
            user_id=user_id if user_id is not None else NOT_GIVEN,
        )

        if execute_response.success:
            return execute_response.output.value  # type: ignore[union-attr]
        error_message = str(execute_response.output.error)  # type: ignore[union-attr]
        if langgraph:
            raise NodeInterrupt(error_message)
        return {"error": error_message}

    return tool_function


def wrap_arcade_tool(
    client: Arcade,
    tool_name: str,
    tool_def: ToolDefinition,
    langgraph: bool = False,
) -> StructuredTool:
    """Wrap an Arcade `ToolDefinition` as a LangChain `StructuredTool`.

    Args:
        client: The Arcade client instance.
        tool_name: The name of the tool to wrap.
        tool_def: The ToolDefinition object to wrap.
        langgraph: Whether to enable LangGraph-specific behavior.

    Returns:
        A StructuredTool instance representing the Arcade tool.
    """
    description = tool_def.description or "No description provided."

    # Create a Pydantic model for the tool's input arguments
    args_schema = tool_definition_to_pydantic_model(tool_def)

    # Create the action function
    action_func = create_tool_function(
        client=client,
        tool_name=tool_name,
        tool_def=tool_def,
        args_schema=args_schema,
        langgraph=langgraph,
    )

    # Create the StructuredTool instance
    return StructuredTool.from_function(
        func=action_func,
        name=tool_name,
        description=description,
        args_schema=args_schema,
        inject_kwargs={"user_id"},
    )
