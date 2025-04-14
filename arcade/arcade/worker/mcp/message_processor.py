import logging
from typing import Callable

try:
    from mcp.types import JSONRPCMessage

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

    # Define stub for type hints when MCP isn't available
    class JSONRPCMessage:
        pass


logger = logging.getLogger("arcade.mcp")


# Type definition for middleware functions
MessageProcessor = Callable[[JSONRPCMessage, str], JSONRPCMessage]


class MCPMessageProcessor:
    """
    Processes MCP messages through a chain of middleware.

    This class manages a chain of middleware that can process MCP messages
    before they are sent or after they are received.
    """

    def __init__(self):
        """Initialize an empty middleware chain."""
        self.middleware: list[MessageProcessor] = []

    def add_middleware(self, middleware: MessageProcessor) -> None:
        """
        Add middleware to the processing chain.

        Args:
            middleware: A callable that takes a message and direction and returns a processed message
        """
        if middleware not in self.middleware:
            self.middleware.append(middleware)
            logger.debug(f"Added middleware: {middleware.__class__.__name__}")

    def process_request(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """
        Process an outgoing request message through the middleware chain.

        Args:
            message: The MCP message to process

        Returns:
            The processed message
        """
        return self._process_message(message, "request")

    def process_response(self, message: JSONRPCMessage) -> JSONRPCMessage:
        """
        Process an incoming response message through the middleware chain.

        Args:
            message: The MCP message to process

        Returns:
            The processed message
        """
        return self._process_message(message, "response")

    def _process_message(self, message: JSONRPCMessage, direction: str) -> JSONRPCMessage:
        """
        Process a message through all middleware in the chain.

        Args:
            message: The MCP message to process
            direction: The message direction ("request" or "response")

        Returns:
            The processed message
        """
        if not MCP_AVAILABLE:
            return message

        processed_message = message
        for middleware in self.middleware:
            try:
                processed_message = middleware(processed_message, direction)
            except Exception as e:
                logger.exception(f"Error in middleware {middleware.__class__.__name__}, {e!s}")  # noqa: TRY401

        return processed_message


def create_message_processor(*middleware: MessageProcessor) -> MCPMessageProcessor:
    """
    Create a message processor with the given middleware.

    Args:
        *middleware: Middleware functions to add to the processor

    Returns:
        An MCPMessageProcessor instance
    """
    processor = MCPMessageProcessor()
    for m in middleware:
        if m is not None:
            processor.add_middleware(m)
    return processor
