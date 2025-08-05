import traceback
from enum import Enum
from typing import Any

# TODO: break out into separate files
# TODO: determine which errors should be abstract. (can't break backwards compatibility)
# TODO: should classes help build up the message/developer_message?


class ErrorOrigin(str, Enum):
    """Origin of the error."""

    TOOLKIT = "TOOLKIT"
    TOOL = "TOOL"
    UPSTREAM = "UPSTREAM"


class ErrorPhase(str, Enum):
    """Phase when the error occurred."""

    LOAD = "LOAD"
    DEFINITION = "DEFINITION"
    RUNTIME = "RUNTIME"


class ErrorCode(str, Enum):
    """Common error codes."""

    LOAD_FAILED = "LOAD_FAILED"
    BAD_INPUT_SCHEMA = "BAD_INPUT_SCHEMA"
    BAD_OUTPUT_SCHEMA = "BAD_OUTPUT_SCHEMA"
    BAD_INPUT_VALUE = "BAD_INPUT_VALUE"
    BAD_OUTPUT_VALUE = "BAD_OUTPUT_VALUE"
    TOOL_RETRY = "TOOL_RETRY"
    BUG = "BUG"
    BAD_REQUEST = "BAD_REQUEST"
    AUTH_ERROR = "AUTH_ERROR"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    SERVER_ERROR = "SERVER_ERROR"


class ToolkitError(Exception):
    """
    Base class for all Arcade errors.

    Note: This class is not intended to be instantiated directly.

    Common (not enforced) attributes expected from subclasses:
      origin      : ErrorOrigin
      phase       : ErrorPhase
      retryable   : bool
      code        : str                # machine-readable subtype of the error
      status_code : int | None         # HTTP status code when relevant
      extra       : dict[str, Any]     # arbitrary structured metadata
    """


class ToolkitLoadError(ToolkitError):
    """
    Raised while importing / loading a toolkit package
    (e.g. missing dependency, SyntaxError in module top-level code).
    """

    origin: ErrorOrigin = ErrorOrigin.TOOLKIT
    phase: ErrorPhase = ErrorPhase.LOAD
    retryable: bool = False
    code: str = ErrorCode.LOAD_FAILED


class ToolError(ToolkitError):
    """
    Any error related to an Arcade tool.

    Note: This class is not intended to be instantiated directly.
    """


# ------  definition-time errors (tool developer's responsibility) ------
class ToolDefinitionError(ToolError):
    """
    Raised when there is an error in the definition/signature of a tool.

    Note: This class is not intended to be instantiated directly.
    """


class ToolInputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's input parameter."""

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.DEFINITION
    retryable: bool = False
    code: str = ErrorCode.BAD_INPUT_SCHEMA


class ToolOutputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's output parameter."""

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.DEFINITION
    retryable: bool = False
    code: str = ErrorCode.BAD_OUTPUT_SCHEMA


# ------  runtime errors ------


class ToolRuntimeError(
    ToolError, RuntimeError
):  # TODO: does it matter if this is a subclass of RuntimeError?
    """
    Any failure starting from when the tool call begins until the tool call returns.

    Note: This class is not intended to be instantiated directly.
    """

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.RUNTIME
    retryable: bool = False
    code: ErrorCode = ErrorCode.BUG
    status_code: int | None = None
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
            "message": self.message,
            "developer_message": self.developer_message,
            "origin": self.origin,
            "retryable": self.retryable,
            "code": self.code,
            "status_code": self.status_code,
            **self.extra,
        }


# 1. ------  serialization errors ------
class ToolSerializationError(ToolRuntimeError):  # TODO: probably make this abstract
    """
    Raised when there is an error serializing/marshalling the tool call arguments or return value.

    Note: This class is not intended to be instantiated directly.
    """

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.RUNTIME
    retryable: bool = False


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error parsing a tool call argument.
    """

    code: str = ErrorCode.BAD_INPUT_VALUE
    status_code: int = 400


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error serializing a tool call return value.
    """

    code: str = ErrorCode.BAD_OUTPUT_VALUE
    status_code: int = 500


# 2. ------  tool-body errors ------
class ToolExecutionError(ToolRuntimeError):
    """
    Raised when there is an error executing a tool.
    """

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.RUNTIME


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool execution error is retryable.
    """

    retryable: bool = True
    code: str = ErrorCode.TOOL_RETRY

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms


class NonRetryableToolError(ToolExecutionError):
    """
    Raised when there is an error executing a tool.
    """

    retryable: bool = False
    code: str = ErrorCode.BUG

    def __init__(
        self,
        message: str,
        status_code: int,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.status_code = status_code


# 3. ------  upstream errors in tool body------
class UpstreamError(ToolExecutionError):
    """
    Error from an upstream service/API during tool execution.

    This class handles all upstream failures except rate limiting.
    The status_code and extra dict provide details about the specific error type.
    """

    origin: ErrorOrigin = ErrorOrigin.UPSTREAM
    phase: ErrorPhase = ErrorPhase.RUNTIME

    def __init__(
        self,
        message: str,
        status_code: int,
        *,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.status_code = status_code
        # Determine retryability based on status code
        self.retryable = status_code >= 500 or status_code == 429
        # Set appropriate error code based on status
        if status_code in (401, 403):
            self.code = ErrorCode.AUTH_ERROR
        elif status_code == 404:
            self.code = ErrorCode.NOT_FOUND
        elif status_code == 429:
            self.code = ErrorCode.RATE_LIMIT
        elif status_code >= 500:
            self.code = ErrorCode.SERVER_ERROR
        elif 400 <= status_code < 500:
            self.code = ErrorCode.BAD_REQUEST
        else:
            self.code = ErrorCode.BUG


class UpstreamRateLimitError(UpstreamError):
    """
    Rate limit error from an upstream service.

    Special case of UpstreamError that includes retry_after_ms information.
    """

    retryable: bool = True
    code: str = ErrorCode.RATE_LIMIT

    def __init__(
        self,
        message: str,
        retry_after_ms: int,
        *,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=429, developer_message=developer_message, extra=extra)
        self.retry_after_ms = retry_after_ms
