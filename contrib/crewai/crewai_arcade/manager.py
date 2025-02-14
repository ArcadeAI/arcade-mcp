from collections.abc import Iterator
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from arcadepy import Arcade
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse

from crewai_arcade.structured import StructuredTool
from crewai_arcade.utils import tool_definition_to_pydantic_model

TOOL_NAME_SEPARATOR = "_"


@runtime_checkable
class AuthCallbackProtocol(Protocol):
    """Protocol for the auth callback function

    The auth callback function can be optionally provided to the ArcadeToolManager.
    If provided, the function will be called when a tool requires authorization.

    Example:
        >>> def my_custom_auth_handler(**kwargs: dict[str, Any]) -> AuthorizationResponse:
        >>>     tool_name = kwargs["tool_name"]
        >>>     tool_input = kwargs["input"]
        >>>     auth_response = kwargs["auth_response"]
        >>>     # handle the authorization...
        >>>     print(f"\nTo authorize, visit: {auth_response.url}")
        >>>     completed_auth_response = manager.wait_for_auth(auth_response)
        >>>     return completed_auth_response
        >>>
        >>> manager = ArcadeToolManager(auth_callback=my_custom_auth_handler)
    """

    def __call__(self, **kwargs: dict[str, Any]) -> AuthorizationResponse: ...


