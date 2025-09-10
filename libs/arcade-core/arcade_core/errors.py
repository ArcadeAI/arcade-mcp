import traceback
import warnings
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ErrorKind(str, Enum):
    """Error kind that is comprised of
    - the who (toolkit, tool, upstream)
    - the when (load time, definition parsing time, runtime)
    - the what (bad_definition, bad_input, bad_output, retry, context_required, fatal, etc.)"""

    TOOLKIT_LOAD_FAILED = "TOOLKIT_LOAD_FAILED"
    TOOL_DEFINITION_BAD_DEFINITION = "TOOL_DEFINITION_BAD_DEFINITION"
    TOOL_DEFINITION_BAD_INPUT_SCHEMA = "TOOL_DEFINITION_BAD_INPUT_SCHEMA"
    TOOL_DEFINITION_BAD_OUTPUT_SCHEMA = "TOOL_DEFINITION_BAD_OUTPUT_SCHEMA"
    TOOL_RUNTIME_BAD_INPUT_VALUE = "TOOL_RUNTIME_BAD_INPUT_VALUE"
    TOOL_RUNTIME_BAD_OUTPUT_VALUE = "TOOL_RUNTIME_BAD_OUTPUT_VALUE"
    TOOL_RUNTIME_RETRY = "TOOL_RUNTIME_RETRY"
    TOOL_RUNTIME_CONTEXT_REQUIRED = "TOOL_RUNTIME_CONTEXT_REQUIRED"
    TOOL_RUNTIME_FATAL = "TOOL_RUNTIME_FATAL"
    UPSTREAM_RUNTIME_BAD_REQUEST = "UPSTREAM_RUNTIME_BAD_REQUEST"
    UPSTREAM_RUNTIME_AUTH_ERROR = "UPSTREAM_RUNTIME_AUTH_ERROR"
    UPSTREAM_RUNTIME_NOT_FOUND = "UPSTREAM_RUNTIME_NOT_FOUND"
    UPSTREAM_RUNTIME_VALIDATION_ERROR = "UPSTREAM_RUNTIME_VALIDATION_ERROR"
    UPSTREAM_RUNTIME_RATE_LIMIT = "UPSTREAM_RUNTIME_RATE_LIMIT"
    UPSTREAM_RUNTIME_SERVER_ERROR = "UPSTREAM_RUNTIME_SERVER_ERROR"
    UPSTREAM_RUNTIME_UNMAPPED = "UPSTREAM_RUNTIME_UNMAPPED"
    UNKNOWN = "UNKNOWN"


class ToolkitError(Exception, ABC):
    """
    Base class for all Arcade errors.

    Note: This class is an abstract class and cannot be instantiated directly.

    These errors are ultimately converted to the ToolCallError schema.
    Attributes expected from subclasses:
      message                   : str                    # user-facing error message
      kind                      : ErrorKind              # the error kind
      can_retry                 : bool                   # whether the operation can be retried
      developer_message         : str | None             # developer-facing error details
      status_code               : int | None             # HTTP status code when relevant
      additional_prompt_content : str | None             # content for retry prompts
      retry_after_ms            : int | None             # milliseconds to wait before retry
      stacktrace                : str | None             # stacktrace information
      extra                     : dict[str, Any] | None  # arbitrary structured metadata
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> "ToolkitError":
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
        self.message = f"{prefix}{self.message}"  # type: ignore[has-type]
        if hasattr(self, "developer_message") and self.developer_message:  # type: ignore[has-type]
            self.developer_message = f"{prefix}{self.developer_message}"  # type: ignore[has-type]

        return self

    @property
    def is_toolkit_error(self) -> bool:
        """Check if this error originated from loading a toolkit."""
        return hasattr(self, "kind") and self.kind.name.startswith("TOOLKIT_")

    @property
    def is_tool_error(self) -> bool:
        """Check if this error originated from a tool."""
        return hasattr(self, "kind") and self.kind.name.startswith("TOOL_")

    @property
    def is_upstream_error(self) -> bool:
        """Check if this error originated from an upstream service."""
        return hasattr(self, "kind") and self.kind.name.startswith("UPSTREAM_")

    def __str__(self) -> str:
        return self.message


class ToolkitLoadError(ToolkitError):
    """
    Raised while importing / loading a toolkit package
    (e.g. missing dependency, SyntaxError in module top-level code).
    """

    kind: ErrorKind = ErrorKind.TOOLKIT_LOAD_FAILED
    can_retry: bool = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def create_message_prefix(self, toolkit_name: str) -> str:
        return f"[{self.kind.value}] {type(self).__name__} when loading toolkit '{toolkit_name}': "


class ToolError(ToolkitError):
    """
    Any error related to an Arcade tool.

    Note: This class is an abstract class and cannot be instantiated directly.
    """


# ------  definition-time errors (tool developer's responsibility) ------
class ToolDefinitionError(ToolError):
    """
    Raised when there is an error in the definition/signature of a tool.
    """

    kind: ErrorKind = ErrorKind.TOOL_DEFINITION_BAD_DEFINITION

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def create_message_prefix(self, tool_name: str) -> str:
        return f"[{self.kind.value}] {type(self).__name__} in definition of tool '{tool_name}': "


class ToolInputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's input parameter."""

    kind: ErrorKind = ErrorKind.TOOL_DEFINITION_BAD_INPUT_SCHEMA


class ToolOutputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's output parameter."""

    kind: ErrorKind = ErrorKind.TOOL_DEFINITION_BAD_OUTPUT_SCHEMA


# ------  runtime errors ------
class ToolRuntimeError(ToolError, RuntimeError):
    """
    Any failure starting from when the tool call begins until the tool call returns.

    Note: This class should typically not be instantiated directly, but rather subclassed.
    """

    kind: ErrorKind = ErrorKind.TOOL_RUNTIME_FATAL
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
        self.developer_message = developer_message  # type: ignore[assignment]
        self.extra = extra

    def create_message_prefix(self, tool_name: str) -> str:
        return f"[{self.kind.value}] {type(self).__name__} during execution of tool '{tool_name}': "

    def stacktrace(self) -> str | None:
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None

    def traceback_info(self) -> str | None:
        """DEPRECATED: Use stacktrace() instead.

        This method is deprecated and will be removed in a future major version.
        """
        return self.stacktrace()

    # wire-format helper
    def to_payload(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "developer_message": self.developer_message,
            "kind": self.kind,
            "can_retry": self.can_retry,
            "status_code": self.status_code,
            **(self.extra or {}),
        }


# 1. ------  serialization errors ------
class ToolSerializationError(ToolRuntimeError):
    """
    Raised when there is an error serializing/marshalling the tool call arguments or return value.

    Note: This class is not intended to be instantiated directly, but rather subclassed.
    """


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error parsing a tool call argument.
    """

    kind: ErrorKind = ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE
    status_code: int = 400


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error serializing a tool call return value.
    """

    kind: ErrorKind = ErrorKind.TOOL_RUNTIME_BAD_OUTPUT_VALUE
    status_code: int = 500


# 2. ------  tool-body errors ------
class ToolExecutionError(ToolRuntimeError):
    """
    DEPRECATED: Raised when there is an error executing a tool.

    ToolExecutionError is deprecated and will be removed in a future major version.
    Use more specific error types instead:
    - RetryableToolError for retryable errors
    - ContextRequiredToolError for errors requiring user context
    - FatalToolError for fatal/unexpected errors
    - UpstreamError for upstream service errors
    - UpstreamRateLimitError for upstream rate limiting errors
    """

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ):
        if type(self) is ToolExecutionError:
            warnings.warn(
                "ToolExecutionError is deprecated and will be removed in a future major version. "
                "Use more specific error types instead: RetryableToolError, ContextRequiredToolError, "
                "FatalToolError, UpstreamError, or UpstreamRateLimitError.",
                DeprecationWarning,
                stacklevel=2,
            )
        super().__init__(message, developer_message=developer_message, extra=extra)


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool execution error is retryable.
    """

    kind: ErrorKind = ErrorKind.TOOL_RUNTIME_RETRY
    can_retry: bool = True

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,  # TODO: Make required in next major version
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

    This is typically used when an argument provided to the tool is invalid in some way,
    and immediately prompting an LLM to retry the tool call is not desired.
    """

    kind: ErrorKind = ErrorKind.TOOL_RUNTIME_CONTEXT_REQUIRED

    def __init__(
        self,
        message: str,
        additional_prompt_content: str,
        developer_message: str | None = None,
        *,
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
        developer_message: str | None = None,
        *,
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

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        *,
        status_code: int,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, developer_message=developer_message, extra=extra)
        self.status_code = status_code
        # Determine retryability based on status code
        self.can_retry = status_code >= 500 or status_code == 429
        # Set appropriate error kind based on status
        if status_code in (401, 403):
            self.kind = ErrorKind.UPSTREAM_RUNTIME_AUTH_ERROR
        elif status_code == 404:
            self.kind = ErrorKind.UPSTREAM_RUNTIME_NOT_FOUND
        elif status_code == 429:
            self.kind = ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT
        elif status_code >= 500:
            self.kind = ErrorKind.UPSTREAM_RUNTIME_SERVER_ERROR
        elif 400 <= status_code < 500:
            self.kind = ErrorKind.UPSTREAM_RUNTIME_BAD_REQUEST
        else:
            self.kind = ErrorKind.UPSTREAM_RUNTIME_UNMAPPED


class UpstreamRateLimitError(UpstreamError):
    """
    Rate limit error from an upstream service.

    Special case of UpstreamError that includes retry_after_ms information.
    """

    kind: ErrorKind = ErrorKind.UPSTREAM_RUNTIME_RATE_LIMIT
    can_retry: bool = True

    def __init__(
        self,
        message: str,
        retry_after_ms: int,
        developer_message: str | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=429, developer_message=developer_message, extra=extra)
        self.retry_after_ms = retry_after_ms
