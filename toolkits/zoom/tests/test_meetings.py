import pytest
from arcade_tdk.errors import ToolExecutionError

from arcade_zoom.tools.meetings import _handle_zoom_api_error


@pytest.mark.asyncio
async def test_handle_zoom_api_error():
    # Create a mock response object
    class MockResponse:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    # Test for 401 Unauthorized
    with pytest.raises(ToolExecutionError, match="Unauthorized: Invalid or expired token"):
        _handle_zoom_api_error(MockResponse(401, "Unauthorized"))

    # Test for 403 Forbidden
    with pytest.raises(ToolExecutionError, match="Forbidden: Access denied"):
        _handle_zoom_api_error(MockResponse(403, "Forbidden"))

    # Test for 429 Too Many Requests
    with pytest.raises(ToolExecutionError, match="Too Many Requests: Rate limit exceeded"):
        _handle_zoom_api_error(MockResponse(429, "Too Many Requests"))

    # Test for other error status codes
    with pytest.raises(ToolExecutionError, match="Error: 500 - Internal Server Error"):
        _handle_zoom_api_error(MockResponse(500, "Internal Server Error"))

    # Test for a successful response (should not raise an error)
    try:
        _handle_zoom_api_error(MockResponse(200, "OK"))
    except ToolExecutionError:
        pytest.fail("ToolExecutionError raised unexpectedly for a successful response.")
