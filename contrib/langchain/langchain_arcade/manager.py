import os
import warnings
from collections.abc import Iterator
from typing import Any, Optional, Union

from arcadepy import NOT_GIVEN, Arcade, AsyncArcade
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse
from langchain_core.tools import StructuredTool

from langchain_arcade._utilities import wrap_arcade_tool

ClientType = Union[Arcade, AsyncArcade]


class LangChainToolManager:
    """
    Base tool manager for LangChain framework.
    Provides a common interface for both synchronous and asynchronous tool managers.

    This class handles the storage and retrieval of tool definitions and provides
    common functionality used by both synchronous and asynchronous implementations.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    @property
    def tools(self) -> list[str]:
        """
        Get the list of tools by name in the manager.

        Returns:
            A list of tool names (strings) currently stored in the manager.
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """Return the number of tools in the manager."""
        return len(self._tools)

    def _get_client_config(self, **kwargs: Any) -> dict[str, Any]:
        """
        Get the client configurations from environment variables and kwargs.

        If api_key or base_url are in the kwargs, they will be used.
        Otherwise, the environment variables ARCADE_API_KEY and ARCADE_BASE_URL will be used.
        If both are provided, the kwargs will take precedence.

        Args:
            **kwargs: Keyword arguments that may contain api_key and base_url.

        Returns:
            A dictionary of client configuration parameters.
        """
        client_kwargs = {
            "api_key": kwargs.get("api_key", os.getenv("ARCADE_API_KEY")),
        }
        base_url = kwargs.get("base_url", os.getenv("ARCADE_BASE_URL"))
        if base_url:
            client_kwargs["base_url"] = base_url
        return client_kwargs

    def _get_tool_definition(self, tool_name: str) -> ToolDefinition:
        """
        Get a tool definition by name, raising an error if not found.

        Args:
            tool_name: The name of the tool to retrieve.

        Returns:
            The ToolDefinition for the specified tool.

        Raises:
            ValueError: If the tool is not found in the manager.
        """
        try:
            return self._tools[tool_name]
        except KeyError:
            raise ValueError(f"Tool '{tool_name}' not found in this manager instance")

    def __getitem__(self, tool_name: str) -> ToolDefinition:
        """
        Get a tool definition by name using dictionary-like access.

        Args:
            tool_name: The name of the tool to retrieve.

        Returns:
            The ToolDefinition for the specified tool.

        Raises:
            ValueError: If the tool is not found in the manager.
        """
        return self._get_tool_definition(tool_name)

    def requires_auth(self, tool_name: str) -> bool:
        """
        Check if a tool requires authorization.

        Args:
            tool_name: The name of the tool to check.

        Returns:
            True if the tool requires authorization, False otherwise.
        """
        tool_def = self._get_tool_definition(tool_name)
        if tool_def.requirements is None:
            return False
        return tool_def.requirements.authorization is not None


