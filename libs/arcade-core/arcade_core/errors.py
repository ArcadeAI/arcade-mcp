import traceback
from typing import Any, Literal, Optional


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


class ToolRuntimeError(ToolError, RuntimeError):
    origin: Literal["WORKER", "UPSTREAM", "ENGINE"]
    retryable: bool
    status_code: int
    extra: dict[str, Any]

    def __init__(
        self,
        message: str,
        *,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.developer_message = developer_message
        self.extra = extra or {}

    def traceback_info(self) -> str | None:
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None

    # wire-format helper
    def to_payload(self) -> dict[str, Any]:
        return {
            "origin": self.origin,
            "retryable": self.retryable,
            "status_code": self.status_code,
            "message": self.message,
            **self.extra,
        }


class ToolExecutionError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    pass


class NonRetryableToolError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    origin = "WORKER"
    retryable = False

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        developer_message: Optional[str] = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code


class RetryableToolError(ToolRuntimeError):
    """
    Raised when a tool error is retryable.
    """

    origin = "WORKER"
    retryable = True

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        developer_message: Optional[str] = None,
        additional_prompt_content: Optional[str] = None,
        retry_after_ms: Optional[int] = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms


# class RetryableToolError(ToolExecutionError):
#     """
#     Raised when a tool error is retryable.
#     """

#     def __init__(
#         self,
#         message: str,
#         developer_message: Optional[str] = None,
#         additional_prompt_content: Optional[str] = None,
#         retry_after_ms: Optional[int] = None,
#     ):
#         super().__init__(message, developer_message)
#         self.additional_prompt_content = additional_prompt_content
#         self.retry_after_ms = retry_after_ms


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
