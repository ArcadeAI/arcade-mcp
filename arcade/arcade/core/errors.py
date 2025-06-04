import traceback
from typing import Optional

from arcade.core.schema import HttpResponse


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
    _can_retry: bool = False

    def __init__(
        self,
        message: str,
        developer_message: Optional[str] = None,
        additional_prompt_content: Optional[str] = None,
        retry_after_ms: Optional[int] = None,
    ):
        super().__init__(message)

        if (
            not self._can_retry
            and retry_after_ms is not None
            or additional_prompt_content is not None
        ):
            raise AttributeError(
                "retry_after_ms and additional_prompt_content are only allowed for errors where `_can_retry` is True"
            )

        self.message = message
        self.developer_message = developer_message
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms

    @property
    def can_retry(self) -> bool:
        return self._can_retry

    @property
    def traceback_info(self) -> str | None:
        # return the traceback information of the parent exception
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None


class ToolExecutionError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    pass


# ------  serialization errors ------


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


# ------  retry-able errors ------


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool error is retryable.
    """

    _can_retry: bool = True


class ThirdPartyApiError(ToolExecutionError):
    """
    Raised when there is an error in a downstream request to a third-party service.
    """

    def __init__(self, http_response: HttpResponse, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_response = http_response.model_dump()


class ThirdPartyApiServerError(ThirdPartyApiError, RetryableToolError):
    """
    Raised when there is a 500 Server Error in a downstream request to a third-party service.
    """

    pass


class ThirdPartyApiRateLimitError(ThirdPartyApiError, RetryableToolError):
    """
    Raised when there is a 429 Too Many Requests in a downstream request to a third-party service.
    """

    pass
