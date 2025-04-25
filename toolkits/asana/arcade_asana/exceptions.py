from arcade.sdk.exceptions import ToolExecutionError


class AsanaToolExecutionError(ToolExecutionError):
    pass


class AsanaNotFoundError(AsanaToolExecutionError):
    pass
