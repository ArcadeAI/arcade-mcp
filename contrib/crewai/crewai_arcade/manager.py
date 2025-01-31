from collections.abc import Iterator
from typing import Any, Callable, Optional

from arcadepy import Arcade
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse

from crewai_arcade.structured import StructuredTool
from crewai_arcade.utils import tool_definition_to_pydantic_model


class ArcadeToolManager:
    """Arcade tool manager for CrewAI

    This manager wraps Arcade tools as CrewAI StructuredTools.
    """

    def __init__(
        self,
        user_id: str,
        client: Optional[Arcade] = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the ArcadeToolManager.

        Args:
            client: Arcade client instance.
            user_id: User ID required for tool authorization.
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If user_id is empty or None.
        """

        if not client:
            api_key = kwargs.get("api_key")
            base_url = kwargs.get("base_url")
            client = Arcade(api_key=api_key, base_url=base_url, **kwargs)

        self.user_id = user_id
        self._client = client
        self._tools: dict[str, ToolDefinition] = {}

    def create_tool_function(self, tool_name: str) -> Callable[..., Any]:
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
                auth_response = self.authorize(tool_name, self.user_id)

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
            response = self._client.tools.execute(
                tool_name=tool_name,
                input=kwargs,
                user_id=self.user_id,
            )

            tool_error = response.output.error if response.output else None
            if tool_error:
                return str(tool_error)
            if response.success and response.output:
                return response.output.value

            return "Failed to call " + tool_name

        return tool_function

    def init_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
    ) -> None:
        """Initialize the tools in the manager.

        This will clear any existing tools in the manager.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> manager.init_tools(tools=["Search.SearchGoogle"])
            >>> manager.get_tools()

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
        """
        self._tools = self._retrieve_tool_definitions(tools, toolkits)

    def wrap_tool(self, name: str, tool_def: ToolDefinition) -> StructuredTool:
        """Wrap an Arcade tool as a CrewAI StructuredTool.

        Args:
            name: The name of the tool to wrap.
            tool_def: The definition of the tool to wrap.

        Returns:
            A StructuredTool instance.
        """
        description = tool_def.description or "No description provided."
        args_schema = tool_definition_to_pydantic_model(tool_def)
        tool_function = self.create_tool_function(name)

        return StructuredTool.from_function(
            func=tool_function,
            name=name,
            description=description,
            args_schema=args_schema,
        )

    def get_tools(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> list[StructuredTool]:
        """
        Retrieve and return tools in a customized format.

        This method fetches tools based on the provided tool names or toolkits
        and adapts them to a specific format. If tools or toolkits are specified,
        the manager updates its internal tools using a dictionary update by tool name.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> # Retrieve a specific tool in the desired format
            >>> manager.get_tools(tools=["Search.SearchGoogle"])

        Args:
            tools: An optional list of tool names to include in the retrieval.
            toolkits: An optional list of toolkits from which to retrieve tools.
            kwargs: Additional keyword arguments for customizing the tool wrapper.

        Returns:
            A list of tool instances adapted to the specified format.
        """
        if not self._tools:
            self.init_tools(tools=tools, toolkits=toolkits)
        elif tools or toolkits:
            new_tools = self._retrieve_tool_definitions(tools, toolkits)
            self._tools.update(new_tools)

        return [self.wrap_tool(name, tool_def) for name, tool_def in self._tools.items()]

    def _retrieve_tool_definitions(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> dict[str, ToolDefinition]:
        """
        Retrieve tool definitions from the Arcade client.

        This method fetches tool definitions based on the provided tool names or toolkits.
        If neither tools nor toolkits are specified, it retrieves all available tools.

        Args:
            tools: Optional list of tool names to retrieve.
            toolkits: Optional list of toolkits to retrieve tools from.

        Returns:
            A dictionary mapping full tool names to their corresponding ToolDefinition objects.
        """
        all_tools: list[ToolDefinition] = []
        if tools is not None or toolkits is not None:
            if tools:
                single_tools = [self._client.tools.get(name=tool_id) for tool_id in tools]
                all_tools.extend(single_tools)
            if toolkits:
                for tk in toolkits:
                    all_tools.extend(self._client.tools.list(toolkit=tk))
        else:
            # retrieve all tools
            page_iterator = self._client.tools.list()
            all_tools.extend(page_iterator)

        tool_definitions: dict[str, ToolDefinition] = {}

        for tool in all_tools:
            full_tool_name = f"{tool.toolkit.name}_{tool.name}"
            tool_definitions[full_tool_name] = tool

        return tool_definitions

    @property
    def tools(self) -> list[str]:
        return list(self._tools.keys())

    def __iter__(self) -> Iterator[tuple[str, ToolDefinition]]:
        yield from self._tools.items()

    def __len__(self) -> int:
        return len(self._tools)

    def __getitem__(self, tool_name: str) -> ToolDefinition:
        return self._tools[tool_name]

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """Authorize a user for a tool.

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize.

        Returns:
            AuthorizationResponse
        """
        return self._client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def wait_for_completion(self, auth_response: AuthorizationResponse) -> AuthorizationResponse:
        """Wait for an authorization process to complete.

        Args:
            auth_response: The authorization response from the initial authorize call.

        Returns:
            AuthorizationResponse with completed status
        """
        return self._client.auth.wait_for_completion(auth_response)

    def is_authorized(self, authorization_id: str) -> bool:
        """Check if a tool authorization is complete."""
        return self._client.auth.status(id=authorization_id).status == "completed"

    def requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authorization."""
        tool_def = self._tools.get(tool_name)
        if tool_def is None or tool_def.requirements is None:
            return False
        return tool_def.requirements.authorization is not None
