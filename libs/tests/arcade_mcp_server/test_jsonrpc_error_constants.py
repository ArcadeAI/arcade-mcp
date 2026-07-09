"""Pin the numeric values of the JSON-RPC error code constants.

These constants are baked into the wire protocol; changing them would break
every connected MCP client. The package source now uses the named constants
instead of bare integer literals (see commit history for PR #828 jottakka #10).
"""

from arcade_mcp_server.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)


def test_parse_error_code():
    assert PARSE_ERROR == -32700


def test_invalid_request_code():
    assert INVALID_REQUEST == -32600


def test_method_not_found_code():
    assert METHOD_NOT_FOUND == -32601


def test_invalid_params_code():
    assert INVALID_PARAMS == -32602


def test_internal_error_code():
    assert INTERNAL_ERROR == -32603
