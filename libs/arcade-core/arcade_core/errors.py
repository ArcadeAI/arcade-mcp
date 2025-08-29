import traceback
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

# TODO: break out into separate files
# TODO: determine which errors should be abstract. (can't break backwards compatibility)
# TODO: should classes help build up the message/developer_message?


class ErrorOrigin(str, Enum):
    """Where the error originated."""

    TOOLKIT = "TOOLKIT"
    TOOL = "TOOL"
    UPSTREAM = "UPSTREAM"
    UNKNOWN = "UNKNOWN"


class ErrorPhase(str, Enum):
    """When the error occurred."""

    LOAD = "LOAD"
    DEFINITION = "DEFINITION"
    RUNTIME = "RUNTIME"
    UNKNOWN = "UNKNOWN"


class ErrorCode(str, Enum):
    """Error codes."""

    # Toolkit Load error codes
    LOAD_FAILED = "LOAD_FAILED"
    # Tool Definition error codes
    BAD_DEFINITION = "BAD_DEFINITION"
    BAD_INPUT_SCHEMA = "BAD_INPUT_SCHEMA"
    BAD_OUTPUT_SCHEMA = "BAD_OUTPUT_SCHEMA"
    # Tool Runtime error codes
    BAD_INPUT_VALUE = "BAD_INPUT_VALUE"
    BAD_OUTPUT_VALUE = "BAD_OUTPUT_VALUE"
    RETRY_TOOL = "RETRY_TOOL"
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    FATAL = "FATAL"
    # Upstream Runtime error codes
    BAD_REQUEST = "BAD_REQUEST"
    AUTH_ERROR = "AUTH_ERROR"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    SERVER_ERROR = "SERVER_ERROR"
    # Unknown error code
    UNKNOWN = "UNKNOWN"


class ToolkitError(Exception, ABC):
    """
    Base class for all Arcade errors.

    Note: This class is an abstract class and cannot be instantiated directly.

    These errors are ultimately converted to the ToolCallError schema.
    Attributes expected from subclasses:
      message                   : str                    # user-facing error message
      origin                    : ErrorOrigin            # where the error originated
      phase                     : ErrorPhase             # when the error occurred
      code                      : ErrorCode              # machine-readable error code
      can_retry                 : bool                   # whether the operation can be retried
      developer_message         : str | None             # developer-facing error details
      status_code               : int | None             # HTTP status code when relevant
      additional_prompt_content : str | None             # content for retry prompts
      retry_after_ms            : int | None             # milliseconds to wait before retry
      stacktrace                : str | None             # stacktrace information
      extra                     : dict[str, Any] | None  # arbitrary structured metadata
    """

    def __new__(cls, *args, **kwargs):
        abs_methods = getattr(cls, "__abstractmethods__", None)
        if abs_methods:
            raise TypeError(f"Can't instantiate abstract class {cls.__name__}")
        return super().__new__(cls)

    @abstractmethod
    def create_message_prefix(self, name: str) -> str:
        pass

    def with_context(self, name: str) -> "ToolkitError":
        """
        Add context to the error message.

        Args:
            name: The name of the tool or toolkit that caused the error.

        Returns:
            The error with the context added to the message.
        """
        prefix = self.create_message_prefix(name)
        self.message = f"{prefix}{self.message}"
        if hasattr(self, "developer_message") and self.developer_message:
            self.developer_message = f"{prefix}{self.developer_message}"

        return self

    def __str__(self) -> str:
        return self.message


class ToolkitLoadError(ToolkitError):
    """
    Raised while importing / loading a toolkit package
    (e.g. missing dependency, SyntaxError in module top-level code).
    """

    origin: ErrorOrigin = ErrorOrigin.TOOLKIT
    phase: ErrorPhase = ErrorPhase.LOAD
    code: ErrorCode = ErrorCode.LOAD_FAILED
    can_retry: bool = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def create_message_prefix(self, toolkit_name: str) -> str:
        return f"[{self.origin.value}_{self.phase.value}_{self.code.value}] {type(self).__name__} when loading toolkit '{toolkit_name}': "


class ToolError(ToolkitError):
    """
    Any error related to an Arcade tool.

    Note: This class is an abstract class and cannot be instantiated directly.
    """


# ------  definition-time errors (tool developer's responsibility) ------
class ToolDefinitionError(ToolError):
    """
    Raised when there is an error in the definition/signature of a tool.

    Note: This class is not intended to be instantiated directly.
    """

    origin: ErrorOrigin = ErrorOrigin.TOOL
    phase: ErrorPhase = ErrorPhase.DEFINITION
    code: ErrorCode = ErrorCode.BAD_DEFINITION

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def create_message_prefix(self, tool_name: str) -> str:
        return f"[{self.origin.value}_{self.phase.value}_{self.code.value}] {type(self).__name__} in definition of tool '{tool_name}': "


class ToolInputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's input parameter."""

    code: ErrorCode = ErrorCode.BAD_INPUT_SCHEMA


class ToolOutputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's output parameter."""

    code: ErrorCode = ErrorCode.BAD_OUTPUT_SCHEMA


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
    code: ErrorCode = ErrorCode.FATAL
    can_retry: bool = False
    status_code: int | None = None
    extra: dict[str, Any] | None = None

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.developer_message = developer_message
        self.extra = extra

    def create_message_prefix(self, tool_name: str) -> str:
        return f"[{self.origin.value}_{self.phase.value}_{self.code.value}] {type(self).__name__} in execution of tool '{tool_name}': "

    def stacktrace(self) -> str | None:
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None

    # wire-format helper
    def to_payload(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "developer_message": self.developer_message,
            "origin": self.origin,
            "code": self.code,
            "phase": self.phase,
            "can_retry": self.can_retry,
            "status_code": self.status_code,
            **(self.extra or {}),
        }


# 1. ------  serialization errors ------
class ToolSerializationError(ToolRuntimeError):  # TODO: probably make this abstract
    """
    Raised when there is an error serializing/marshalling the tool call arguments or return value.

    Note: This class is not intended to be instantiated directly.
    """

    # TODO: create a new error code and set it here as default?


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error parsing a tool call argument.
    """

    code: ErrorCode = ErrorCode.BAD_INPUT_VALUE
    status_code: int = 400


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error serializing a tool call return value.
    """

    code: ErrorCode = ErrorCode.BAD_OUTPUT_VALUE
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

    code: ErrorCode = ErrorCode.RETRY_TOOL
    can_retry: bool = True

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str
        | None = None,  # TODO: Should be required? Would be breaking if I made it required
        retry_after_ms: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms


class ContextRequiredToolError(ToolExecutionError):
    """
    Raised when the combination of additional content from the tool AND
    additional context from the end-user/orchestrator is required before retrying the tool.
    """

    code: ErrorCode = ErrorCode.CONTEXT_REQUIRED

    def __init__(
        self,
        message: str,
        *,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,  # TODO: Should be required?
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.additional_prompt_content = additional_prompt_content


class FatalToolError(ToolExecutionError):
    """
    Raised when there is an unexpected or unknown error executing a tool.
    """

    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)


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
        *,
        status_code: int,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.status_code = status_code
        # Determine retryability based on status code
        self.can_retry = status_code >= 500 or status_code == 429
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
            self.code = ErrorCode.FATAL


class UpstreamRateLimitError(UpstreamError):
    """
    Rate limit error from an upstream service.

    Special case of UpstreamError that includes retry_after_ms information.
    """

    code: ErrorCode = ErrorCode.RATE_LIMIT
    can_retry: bool = True

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
