class ToolExecutionError(Exception):
    """Custom exception for tool execution failures."""

    def __init__(self, message: str):
        super().__init__(message)
