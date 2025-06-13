from arcade_tdk.errors import ToolExecutionError


class JiraToolExecutionError(ToolExecutionError):
    pass


class NotFoundError(JiraToolExecutionError):
    pass


class MultipleItemsFoundError(JiraToolExecutionError):
    pass
