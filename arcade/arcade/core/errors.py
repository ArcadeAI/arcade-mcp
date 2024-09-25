from typing import Optional


class ToolkitError(Exception):
    """
    Base class for all errors related to toolkits.
    """

    pass


class ToolkitLoadError(ToolkitError):
    """
    Raised when there is an error loading a toolkit.
    """

    pass


class ToolError(Exception):
    """
    Base class for all errors related to tools.
    """

    pass


class ToolDefinitionError(ToolError):
    """
    Raised when there is an error in the definition of a tool.
    """

    pass


# ------  runtime errors ------


class ToolRuntimeError(RuntimeError):
    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.developer_message = developer_message


class ToolExecutionError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message, developer_message)


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool error is retryable.
    """

    def __init__(
        self,
        message: str,
        developer_message: Optional[str] = None,
        additional_prompt_content: Optional[str] = None,
        retry_after_ms: Optional[int] = None,
    ):
        super().__init__(message, developer_message)
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms


class ToolSerializationError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message, developer_message)


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error in the input to a tool.
    """

    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message, developer_message)


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error in the output of a tool.
    """

    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message, developer_message)
