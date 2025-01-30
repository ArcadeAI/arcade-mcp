from typing import Any, Callable, Optional

from arcadepy import Arcade
from arcadepy.types import ToolDefinition
from common_arcade.manager import BaseArcadeManager
from common_arcade.utils import tool_definition_to_pydantic_model

from crewai_arcade.structured import StructuredTool


class CrewAIToolManager(BaseArcadeManager):
    """CrewAI-specific implementation of the BaseArcadeManager.

    This manager requires a user_id during initialization as it's needed for tool authorization.
    """

    def __init__(
        self,
        user_id: str,
        client: Optional[Arcade] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the CrewAIToolManager.

        Args:
            client: Arcade client instance.
            user_id: User ID required for tool authorization.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If user_id is empty or None.
        """
        if not user_id:
            raise ValueError("user_id is required for CrewAIToolManager")

        super().__init__(client=client, user_id=user_id, **kwargs)

    def create_tool_function(self, tool_name: str, **kwargs: Any) -> Callable[..., Any]:
        """Creates a function wrapper for an Arcade tool.

        Args:
            tool_name: The name of the tool to create a function for.
            **kwargs: Additional keyword arguments for tool configuration.

        Returns:
            A callable function that executes the tool.
        """

        def tool_function(*args: Any, **kwargs: Any) -> Any:
            # Handle authorization if required
            if self.requires_auth(tool_name):
                # Get authorization status
                auth_response = self.authorize(tool_name, self.user_id)  # type: ignore[arg-type]

                if not self.is_authorized(auth_response.id):  # type: ignore[arg-type]
                    print(
                        f"Authorization required for {tool_name}. Authorization URL: {auth_response.url}"
                    )

                    auth_response = self.wait_for_completion(auth_response)

                    if not self.is_authorized(auth_response.id):  # type: ignore[arg-type]
                        return ValueError(
                            f"Authorization failed for {tool_name}. URL: {auth_response.url}"
                        )

            # Tool execution
            response = self.client.tools.execute(
                tool_name=tool_name,
                input=kwargs,
                user_id=self.user_id,  # type: ignore[arg-type]
            )

            tool_error = response.output.error if response.output else None
            if tool_error:
                return str(tool_error)
            if response.success:
                return response.output.value

            return "Failed to call " + tool_name

        return tool_function

    def wrap_tool(self, name: str, tool_def: ToolDefinition, **kwargs: Any) -> Any:
        """Wrap a tool as a CrewAI StructuredTool.

        Args:
            name: The name of the tool to wrap.
            tool_def: The definition of the tool to wrap.
            **kwargs: Additional keyword arguments for tool configuration.

        Returns:
            A StructuredTool instance.
        """
        description = tool_def.description or "No description provided."
        args_schema = tool_definition_to_pydantic_model(tool_def)
        tool_function = self.create_tool_function(name, **kwargs)

        return StructuredTool.from_function(
            func=tool_function,
            name=name,
            description=description,
            args_schema=args_schema,
        )
