from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, Optional

from arcadepy import Arcade
from arcadepy.types import ToolGetResponse as ToolDefinition

from .auth import ArcadeAuthMixin


class BaseArcadeManager(ABC, ArcadeAuthMixin):
    """
    Abstract base class specifically for Arcade-based tool managers.

    This class adds Arcade-specific functionality while remaining
    framework-agnostic in terms of tool conversion.
    """

    def __init__(
        self,
        client: Optional[Arcade] = None,
        user_id: Optional[str] = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize the ArcadeToolManager.

        Example:
            >>> manager = ArcadeToolManager(api_key="...")
            >>>
            >>> # retrieve a specific tool adapted for the framework
            >>> manager.get_tools(tools=["Search.SearchGoogle"])
            >>>
            >>> # retrieve all tools in a toolkit adapted for the framework
            >>> manager.get_tools(toolkits=["Search"])
            >>>
            >>> # clear and initialize new tools in the manager
            >>> manager.init_tools(tools=["Search.SearchGoogle"], toolkits=["Search"])

        Args:
            client: Optional Arcade client instance.
        """
        if not client:
            api_key = kwargs.get("api_key")
            base_url = kwargs.get("base_url")
            client = Arcade(api_key=api_key, base_url=base_url)  # type: ignore[arg-type]

        self.client = client
        self.user_id = user_id
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
                single_tools = [self.client.tools.get(name=tool_id) for tool_id in tools]
                all_tools.extend(single_tools)
            if toolkits:
                for tk in toolkits:
                    all_tools.extend(self.client.tools.list(toolkit=tk))
        else:
            # retrieve all tools
            page_iterator = self.client.tools.list()
            all_tools.extend(page_iterator)

        tool_definitions: dict[str, ToolDefinition] = {}

        for tool in all_tools:
            full_tool_name = f"{tool.toolkit.name}_{tool.name}"
            tool_definitions[full_tool_name] = tool

        return tool_definitions

    @abstractmethod
    def wrap_tool(self, name: str, tool_def: ToolDefinition, **kwargs: Any) -> Any:
        """
        Adapt a tool to the framework-specific tool wrapper.

        This method should be implemented to convert a given tool definition into a
        format or wrapper that is specific to the framework being used.

        Args:
            name: The name of the tool.
            tool_def: The ToolDefinition object containing the tool's details.
            **kwargs: Additional keyword arguments that may be required for wrapping the tool.

        Returns:
            A framework-specific wrapped tool.
        """

    def get_tools(
        self, tools: Optional[list[str]] = None, toolkits: Optional[list[str]] = None, **kwargs: Any
    ) -> list[Any]:
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

        return [self.wrap_tool(name, tool_def, **kwargs) for name, tool_def in self._tools.items()]
