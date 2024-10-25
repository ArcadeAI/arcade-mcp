import os
from typing import Optional

from arcadepy import Arcade
from arcadepy.types.shared import AuthorizationResponse, ToolDefinition
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
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        **kwargs,
    ):
        """Initialize the ArcadeToolManager.

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            client: Optional Arcade client instance.
        """
        if not client:
            api_key = kwargs.get("api_key") or os.getenv("ARCADE_API_KEY")
            client = Arcade(api_key=api_key)  # will throw error if no api_key
        self.client = client
        self.init_tools(tools, toolkits)

    def __iter__(self):
        yield from self._tools.items()

    def __len__(self):
        return len(self._tools)

    def __getitem__(self, tool_name: str):
        return self._tools[tool_name]

    def init_tools(
        self,
        tools: Optional[list[str]] = None,
        toolkits: Optional[list[str]] = None,
        langgraph: bool = False,
    ) -> list[StructuredTool]:
        """Initialize Arcade tools and return them as LangChain StructuredTool objects.

        > Note: This will clear any existing tools in the manager.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>> manager.init_tools(tools=["Search.SearchGoogle"])

        Args:
            tools: Optional list of tool names to include.
            toolkits: Optional list of toolkits to include.
            langgraph: Whether to use LangGraph-specific behavior.

        Returns:
            List of StructuredTool instances.
        """
        if tools or toolkits:
            self._tools = self._retrieve_tool_definitions(tools, toolkits)

        tools = []
        for tool_name, definition in self:
            lc_tool = wrap_arcade_tool(self.client, tool_name, definition, langgraph)
            tools.append(lc_tool)
        return tools

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """Authorize a user for a tool."""
        return self.client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def is_authorized(self, authorization_id: str) -> bool:
        """Check if a tool authorization is complete."""
        return self.client.auth.status(authorization_id=authorization_id).status == "completed"

    def requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authorization."""

        tool_def = self._get_tool_definition(tool_name)
        return tool_def.requirements.authorization is not None

    def _get_tool_definition(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError:
            raise ValueError(f"Tool '{tool_name}' not found in this ArcadeToolManager instance")

    def _retrieve_tool_definitions(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None
    ) -> dict[str, ToolDefinition]:
        all_tools: list[ToolDefinition] = []
        if tools or toolkits:
            if tools:
                single_tools = [self.client.tools.get(tool_id=tool_id) for tool_id in tools]
                all_tools.extend(single_tools)
            if toolkits:
                for tk in toolkits:
                    all_tools.extend(self.client.tools.list(toolkit=tk))
        else:
            # retrieve all tools
            all_tools = self.client.tools.list()

        tool_definitions: dict[str, ToolDefinition] = {}

        for tool in all_tools:
            full_tool_name = f"{tool.toolkit.name}_{tool.name}"
            tool_definitions[full_tool_name] = tool

        return tool_definitions
