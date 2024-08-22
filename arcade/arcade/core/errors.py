from typing import Optional


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
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ToolExecutionError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    def __init__(self, message: str, developer_message: Optional[str] = None):
        super().__init__(message)
        self.developer_message = developer_message


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool error is retryable.
    """

    def __init__(
        self,
        message: str,
        developer_message: Optional[str] = None,
        additional_prompt_content: Optional[str] = None,
    ):
        super().__init__(message)
        self.developer_message = developer_message
        self.additional_prompt_content = additional_prompt_content


class ToolSerializationError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    pass


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error in the input to a tool.
    """

    pass


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error in the output of a tool.
    """

    pass