class ToolManager(LangChainToolManager):
    """
    Synchronous Arcade tool manager for LangChain framework.

    This class wraps Arcade tools as LangChain StructuredTool objects for integration
    with synchronous operations.

    Example:
        >>> manager = ToolManager(api_key="your-api-key")
        >>> # Initialize with specific tools and toolkits
        >>> manager.init_tools(tools=["Search.SearchGoogle"], toolkits=["Weather"])
        >>> # Get tools as LangChain StructuredTools
        >>> langchain_tools = manager.to_langchain()
        >>> # Handle authorization for tools that require it
        >>> if manager.requires_auth("Search.SearchGoogle"):
        >>>     auth_response = manager.authorize("Search.SearchGoogle", "user_123")
        >>>     manager.wait_for_auth(auth_response.id)
    """

    def __init__(self, client: Optional[Arcade] = None, **kwargs: Any) -> None:
        """
        Initialize the ToolManager.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> # or with an existing client
            >>> client = Arcade(api_key="your-api-key")
            >>> manager = ToolManager(client=client)

        Args:
            client: Optional Arcade client instance. If not provided, one will be created.
            **kwargs: Additional keyword arguments to pass to the Arcade client if creating one.
                      Common options include api_key and base_url.
        """
        super().__init__()
        if client is None:
            client_kwargs = self._get_client_config(**kwargs)
            client = Arcade(**client_kwargs)
        self._client = client

    @property
    def definitions(self) -> list[ToolDefinition]:
        """
        Get the list of tool definitions in the manager.

        Returns:
            A list of ToolDefinition objects currently stored in the manager.
        """
        return list(self._tools.values())

    def __iter__(self) -> Iterator[tuple[str, ToolDefinition]]:
        """
        Iterate over the tools in the manager as (name, definition) pairs.

        Returns:
            Iterator over (tool_name, tool_definition) tuples.
        """
        yield from self._tools.items()

    def to_langchain(
        self, use_interrupts: bool = True, use_underscores: bool = True
    ) -> list[StructuredTool]:
        """
        Get the tools in the manager as LangChain StructuredTool objects.

        Args:
            use_interrupts: Whether to use interrupts for the tool. This is useful
                           for LangGraph workflows where you need to handle tool
                           authorization through state transitions.
            use_underscores: Whether to use underscores for the tool name instead of periods.
                            For example, "Search_SearchGoogle" vs "Search.SearchGoogle".
                            Some model providers like OpenAI work better with underscores.

        Returns:
            List of StructuredTool instances ready to use with LangChain.
        """
        tool_map = _create_tool_map(self.definitions, use_underscores=use_underscores)
        return [
            wrap_arcade_tool(self._client, tool_name, definition, langgraph=use_interrupts)
            for tool_name, definition in tool_map.items()
        ]

    def init_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        raise_on_empty: bool = True,
    ) -> list[StructuredTool]:
        """
        Initialize the tools in the manager and return them as LangChain tools.

        This will clear any existing tools in the manager and replace them with
        the new tools specified by the tools and toolkits parameters.

        Note: In version 2.0+, this method returns a list of StructuredTool objects.
        In earlier versions, it returned None.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> langchain_tools = manager.init_tools(tools=["Search.SearchGoogle"])
            >>> # Use these tools with a LangChain chain or agent
            >>> agent = Agent(tools=langchain_tools, llm=llm)

        Args:
            tools: Optional list of specific tool names to include (e.g., "Search.SearchGoogle").
            toolkits: Optional list of toolkit names to include all tools from (e.g., "Search").
            limit: Optional limit on the number of tools to retrieve per request.
            offset: Optional offset for paginated requests.
            raise_on_empty: Whether to raise an error if no tools or toolkits are provided.

        Returns:
            List of StructuredTool instances ready to use with LangChain.

        Raises:
            ValueError: If no tools or toolkits are provided and raise_on_empty is True.
        """
        tools_list = self._retrieve_tool_definitions(tools, toolkits, raise_on_empty, limit, offset)
        self._tools = _create_tool_map(tools_list)
        return self.to_langchain()

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """
        Authorize a user for a specific tool.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> manager.init_tools(tools=["Gmail.SendEmail"])
            >>> auth_response = manager.authorize("Gmail.SendEmail", "user_123")
            >>> # auth_response.auth_url contains the URL for the user to authorize

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize. This should be a unique identifier for the user.

        Returns:
            AuthorizationResponse containing authorization details, including the auth_url
            that should be presented to the user to complete authorization.
        """
        return self._client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def is_authorized(self, authorization_id: str) -> bool:
        """
        Check if a tool authorization is complete.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> auth_response = manager.authorize("Gmail.SendEmail", "user_123")
            >>> # After user completes authorization
            >>> is_complete = manager.is_authorized(auth_response.id)

        Args:
            authorization_id: The authorization ID to check. This can be the full AuthorizationResponse
                             object or just the ID string.

        Returns:
            True if the authorization is completed, False otherwise.
        """
        # Handle case where entire AuthorizationResponse object is passed
        if hasattr(authorization_id, "id"):
            authorization_id = authorization_id.id

        response = self._client.auth.status(id=authorization_id)
        if response:
            return response.status == "completed"
        return False

    def wait_for_auth(self, authorization_id: str) -> AuthorizationResponse:
        """
        Wait for a tool authorization to complete. This method blocks until
        the authorization is complete or fails.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> auth_response = manager.authorize("Gmail.SendEmail", "user_123")
            >>> # Share auth_response.auth_url with the user
            >>> # Wait for the user to complete authorization
            >>> completed_auth = manager.wait_for_auth(auth_response.id)

        Args:
            authorization_id: The authorization ID to wait for. This can be the full
                             AuthorizationResponse object or just the ID string.

        Returns:
            AuthorizationResponse with the completed authorization details.
        """
        # Handle case where entire AuthorizationResponse object is passed
        if hasattr(authorization_id, "id"):
            authorization_id = authorization_id.id

        return self._client.auth.wait_for_completion(authorization_id)

    def _retrieve_tool_definitions(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        raise_on_empty: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[ToolDefinition]:
        """
        Retrieve tool definitions from the Arcade client, accounting for pagination.

        Args:
            tools: Optional list of specific tool names to include.
            toolkits: Optional list of toolkit names to include all tools from.
            raise_on_empty: Whether to raise an error if no tools or toolkits are provided.
            limit: Optional limit on the number of tools to retrieve per request.
            offset: Optional offset for paginated requests.

        Returns:
            List of ToolDefinition instances.

        Raises:
            ValueError: If no tools or toolkits are provided and raise_on_empty is True.
        """
        all_tools: list[ToolDefinition] = []

        # If no specific tools or toolkits are requested, raise an error.
        if not tools and not toolkits:
            if raise_on_empty:
                raise ValueError("No tools or toolkits provided to retrieve tool definitions.")
            return []

        # Retrieve individual tools if specified
        if tools:
            for tool_id in tools:
                single_tool = self._client.tools.get(name=tool_id)
                all_tools.append(single_tool)

        # Retrieve tools from specified toolkits
        if toolkits:
            for tk in toolkits:
                # Convert None to NOT_GIVEN for Stainless client
                paginated_tools = self._client.tools.list(
                    toolkit=tk,
                    limit=limit if limit is not None else NOT_GIVEN,
                    offset=offset if offset is not None else NOT_GIVEN,
                )
                all_tools.extend(paginated_tools)

        return all_tools

    def add_tool(self, tool_name: str) -> None:
        """
        Add a single tool to the manager by name.

        Unlike init_tools(), this method preserves existing tools in the manager
        and only adds the specified tool.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> manager.add_tool("Gmail.SendEmail")
            >>> manager.add_tool("Search.SearchGoogle")
            >>> # Get all tools including newly added ones
            >>> all_tools = manager.to_langchain()

        Args:
            tool_name: The fully qualified name of the tool to add (e.g., "Search.SearchGoogle")

        Raises:
            ValueError: If the tool cannot be found
        """
        tool = self._client.tools.get(name=tool_name)
        self._tools.update(_create_tool_map([tool]))

    def add_toolkit(
        self, toolkit_name: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> None:
        """
        Add all tools from a specific toolkit to the manager.

        Unlike init_tools(), this method preserves existing tools in the manager
        and only adds the tools from the specified toolkit.

        Example:
            >>> manager = ToolManager(api_key="your-api-key")
            >>> manager.add_toolkit("Gmail")
            >>> manager.add_toolkit("Search")
            >>> # Get all tools including newly added ones
            >>> all_tools = manager.to_langchain()

        Args:
            toolkit_name: The name of the toolkit to add (e.g., "Search")
            limit: Optional limit on the number of tools to retrieve per request
            offset: Optional offset for paginated requests

        Raises:
            ValueError: If the toolkit cannot be found or has no tools
        """
        tools = self._client.tools.list(
            toolkit=toolkit_name,
            limit=NOT_GIVEN if limit is None else limit,
            offset=NOT_GIVEN if offset is None else offset,
        )

        for tool in tools:
            self._tools.update(_create_tool_map([tool]))

    def get_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        langgraph: bool = True,
    ) -> list[StructuredTool]:
        """
        DEPRECATED: Return the tools in the manager as LangChain StructuredTool objects.

        This method is deprecated and will be removed in a future major version.
        Please use `init_tools()` to initialize tools and `to_langchain()` to convert them.

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            langgraph: Whether to use LangGraph-specific behavior
                such as NodeInterrupts for auth.

        Returns:
            List of StructuredTool instances.
        """
        warnings.warn(
            "get_tools() is deprecated and will be removed in the next major version. "
            "Please use init_tools() to initialize tools and to_langchain() to convert them.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Support existing usage pattern
        if tools or toolkits:
            self.init_tools(tools=tools, toolkits=toolkits)

        return self.to_langchain(use_interrupts=langgraph)


class ArcadeToolManager(ToolManager):
    """
    Deprecated alias for ToolManager.

    ArcadeToolManager is deprecated and will be removed in the next major version.
    Please use ToolManager instead.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "ArcadeToolManager is deprecated and will be removed in the next major version. "
            "Please use ToolManager instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


class AsyncToolManager(LangChainToolManager):
    """
    Async version of Arcade tool manager for LangChain framework.

    This class wraps Arcade tools as LangChain StructuredTool objects for integration
    with asynchronous operations.

    Example:
        >>> manager = AsyncToolManager(api_key="your-api-key")
        >>> # Initialize with specific tools and toolkits
        >>> await manager.init_tools(tools=["Search.SearchGoogle"], toolkits=["Weather"])
        >>> # Get tools as LangChain StructuredTools
        >>> langchain_tools = await manager.to_langchain()
        >>> # Handle authorization for tools that require it
        >>> if manager.requires_auth("Search.SearchGoogle"):
        >>>     auth_response = await manager.authorize("Search.SearchGoogle", "user_123")
        >>>     await manager.wait_for_auth(auth_response.id)
    """

    def __init__(
        self,
        client: Optional[AsyncArcade] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the AsyncToolManager.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> # or with an existing client
            >>> client = AsyncArcade(api_key="your-api-key")
            >>> manager = AsyncToolManager(client=client)

        Args:
            client: Optional AsyncArcade client instance. If not provided, one will be created.
            **kwargs: Additional keyword arguments to pass to the AsyncArcade client if creating one.
                      Common options include api_key and base_url.
        """
        super().__init__()
        if not client:
            client_kwargs = self._get_client_config(**kwargs)
            client = AsyncArcade(**client_kwargs)
        self._client = client

    @property
    def definitions(self) -> list[ToolDefinition]:
        """
        Get the list of tool definitions in the manager.

        Returns:
            A list of ToolDefinition objects currently stored in the manager.
        """
        return list(self._tools.values())

    def __iter__(self) -> Iterator[tuple[str, ToolDefinition]]:
        """
        Iterate over the tools in the manager as (name, definition) pairs.

        Returns:
            Iterator over (tool_name, tool_definition) tuples.
        """
        yield from self._tools.items()

    async def init_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        raise_on_empty: bool = True,
    ) -> list[StructuredTool]:
        """
        Initialize the tools in the manager asynchronously and return them as LangChain tools.

        This will clear any existing tools in the manager and replace them with
        the new tools specified by the tools and toolkits parameters.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> langchain_tools = await manager.init_tools(tools=["Search.SearchGoogle"])
            >>> # Use these tools with a LangChain chain or agent
            >>> agent = Agent(tools=langchain_tools, llm=llm)

        Args:
            tools: Optional list of specific tool names to include (e.g., "Search.SearchGoogle").
            toolkits: Optional list of toolkit names to include all tools from (e.g., "Search").
            limit: Optional limit on the number of tools to retrieve per request.
            offset: Optional offset for paginated requests.
            raise_on_empty: Whether to raise an error if no tools or toolkits are provided.

        Returns:
            List of StructuredTool instances ready to use with LangChain.

        Raises:
            ValueError: If no tools or toolkits are provided and raise_on_empty is True.
        """
        tools_list = await self._retrieve_tool_definitions(
            tools, toolkits, raise_on_empty, limit, offset
        )
        self._tools.update(_create_tool_map(tools_list))
        return await self.to_langchain()

    async def to_langchain(
        self, use_interrupts: bool = True, use_underscores: bool = True
    ) -> list[StructuredTool]:
        """
        Get the tools in the manager as LangChain StructuredTool objects asynchronously.

        Args:
            use_interrupts: Whether to use interrupts for the tool. This is useful
                           for LangGraph workflows where you need to handle tool
                           authorization through state transitions.
            use_underscores: Whether to use underscores for the tool name instead of periods.
                            For example, "Search_SearchGoogle" vs "Search.SearchGoogle".
                            Some model providers like OpenAI work better with underscores.

        Returns:
            List of StructuredTool instances ready to use with LangChain.
        """
        tool_map = _create_tool_map(self.definitions, use_underscores=use_underscores)
        return [
            wrap_arcade_tool(self._client, tool_name, definition, langgraph=use_interrupts)
            for tool_name, definition in tool_map.items()
        ]

    async def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """
        Authorize a user for a tool.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> await manager.init_tools(tools=["Gmail.SendEmail"])
            >>> auth_response = await manager.authorize("Gmail.SendEmail", "user_123")
            >>> # auth_response.auth_url contains the URL for the user to authorize

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize. This should be a unique identifier for the user.

        Returns:
            AuthorizationResponse containing authorization details, including the auth_url
            that should be presented to the user to complete authorization.
        """
        return await self._client.tools.authorize(tool_name=tool_name, user_id=user_id)

    async def is_authorized(self, authorization_id: str) -> bool:
        """
        Check if a tool authorization is complete.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> auth_response = await manager.authorize("Gmail.SendEmail", "user_123")
            >>> # After user completes authorization
            >>> is_complete = await manager.is_authorized(auth_response.id)

        Args:
            authorization_id: The authorization ID to check. This can be the full AuthorizationResponse
                             object or just the ID string.

        Returns:
            True if the authorization is completed, False otherwise.
        """
        # Handle case where entire AuthorizationResponse object is passed
        if hasattr(authorization_id, "id"):
            authorization_id = authorization_id.id

        auth_status = await self._client.auth.status(id=authorization_id)
        return auth_status.status == "completed"

    async def wait_for_auth(self, authorization_id: str) -> AuthorizationResponse:
        """
        Wait for a tool authorization to complete. This method blocks until
        the authorization is complete or fails.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> auth_response = await manager.authorize("Gmail.SendEmail", "user_123")
            >>> # Share auth_response.auth_url with the user
            >>> # Wait for the user to complete authorization
            >>> completed_auth = await manager.wait_for_auth(auth_response.id)

        Args:
            authorization_id: The authorization ID to wait for. This can be the full
                             AuthorizationResponse object or just the ID string.

        Returns:
            AuthorizationResponse with the completed authorization details.
        """
        # Handle case where entire AuthorizationResponse object is passed
        if hasattr(authorization_id, "id"):
            authorization_id = authorization_id.id

        return await self._client.auth.wait_for_completion(authorization_id)

    async def _retrieve_tool_definitions(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        raise_on_empty: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[ToolDefinition]:
        """
        Retrieve tool definitions asynchronously from the Arcade client, accounting for pagination.

        Args:
            tools: Optional list of specific tool names to include.
            toolkits: Optional list of toolkit names to include all tools from.
            raise_on_empty: Whether to raise an error if no tools or toolkits are provided.
            limit: Optional limit on the number of tools to retrieve per request.
            offset: Optional offset for paginated requests.

        Returns:
            List of ToolDefinition instances.

        Raises:
            ValueError: If no tools or toolkits are provided and raise_on_empty is True.
        """
        all_tools: list[ToolDefinition] = []

        # If no specific tools or toolkits are requested, raise an error.
        if not tools and not toolkits:
            if raise_on_empty:
                raise ValueError("No tools or toolkits provided to retrieve tool definitions.")
            return []

        # First, gather single tools if the user specifically requested them.
        if tools:
            for tool_id in tools:
                # ToolsResource.get(...) returns a single ToolDefinition.
                single_tool = await self._client.tools.get(name=tool_id)
                all_tools.append(single_tool)

        # Next, gather tool definitions from any requested toolkits.
        if toolkits:
            for tk in toolkits:
                # Convert None to NOT_GIVEN for Stainless client
                paginated_tools = await self._client.tools.list(
                    toolkit=tk,
                    limit=NOT_GIVEN if limit is None else limit,
                    offset=NOT_GIVEN if offset is None else offset,
                )
                async for tool in paginated_tools:
                    all_tools.append(tool)

        return all_tools

    async def add_tool(self, tool_name: str) -> None:
        """
        Add a single tool to the manager by name.

        Unlike init_tools(), this method preserves existing tools in the manager
        and only adds the specified tool.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> await manager.add_tool("Gmail.SendEmail")
            >>> await manager.add_tool("Search.SearchGoogle")
            >>> # Get all tools including newly added ones
            >>> all_tools = await manager.to_langchain()

        Args:
            tool_name: The fully qualified name of the tool to add (e.g., "Search.SearchGoogle")

        Raises:
            ValueError: If the tool cannot be found
        """
        tool = await self._client.tools.get(name=tool_name)
        self._tools.update(_create_tool_map([tool]))

    async def add_toolkit(
        self, toolkit_name: str, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> None:
        """
        Add all tools from a specific toolkit to the manager.

        Unlike init_tools(), this method preserves existing tools in the manager
        and only adds the tools from the specified toolkit.

        Example:
            >>> manager = AsyncToolManager(api_key="your-api-key")
            >>> await manager.add_toolkit("Gmail")
            >>> await manager.add_toolkit("Search")
            >>> # Get all tools including newly added ones
            >>> all_tools = await manager.to_langchain()

        Args:
            toolkit_name: The name of the toolkit to add (e.g., "Search")
            limit: Optional limit on the number of tools to retrieve per request
            offset: Optional offset for paginated requests

        Raises:
            ValueError: If the toolkit cannot be found or has no tools
        """
        paginated_tools = await self._client.tools.list(
            toolkit=toolkit_name,
            limit=NOT_GIVEN if limit is None else limit,
            offset=NOT_GIVEN if offset is None else offset,
        )

        async for tool in paginated_tools:
            self._tools.update(_create_tool_map([tool]))

    async def get_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        langgraph: bool = True,
    ) -> list[StructuredTool]:
        """
        DEPRECATED: Return the tools in the manager as LangChain StructuredTool objects.

        This method is deprecated and will be removed in a future major version.
        Please use `init_tools()` to initialize tools and `to_langchain()` to convert them.

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            langgraph: Whether to use LangGraph-specific behavior
                such as NodeInterrupts for auth.

        Returns:
            List of StructuredTool instances.
        """
        warnings.warn(
            "get_tools() is deprecated and will be removed in the next major version. "
            "Please use init_tools() to initialize tools and to_langchain() to convert them.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Support existing usage pattern
        if tools or toolkits:
            return await self.init_tools(tools=tools, toolkits=toolkits)
        return []


def _create_tool_map(
    tools: list[ToolDefinition],
    use_underscores: bool = True,
) -> dict[str, ToolDefinition]:
    """
    Build a dictionary that maps the "full_tool_name" to the tool definition.

    Args:
        tools: List of ToolDefinition objects to map.
        use_underscores: Whether to use underscores instead of periods in tool names.
                         For example, "Search_SearchGoogle" vs "Search.SearchGoogle".

    Returns:
        Dictionary mapping tool names to tool definitions.

    Note:
        This is a temporary solution to support the naming convention of certain model providers
        like OpenAI, which work better with underscores in tool names.
    """
    tool_map: dict[str, ToolDefinition] = {}
    for tool in tools:
        # Ensure toolkit name and tool name are not None before creating the key
        toolkit_name = tool.toolkit.name if tool.toolkit and tool.toolkit.name else None
        if toolkit_name and tool.name:
            if use_underscores:
                tool_name = f"{toolkit_name}_{tool.name}"
            else:
                tool_name = f"{toolkit_name}.{tool.name}"
            tool_map[tool_name] = tool
    return tool_map
