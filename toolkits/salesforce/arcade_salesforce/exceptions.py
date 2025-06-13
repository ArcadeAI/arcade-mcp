from arcade_tdk.errors import ToolExecutionError


class SalesforceToolExecutionError(ToolExecutionError):
    def __init__(self, errors: list[str], message: str = "Failed to execute Salesforce tool"):
        self.message = message
        self.errors = errors
        exc_message = f"{message}. Errors: {errors}"
        super().__init__(
            message=exc_message,
            developer_message=exc_message,
        )


class ResourceNotFoundError(SalesforceToolExecutionError):
    def __init__(self, errors: list[str]):
        super().__init__(message="Resource not found", errors=errors)


class BadRequestError(SalesforceToolExecutionError):
    def __init__(self, errors: list[str]):
        super().__init__(message="Bad request", errors=errors)
