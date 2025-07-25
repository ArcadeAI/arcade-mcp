import traceback
from typing import Any, Literal, Optional


class ToolkitError(Exception):
    """
    Base class for all errors related to toolkits.
    """

    origin: Literal["WORKER", "UPSTREAM", "ENGINE"]
    retryable: bool
    code: str
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
            "code": self.code,
            "message": self.message,
            **self.extra,
        }


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
    def __init__(
        self,
        message: str,
        developer_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.developer_message = developer_message

    def traceback_info(self) -> str | None:
        # return the traceback information of the parent exception
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None


# class ToolExecutionError(ToolRuntimeError):
#     """
#     Raised when there is an error executing a tool.
#     """

#     pass


class ToolExecutionError(ToolkitError):
    """
    Raised when there is an error executing a tool.
    """

    origin = "WORKER"
    retryable = False
    code = "BUG"


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
