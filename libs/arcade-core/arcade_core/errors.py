import traceback
from enum import Enum
from typing import Any

# TODO: break out into separate files
# TODO: determine which errors should be abstract. (can't break backwards compatibility)
# TODO: should classes help build up the message/developer_message?
# TODO: remove "extra" entirely?


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
class ToolExecutionError(
    ToolRuntimeError
):  # TODO: I'd love to make this abstract, but can't break backwards compatibility
    """
    Raised when there is an error executing a tool.

    Note: This class is not intended to be instantiated directly.
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
    ):
        super().__init__(message, developer_message=developer_message)
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
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code


# 3. ------  upstream errors in tool body------
class UpstreamError(ToolRuntimeError):  # TODO: probably make this abstract
    """
    Parent error for all failures from the upstream provider.

    Note: This class is not intended to be instantiated directly.
    """

    origin: ErrorOrigin = ErrorOrigin.UPSTREAM
    phase: ErrorPhase = ErrorPhase.RUNTIME


class UpstreamBadRequestError(UpstreamError):
    """Raised when an upstream provider returns a bad request error."""

    retryable: bool = False
    code: str = ErrorCode.BAD_REQUEST
    status_code: int = 400


class UpstreamAuthError(UpstreamError):
    """
    Raised when an upstream provider returns an authentication or authorization error.

    This covers both missing/invalid credentials (401) and insufficient permissions (403).
    """

    retryable: bool = False
    code: str = ErrorCode.AUTH_ERROR

    def __init__(
        self,
        message: str,
        status_code: int,  # must be 401 or 403
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code


class UpstreamNotFoundError(UpstreamError):
    """Raised when an upstream provider returns a not found error."""

    retryable: bool = False
    code: str = ErrorCode.NOT_FOUND
    status_code: int = 404


class UpstreamValidationError(UpstreamError):
    """Raised when upstream provider rejects request due to validation errors."""

    retryable: bool = False
    code: str = ErrorCode.VALIDATION_ERROR
    status_code: int = 422


class UpstreamRateLimitError(UpstreamError):
    """
    Raised when an upstream provider is rate limiting a request in a tool.
    """

    retryable: bool = True
    code: str = ErrorCode.RATE_LIMIT
    status_code: int = 429

    def __init__(
        self,
        retry_after_ms: int,
        message: str,
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.retry_after_ms = retry_after_ms


class UpstreamServerError(UpstreamError):
    """Raised when an upstream provider returns a server error (5xx)."""

    retryable: bool = True
    code: str = ErrorCode.SERVER_ERROR
    status_code: int = 500

    def __init__(
        self,
        message: str,
        status_code: int,  # must be 5xx
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code
