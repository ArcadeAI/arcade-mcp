from arcade_tdk.errors import ToolExecutionError


class AsanaToolExecutionError(ToolExecutionError):
    pass


class PaginationTimeoutError(AsanaToolExecutionError):
    def __init__(self, timeout_seconds: int, tool_name: str):
        message = f"Pagination timed out after {timeout_seconds} seconds"
        super().__init__(
            message=message,
            developer_message=f"{message} while calling the tool {tool_name}",
        )