class ArcadeToolManager:
    """Arcade tool manager for CrewAI

    This manager wraps Arcade tools as CrewAI StructuredTools.
    """

    def __init__(
        self,
        user_id: str,
        client: Optional[Arcade] = None,
        auth_callback: Optional[AuthCallbackProtocol] = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the ArcadeToolManager.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>>
            >>> # retrieve a specific Arcade tool as a CrewAI tool and add it to the manager
            >>> manager.get_tools(tools=["Search.SearchGoogle"])
            >>>
            >>> # retrieve all Arcade tools in a toolkit as CrewAI tools and add them to the manager
            >>> manager.get_tools(toolkits=["Search"])
            >>>
            >>> # retrieve all tools in the manager as CrewAI tools
            >>> manager.get_tools()
            >>>
            >>> # clear and initialize new tools in the manager
            >>> manager.init_tools(tools=["Search.SearchGoogle"], toolkits=["Search"])

        Args:
            user_id: User ID required for tool authorization.
            client: Arcade client instance.
            auth_callback: Optional callback function for handling authorization events in a custom way.
            **kwargs: Additional keyword arguments for the Arcade client if the client is not provided.
        """
        if not client:
            api_key = kwargs.get("api_key")
            base_url = kwargs.get("base_url")
            arcade_kwargs = {"api_key": api_key, "base_url": base_url, **kwargs}
            client = Arcade(**arcade_kwargs)  # type: ignore[arg-type]

        self.user_id = user_id
        self._client = client
        self._tools: dict[str, ToolDefinition] = {}
        self.auth_callback = auth_callback if auth_callback else self._default_auth_callback

        if not isinstance(self.auth_callback, AuthCallbackProtocol):
            raise TypeError(
                "auth_callback must adhere to the AuthCallbackProtocol signature: "
                "def my_custom_auth_handler(**kwargs: dict[str, Any]) -> AuthorizationResponse"
            )

    @property
    def tools(self) -> list[str]:
        return list(self._tools.keys())

    def __iter__(self) -> Iterator[tuple[str, ToolDefinition]]:
        yield from self._tools.items()

    def __len__(self) -> int:
        return len(self._tools)

    def __getitem__(self, tool_name: str) -> ToolDefinition:
        return self._tools[tool_name]

    def init_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
    ) -> None:
        """Initialize the tools in the manager.

        This method clears any existing tools in the manager and replaces them
        with tools and toolkits that are provided. If no tools or toolkits are
        provided, then all tools in the Arcade client will be added.

        Example:
            >>> manager = ArcadeToolManager(user_id="...", api_key="...")
            >>> manager.init_tools(tools=["Search.SearchGoogle"])
            >>> manager.get_tools()

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
        """
        self._tools = self._retrieve_tool_definitions(tools, toolkits)

    def add_tools(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> None:
        """Add tools to the manager.

        This method adds tools to the manager's internal tool list. If no tools or
        toolkits are provided, all tools in the Arcade client will be added.

        Example:
            >>> manager = ArcadeToolManager(user_id="...", api_key="...")
            >>> manager.init_tools(tools=["Search.SearchGoogle"])
            >>> manager.add_tools(tools=["Google.ListEmails"], toolkits=["Slack"])
            >>> manager.get_tools()

        Args:
            tools: List of tool names to add.
            toolkits: List of toolkits to add tools from.
        """
        new_tool_definitions = self._retrieve_tool_definitions(tools, toolkits)
        self._tools.update(new_tool_definitions)

    def get_tools(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> list[StructuredTool]:
        """Retrieves the requested tools or toolkits from the manager.

        This method retrieves the provided tools or toolkits as CrewAI StructuredTools.

        If any provided tools or toolkits are not already present in the
        internal tool list, then they are added to the manager.
        If no tools or toolkits are provided, then all tools in the manager's
        internal tool list are returned as CrewAI StructuredTools.

        Example:
            >>> manager = ArcadeToolManager(user_id="...", api_key="...")
            >>>
            >>> # Retrieve a specific tool as a CrewAI tool
            >>> manager.get_tools(tools=["Search.SearchGoogle"])
            >>>
            >>> # Retrieve all tools in a toolkit as CrewAI tools
            >>> manager.get_tools(toolkits=["Search"])
            >>>
            >>> # Retrieve all tools in the manager as CrewAI tools
            >>> manager.get_tools()

        Args:
            tools: An optional list of tool names to retrieve and wrap. If any of these
                   tools are missing from the internal list, they will be added.
            toolkits: An optional list of toolkits from which to retrieve and wrap tools.
                      Tools from these toolkits will be added if they are not already present.

        Returns:
            A list of StructuredTool instances adapted from the specified tools.
        """
        if tools or toolkits:
            if len(self) == 0:
                self.init_tools(tools, toolkits)
            else:
                new_tools = self._retrieve_tool_definitions(tools, toolkits)
                self._tools.update(new_tools)

        # Wrap the requested tools as CrewAI StructuredTools
        crewai_tools: list[StructuredTool] = []
        for tool_name, tool_def in self:
            crewai_tools.append(self.wrap_tool(tool_name, tool_def))

        return crewai_tools

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
        tool_function = self._create_tool_function(name)

        return StructuredTool.from_function(
            func=tool_function,
            name=name,
            description=description,
            args_schema=args_schema,
        )

    def _retrieve_tool_definitions(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> dict[str, ToolDefinition]:
        """Retrieve tool definitions from the Arcade client.

        This method fetches tool definitions based on the provided tool names or toolkits.
        If no specific tools or toolkits are provided, the method will fetch and return
        all tools available in the Arcade client.

        Args:
            tools: Optional list of tool names to retrieve.
            toolkits: Optional list of toolkits to retrieve tools from.

        Returns:
            A dictionary mapping full tool names to their corresponding ToolDefinition objects
        """
        all_tools: list[ToolDefinition] = []

        if tools:
            single_tools = [self._client.tools.get(name=tool_id) for tool_id in tools]
            all_tools.extend(single_tools)

        if toolkits:
            for tk in toolkits:
                all_tools.extend(self._client.tools.list(toolkit=tk))

        if not tools and not toolkits:
            # Retrieve all Arcade tools.
            page_iterator = self._client.tools.list()
            all_tools.extend(page_iterator)

        tool_definitions: dict[str, ToolDefinition] = {}
        for tool in all_tools:
            full_tool_name = f"{tool.toolkit.name}{TOOL_NAME_SEPARATOR}{tool.name}"
            tool_definitions[full_tool_name] = tool

        return tool_definitions

    def _create_tool_function(self, tool_name: str) -> Callable[..., Any]:
        """Creates a function wrapper for an Arcade tool.

        Args:
            tool_name: The name of the tool to create a function for.

        Returns:
            A callable function that executes the tool.
        """

        def tool_function(**kwargs: Any) -> Any:
            # Handle authorization if required
            if self.requires_auth(tool_name):
                # Get authorization status
                auth_response = self.authorize(tool_name, self.user_id)

                if not self.is_authorized(auth_response.id):  # type: ignore[arg-type]
                    # Handle authorization
                    auth_response = self._call_auth_callback(auth_response, tool_name, **kwargs)
                    if not self.is_authorized(auth_response.id):  # type: ignore[arg-type]
                        return ValueError(
                            f"Authorization failed for {tool_name}. URL: {auth_response.url}"
                        )

            # Execute the tool
            response = self._client.tools.execute(
                tool_name=tool_name,
                input=kwargs,
                user_id=self.user_id,
            )

            tool_error = response.output.error if response.output else None
            if tool_error:
                return str(tool_error)
            if response.success:
                return response.output.value  # type: ignore[union-attr]

            return "Failed to call " + tool_name

        return tool_function

    def requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authorization."""
        cleaned_tool_name = tool_name.replace(".", TOOL_NAME_SEPARATOR)
        tool_def = self._tools.get(cleaned_tool_name)

        if tool_def is None:
            raise ValueError(f"Tool '{tool_name}' not found in this ArcadeToolManager instance")

        if tool_def.requirements is None:
            return False

        return tool_def.requirements.authorization is not None

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """Authorize a user for a tool.

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize.

        Returns:
            AuthorizationResponse
        """
        return self._client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def is_authorized(self, authorization_id: str) -> bool:
        """Check if a tool authorization is complete."""
        return self._client.auth.status(id=authorization_id).status == "completed"

    def wait_for_auth(self, auth_response: AuthorizationResponse) -> AuthorizationResponse:
        """Wait for an authorization process to complete.

        Args:
            auth_response: The authorization response from the initial authorize call.

        Returns:
            AuthorizationResponse with completed status
        """
        return self._client.auth.wait_for_completion(auth_response)

    def _call_auth_callback(
        self,
        auth_response: AuthorizationResponse,
        tool_name: str,
        **kwargs: dict[str, Any],
    ) -> AuthorizationResponse:
        """Helper method to call the auth_callback."""
        callback_kwargs = {
            "tool_name": tool_name,
            "input": kwargs,
            "auth_response": auth_response,
        }
        try:
            return self.auth_callback(**callback_kwargs)
        except KeyError:
            raise TypeError(
                "The ArcadeToolManager's auth_callback must adhere to the AuthCallbackProtocol signature: "
                "def my_custom_auth_handler(**kwargs: dict[str, Any]) -> AuthorizationResponse"
            )

    def _default_auth_callback(self, **kwargs: dict[str, Any]) -> AuthorizationResponse:
        print(f"Please use the following link to authorize: {kwargs['auth_response'].url}")
        completed_auth_response = self.wait_for_auth(kwargs["auth_response"])
        return completed_auth_response
