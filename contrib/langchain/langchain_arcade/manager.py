import os
from collections.abc import Iterator
from typing import Any, Optional

from arcadepy import Arcade
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse
from langchain_core.tools import StructuredTool

from langchain_arcade._utilities import (
    wrap_arcade_tool,
)


class ArcadeToolManager:
    """
    Arcade tool manager for LangChain framework.

    This class wraps Arcade tools as LangChain `StructuredTool`
    objects for integration.
    """

    def __init__(
        self,
        client: Optional[Arcade] = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the ArcadeToolManager.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>>
            >>> # retrieve a specific tool as a langchain tool
            >>> manager.get_tools(tools=["Search.SearchGoogle"])
            >>>
            >>> # retrieve all tools in a toolkit as langchain tools
            >>> manager.get_tools(toolkits=["Search"])
            >>>
            >>> # clear and initialize new tools in the manager
            >>> manager.init_tools(tools=["Search.SearchGoogle"], toolkits=["Search"])

        Args:
            client: Optional Arcade client instance.
            **kwargs: Additional keyword arguments to pass to the Arcade client.
        """
        if not client:
            api_key = kwargs.get("api_key", os.getenv("ARCADE_API_KEY"))
            base_url = kwargs.get("base_url", os.getenv("ARCADE_BASE_URL"))
            arcade_kwargs = {"api_key": api_key, **kwargs}
            if base_url:
                arcade_kwargs["base_url"] = base_url

            client = Arcade(**arcade_kwargs)  # type: ignore[arg-type]
        self.client = client
        self._tools: dict[str, ToolDefinition] = {}

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

    def get_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        langgraph: bool = True,
    ) -> list[StructuredTool]:
        """Return the tools in the manager as LangChain StructuredTool objects.

        Note: if tools/toolkits are provided, the manager will update it's
        internal tools using a dictionary update by tool name.

        If langgraph is True, the tools will be wrapped with LangGraph-specific
        behavior such as NodeInterrupts for auth.
        Note: Changed in 1.0.0 to default to True.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>>
            >>> # retrieve a specific tool as a langchain tool
            >>> manager.get_tools(tools=["Search.SearchGoogle"])

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            langgraph: Whether to use LangGraph-specific behavior
                such as NodeInterrupts for auth.

        Returns:
            List of StructuredTool instances.
        """
        # TODO account for versioning
        if tools or toolkits:
            new_tools = self._retrieve_tool_definitions(tools, toolkits)
            self._tools.update(new_tools)
        elif len(self) == 0:
            self.init_tools()

        langchain_tools: list[StructuredTool] = []
        for tool_name, definition in self:
            lc_tool = wrap_arcade_tool(self.client, tool_name, definition, langgraph)
            langchain_tools.append(lc_tool)
        return langchain_tools

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """Authorize a user for a tool.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> manager.authorize("X.PostTweet", "user_123")

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize.

        Returns:
            AuthorizationResponse
        """
        return self.client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def is_authorized(self, authorization_id: str) -> bool:
        """Check if a tool authorization is complete.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> manager.init_tools(toolkits=["Search"])
            >>> manager.is_authorized("auth_123")
        """
        return self.client.auth.status(id=authorization_id).status == "completed"

    def wait_for_auth(self, authorization_id: str) -> AuthorizationResponse:
        """Wait for a tool authorization to complete.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> manager.init_tools(toolkits=["Google.ListEmails"])
            >>> response = manager.authorize("Google.ListEmails", "user_123")
            >>> manager.wait_for_auth(response)
            >>> # or
            >>> manager.wait_for_auth(response.id)
        """
        return self.client.auth.wait_for_completion(authorization_id)

    def requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authorization."""

        tool_def = self._get_tool_definition(tool_name)
        if tool_def.requirements is None:
            return False
        return tool_def.requirements.authorization is not None

    def _get_tool_definition(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError:
            raise ValueError(f"Tool '{tool_name}' not found in this ArcadeToolManager instance")

    def _retrieve_tool_definitions(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> dict[str, ToolDefinition]:
        """Retrieve tool definitions from the Arcade client, accounting for pagination."""
        all_tools: list[ToolDefinition] = []

        # First, gather single tools if the user specifically requested them.
        if tools:
            for tool_id in tools:
                # ToolsResource.get(...) returns a single ToolDefinition.
                single_tool = self.client.tools.get(name=tool_id)
                all_tools.append(single_tool)

        # Next, gather tool definitions from any requested toolkits.
        if toolkits:
            for tk in toolkits:
                # tools.list(...) returns a paginated response (SyncOffsetPage),
                # which has an __iter__ method that automatically iterates over all pages.
                paginated_tools = self.client.tools.list(toolkit=tk)
                all_tools.extend(paginated_tools)

        # If no specific tools or toolkits were requested, retrieve *all* tools.
        if not tools and not toolkits:
            paginated_all_tools = self.client.tools.list()
            all_tools.extend(paginated_all_tools)
        # Build a dictionary that maps the "full_tool_name" to the tool definition.
        tool_definitions: dict[str, ToolDefinition] = {}
        for tool in all_tools:
            # For items returned by .list(), the 'toolkit' and 'name' attributes
            # should be present as plain fields on the object. (No need to do toolkit.name)
            full_tool_name = f"{tool.toolkit.name}_{tool.name}"
            tool_definitions[full_tool_name] = tool

        return tool_definitions
